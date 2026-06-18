import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from app.deps import require_admin
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
