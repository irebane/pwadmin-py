from fastapi import APIRouter, Depends
from app.deps import require_admin

router = APIRouter(prefix="/api/maps")


@router.get("/status")
async def maps_status(user: dict = Depends(require_admin)):
    return {"zones": []}


@router.post("/control")
async def maps_control(user: dict = Depends(require_admin)):
    return {"success": False, "message": "Not implemented"}
