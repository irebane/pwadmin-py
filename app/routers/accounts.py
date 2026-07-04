from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db, get_current_user, require_admin
from app.services.accounts import (
    load_account_v2, load_chars_v2, load_deleted_chars_v2, list_accounts_v2, account_tool_v2, account_save_v2,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/accounts")


class LoadBody(BaseModel):
    id: int = 0


@router.post("/load")
async def account_load(
    body: LoadBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not user.get("is_admin") and user.get("id") != body.id:
        return JSONResponse([{"error": "Unauthorized."}])
    result = await load_account_v2(
        db, body.id,
        viewer_is_admin=user.get("is_admin", False),
        viewer_id=user.get("id", 0),
        viewer_pw=user.get("pw", ""),
    )
    return JSONResponse(result)


@router.post("/chars")
async def account_chars(
    body: LoadBody,
    user: dict = Depends(get_current_user),
):
    if not user.get("is_admin") and user.get("id") != body.id:
        return JSONResponse({"error": "Unauthorized."})
    chars = await load_chars_v2(body.id)
    return JSONResponse(chars)


@router.post("/chars/deleted")
async def account_deleted_chars(
    body: LoadBody,
    user: dict = Depends(require_admin),
):
    chars = await load_deleted_chars_v2(body.id)
    return JSONResponse(chars)


class ListBody(BaseModel):
    sname: str = ""
    stype: int = 1


@router.post("/list")
async def account_list(
    body: ListBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    result = await list_accounts_v2(db, body.sname, body.stype)
    return JSONResponse(result)


class ToolBody(BaseModel):
    tool: int = 0
    id: int = 0
    amount: int = 0
    day: int = 0
    bannerid: int = 0
    targetid: int = 0
    bantype: int = 0
    gmid: int = 0
    banreason: str = ""
    bandur: int = 0


@router.post("/tool")
async def account_tool(
    body: ToolBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    result = await account_tool_v2(db, body.tool, body.model_dump(), is_admin=True)
    return JSONResponse(result)


class SaveBody(BaseModel):
    NameStack: str = ""
    PasswordStack: str = ""
    Email: str = ""
    RealName: str = ""
    Gender: int = 0
    DateYMD: str = ""
    Rank: int = 0


@router.post("/save")
async def account_save(
    body: SaveBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await account_save_v2(
        db, user,
        body.NameStack, body.PasswordStack,
        body.Email, body.RealName,
        body.Gender, body.DateYMD, body.Rank,
    )
    return JSONResponse(result)
