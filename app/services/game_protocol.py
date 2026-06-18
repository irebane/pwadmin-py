"""High-level game operations built on top of GameClient."""
from app.services.game_client import GameClient
from app.config import settings

_client: GameClient | None = None


def get_client() -> GameClient:
    global _client
    if _client is None:
        _client = GameClient(host="localhost", port=settings.server_port)
    return _client
