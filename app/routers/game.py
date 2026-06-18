from fastapi import APIRouter, Depends
from app.deps import require_admin
from app.services.game_client import GameClient
from app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/api/game")
_client = GameClient(host="localhost", port=settings.server_port)


@router.get("/online")
async def online_players(user: dict = Depends(require_admin)):
    return await _client.get_online_roles()


@router.get("/guilds")
async def guilds(user: dict = Depends(require_admin)):
    return await _client.get_guilds()


@router.delete("/guilds/{guild_id}")
async def delete_guild(guild_id: int, user: dict = Depends(require_admin)):
    return {"success": await _client.delete_guild(guild_id)}


class MailBody(BaseModel):
    role_id: int
    subject: str
    content: str


@router.post("/mail")
async def send_mail(body: MailBody, user: dict = Depends(require_admin)):
    return {"success": await _client.send_mail(body.role_id, body.subject, body.content)}
