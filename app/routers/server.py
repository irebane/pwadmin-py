import asyncio
import json
import shutil
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from app.deps import require_admin
from app.config import settings
from app.services.server_config import read_game_config, save_game_config
from app.services.server_status import get_server_status, get_maps_status
from pydantic import BaseModel

_LOG_FILE = Path(__file__).parent.parent.parent / "data" / "activity_log.json"


def _read_log() -> list:
    try:
        return json.loads(_LOG_FILE.read_text()) if _LOG_FILE.exists() else []
    except Exception:
        return []


def _write_log(log: list) -> None:
    _LOG_FILE.write_text(json.dumps(log))

router = APIRouter(prefix="/api/server")


@router.get("/status")
async def server_status(user: dict = Depends(require_admin)):
    return await get_server_status()


@router.get("/maps")
async def maps_status(user: dict = Depends(require_admin)):
    return await get_maps_status()


@router.get("/config")
async def get_config(user: dict = Depends(require_admin)):
    return await read_game_config()


class ConfigBody(BaseModel):
    debug_mode: int = 0
    class_mask: int = 0
    exp_bonus: int = 0
    sp_bonus: int = 0
    drop_bonus: int = 0
    money_bonus: int = 0
    pvp: int = 0
    tw: int = 0
    name_insens: int = 0
    name_max_len: int = 16
    glinkd_count: int = 1
    db_workers: int = 1
    name_workers: int = 1


@router.post("/config")
async def save_config(body: ConfigBody, user: dict = Depends(require_admin)):
    error = await save_game_config(body.model_dump())
    if error:
        raise HTTPException(500, detail=error)
    return {"success": True, "message": "For changes you need (re)start the server!"}


class LogBody(BaseModel):
    action: str        # get | add | clear
    entry: str = ""


@router.post("/log")
async def activity_log(body: LogBody, user: dict = Depends(require_admin)):
    if body.action == "get":
        return _read_log()
    if body.action == "clear":
        _write_log([])
        return {"ok": True}
    if body.action == "add":
        entry = body.entry.strip()
        if not entry:
            raise HTTPException(400, detail="Empty entry")
        log = _read_log()
        log.insert(0, entry)
        if len(log) > 200:
            log = log[:200]
        _write_log(log)
        return {"ok": True}
    raise HTTPException(400, detail="Invalid action")


class MapControlBody(BaseModel):
    action: str   # start | stop | stopmaps | startmaps
    zone: str = ""


@router.post("/maps")
async def maps_control(body: MapControlBody, user: dict = Depends(require_admin)):
    from app.config import settings
    allowed = {"start", "stop", "stopmaps", "startmaps"}
    if body.action not in allowed:
        raise HTTPException(400, detail="Invalid action")

    if body.action in ("stopmaps", "startmaps"):
        await asyncio.create_subprocess_exec(
            "sudo", "/home/gs_zone.sh", body.action,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL,
        )
        return {"ok": True}

    # Single zone
    zones = settings.gs_zones_dict
    if body.zone not in zones:
        raise HTTPException(400, detail=f"Unknown zone: {body.zone}")
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "/home/gs_zone.sh", body.action, body.zone,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode(errors="replace").strip()
        if "Already running" in output:
            raise HTTPException(409, detail="Zone is already running.")
        return {"ok": True}
    except asyncio.TimeoutError:
        raise HTTPException(504, detail="Zone command timed out")


_ITEMS_JSON = Path("data/pw_items.json")
_ITEMS_BAK  = Path("data/pw_items.json.bak")
_TOOL       = Path(__file__).parent.parent.parent / "tools" / "generate_items.py"


@router.post("/regenerate-items")
async def regenerate_items(user: dict = Depends(require_admin)):
    """Regenerate pw_items.json from the game server's elements.data."""
    elements_path = f"{settings.server_path.rstrip('/')}/gamed/config/elements.data"
    if not Path(elements_path).exists():
        raise HTTPException(404, detail=f"elements.data not found at {elements_path}")
    if not _TOOL.exists():
        raise HTTPException(500, detail="generate_items.py tool not found")

    # Backup existing
    if _ITEMS_JSON.exists():
        shutil.copy2(_ITEMS_JSON, _ITEMS_BAK)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_generate, elements_path)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    # Clear the LRU cache so the new file is picked up immediately
    try:
        from app.services.items import _load_items, _build_id_map
        _load_items.cache_clear()
        _build_id_map.cache_clear()
    except Exception:
        pass

    return result


def _run_generate(elements_path: str) -> dict:
    import subprocess, json as _json
    proc = subprocess.run(
        [sys.executable, str(_TOOL), "--source", "elements",
         "--elements", elements_path, "--no-backup"],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "generator failed")
    data = _json.loads(_ITEMS_JSON.read_text(encoding="utf-8"))
    total = sum(len(v) for subs in data.values() for v in subs.values())
    return {"success": True, "total_items": total, "log": proc.stderr.strip()}


class ControlBody(BaseModel):
    action: str  # start | stop | restart


@router.post("/control")
async def server_control(body: ControlBody, user: dict = Depends(require_admin)):
    if body.action not in ("start", "stop", "restart"):
        raise HTTPException(400, detail="Invalid action")
    try:
        # Fire and forget — systemctl can take 30-60s for a full server restart.
        # Frontend polls /api/server/status to detect completion.
        await asyncio.create_subprocess_exec(
            "sudo", "/usr/bin/systemctl", body.action, "pwserver",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
