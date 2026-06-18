import asyncio
from fastapi import APIRouter, Depends, HTTPException
from app.deps import require_admin
from app.services.server_config import read_game_config, save_game_config
from app.services.server_status import get_server_status, get_maps_status
from pydantic import BaseModel

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


class ControlBody(BaseModel):
    action: str  # start | stop | restart


@router.post("/control")
async def server_control(body: ControlBody, user: dict = Depends(require_admin)):
    if body.action not in ("start", "stop", "restart"):
        raise HTTPException(400, detail="Invalid action")
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "systemctl", body.action, "pwserver",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            raise HTTPException(500, detail=stderr.decode().strip() or f"systemctl {body.action} failed")
        return {"success": True}
    except asyncio.TimeoutError:
        raise HTTPException(504, detail="systemctl timed out")
