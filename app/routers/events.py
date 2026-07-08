from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from app.deps import require_admin
from app.services.events import parse_gm_activity_config

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/events")
async def events_page(request: Request):
    from app.auth.sessions import read_session as _rs
    from fastapi.responses import RedirectResponse
    if not (_rs(request) or {}).get("is_admin"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "events/index.html", {"is_admin": True})


@router.get("/api/events")
async def list_events(user: dict = Depends(require_admin)):
    return parse_gm_activity_config()
