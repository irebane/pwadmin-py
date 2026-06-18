from fastapi import APIRouter, Depends, HTTPException
from app.deps import get_current_user
from app.config import settings

router = APIRouter()


def _get_game_client():
    try:
        from app.services.game_client import GameClient
        return GameClient(host="localhost", port=settings.server_port)
    except Exception:
        return None


@router.get("/api/accounts/{user_id}/characters")
async def get_characters(user_id: int, user: dict = Depends(get_current_user)):
    if not user.get("is_admin") and user["id"] != user_id:
        raise HTTPException(403)
    client = _get_game_client()
    if client is None:
        return []
    return await client.get_user_roles(user_id)


@router.get("/api/characters/{role_id}")
async def get_character(role_id: int, user: dict = Depends(get_current_user)):
    client = _get_game_client()
    if client is None:
        return None
    return await client.get_role_data(role_id, server_ver=75)
