import asyncio
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.deps import require_admin
from app.config import settings
from app.services.server_config import read_game_config, save_game_config
from app.services.server_status import get_server_status, get_maps_status
from app.services import instance_watch
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
        zones = settings.gs_zones_dict
        if body.action == "startmaps":
            args = list(zones.keys())
        else:  # stopmaps — protect World-type zones (gs01 is always protected by the script itself)
            args = [z for z, info in zones.items() if info.get("type") == "world"]
        await asyncio.create_subprocess_exec(
            "sudo", "/home/gs_zone.sh", body.action, *args,
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
        if "Insufficient memory" in output:
            raise HTTPException(503, detail=output)
        return {"ok": True}
    except asyncio.TimeoutError:
        raise HTTPException(504, detail="Zone command timed out")


class AutostartBody(BaseModel):
    enabled: bool
    idle_minutes: int = 60


@router.get("/autostart")
async def autostart_status(user: dict = Depends(require_admin)):
    return {
        "enabled": instance_watch.is_enabled(),
        "idle_minutes": instance_watch.get_idle_minutes(),
        "log": instance_watch.get_log(),
    }


@router.post("/autostart")
async def autostart_set(body: AutostartBody, user: dict = Depends(require_admin)):
    instance_watch.set_enabled(body.enabled, body.idle_minutes)
    return {"enabled": body.enabled, "idle_minutes": instance_watch.get_idle_minutes()}


_ITEMS_JSON  = Path("data/pw_items.json")
_BACKUP_DIR  = Path("data/backups")
_UPLOADS_DIR = Path("data/uploads")
_TOOL        = Path(__file__).parent.parent.parent / "tools" / "generate_items.py"
_UPLOADED_EL = _UPLOADS_DIR / "elements.data"
_BAK_RE      = re.compile(r'^pw_items_\d{8}_\d{6}\.json\.bak$')


def _item_count(path: Path) -> int:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return sum(len(v) for subs in d.values() for v in subs.values())
    except Exception:
        return -1


def _file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size_kb": round(stat.st_size / 1024, 1),
        "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "item_count": _item_count(path),
    }


def _clear_item_cache() -> None:
    try:
        from app.services.items import _load_items, _build_id_map
        _load_items.cache_clear()
        _build_id_map.cache_clear()
    except Exception:
        pass


@router.get("/items-files")
async def items_files(user: dict = Depends(require_admin)):
    current = _file_info(_ITEMS_JSON) if _ITEMS_JSON.exists() else None
    backups = []
    if _BACKUP_DIR.exists():
        for f in sorted(_BACKUP_DIR.iterdir(), reverse=True):
            if _BAK_RE.match(f.name):
                backups.append(_file_info(f))

    server_el = Path(f"{settings.server_path.rstrip('/')}/gamed/config/elements.data")
    if server_el.exists():
        el_source = "server"
        el_path   = str(server_el)
    elif _UPLOADED_EL.exists():
        el_source = "uploaded"
        el_path   = str(_UPLOADED_EL)
    else:
        el_source = "none"
        el_path   = str(server_el)  # show expected path even if missing

    return {
        "current": current,
        "backups": backups,
        "uploaded_elements": _UPLOADED_EL.exists(),
        "el_source": el_source,   # "server" | "uploaded" | "none"
        "el_path":   el_path,
    }


class ActivateBody(BaseModel):
    filename: str


@router.post("/items-activate")
async def items_activate(body: ActivateBody, user: dict = Depends(require_admin)):
    if not _BAK_RE.match(body.filename):
        raise HTTPException(400, detail="Invalid filename")
    src = _BACKUP_DIR / body.filename
    if not src.exists():
        raise HTTPException(404, detail="Backup not found")

    # Back up current before overwriting
    if _ITEMS_JSON.exists():
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(_ITEMS_JSON, _BACKUP_DIR / f"pw_items_{ts}.json.bak")

    shutil.copy2(src, _ITEMS_JSON)
    _clear_item_cache()
    return {"success": True, "item_count": _item_count(_ITEMS_JSON)}


@router.delete("/items-backup/{filename}")
async def items_backup_delete(filename: str, user: dict = Depends(require_admin)):
    if not _BAK_RE.match(filename):
        raise HTTPException(400, detail="Invalid filename")
    target = _BACKUP_DIR / filename
    if not target.exists():
        raise HTTPException(404, detail="Backup not found")
    target.unlink()
    return {"success": True}


@router.post("/upload-elements")
async def upload_elements(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if not file.filename or not file.filename.endswith(".data"):
        raise HTTPException(400, detail="File must be a .data file")
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    # Destination is always the fixed path — never derived from the uploaded filename
    dest = _UPLOADED_EL.resolve()
    # Guard: refuse if dest somehow resolves to the live game file
    game_el = Path(f"{settings.server_path.rstrip('/')}/gamed/config/elements.data").resolve()
    if dest == game_el:
        raise HTTPException(500, detail="Upload destination collision with live game file — check SERVER_PATH config")
    content = await file.read()
    if len(content) < 1024:
        raise HTTPException(400, detail="File too small to be a valid elements.data")
    dest.write_bytes(content)
    return {"success": True, "size_mb": round(len(content) / 1024 / 1024, 1)}


@router.get("/item-configs")
async def item_configs(user: dict = Depends(require_admin)):
    """List available elements.data configs and auto-detect the right one."""
    import sys as _sys
    _sys.path.insert(0, str(_TOOL.parent))
    from generate_items import list_configs, detect_config as _detect

    configs = list_configs()

    server_el = f"{settings.server_path.rstrip('/')}/gamed/config/elements.data"
    el_path = server_el if Path(server_el).exists() else (
        str(_UPLOADED_EL) if _UPLOADED_EL.exists() else None
    )
    detected = _detect(el_path) if el_path else None

    return {"configs": configs, "detected": detected}


class RegenerateBody(BaseModel):
    config: str = ""


@router.post("/regenerate-items")
async def regenerate_items(body: RegenerateBody = RegenerateBody(), user: dict = Depends(require_admin)):
    """Regenerate pw_items.json from elements.data (server path or uploaded file)."""
    # Prefer server's own file, fall back to uploaded
    server_el = f"{settings.server_path.rstrip('/')}/gamed/config/elements.data"
    if Path(server_el).exists():
        elements_path = server_el
    elif _UPLOADED_EL.exists():
        elements_path = str(_UPLOADED_EL)
    else:
        raise HTTPException(
            404,
            detail=(
                f"elements.data not found at server path ({server_el}) "
                "and no uploaded file exists. Upload elements.data first."
            ),
        )
    if not _TOOL.exists():
        raise HTTPException(500, detail="generate_items.py tool not found")

    # Backup existing with timestamp
    if _ITEMS_JSON.exists():
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(_ITEMS_JSON, _BACKUP_DIR / f"pw_items_{ts}.json.bak")

    cfg_name = body.config.strip() if body.config else ""

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_generate, elements_path, cfg_name)
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    _clear_item_cache()
    return result


def _run_generate(elements_path: str, cfg_name: str = "") -> dict:
    import subprocess
    cmd = [sys.executable, str(_TOOL), "--source", "elements",
           "--elements", elements_path, "--no-backup"]
    if cfg_name:
        cmd += ["--config", cfg_name]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "generator failed")
    data = json.loads(_ITEMS_JSON.read_text(encoding="utf-8"))
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
