from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.deps import get_db
from app.auth.passwords import verify_password_compat, hash_password_compat
from app.auth.sessions import create_session, clear_session
from app.auth.csrf import generate_csrf_token
from app.models.users import User
from app.models.audit import LoginAttempt
from app.config import settings
from pydantic import BaseModel

router = APIRouter()

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host

    cutoff = datetime.utcnow() - timedelta(minutes=LOCKOUT_MINUTES)
    recent_failures = await db.scalar(
        select(func.count()).where(
            LoginAttempt.ip == ip,
            LoginAttempt.username == body.username.lower(),
            LoginAttempt.success == 0,
            LoginAttempt.attempted_at >= cutoff,
        )
    )
    if recent_failures >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")

    username = body.username.lower().strip()
    result = await db.execute(select(User).where(User.name == username))
    user = result.scalar_one_or_none()

    success = False
    is_admin = False

    if user and verify_password_compat(username, body.password, user.passwd, settings.pass_type):
        success = True
        if user.ID == settings.admin_id:
            is_admin = verify_password_compat(username, body.password, settings.admin_pw, settings.pass_type)

    db.add(LoginAttempt(ip=ip, username=username, success=int(success)))
    await db.commit()

    if not success:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_data = {
        "id": user.ID,
        "name": user.name,
        "email": user.email,
        "pw": body.password,  # store plaintext like PHP ($_SESSION['pw'] = $p)
        "is_admin": is_admin,
    }
    create_session(response, session_data)
    csrf_token = generate_csrf_token()
    response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="strict")
    return {"success": True, "is_admin": is_admin}


@router.post("/api/logout")
async def logout(response: Response):
    clear_session(response)
    response.delete_cookie("csrf_token")
    return {"success": True}


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str


@router.post("/api/register")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    username = body.username.lower().strip()
    if not (4 <= len(username) <= 20) or not username.isalnum():
        raise HTTPException(status_code=400, detail="Username must be 4-20 alphanumeric characters")
    if not (4 <= len(body.password) <= 20) or not body.password.isalnum():
        raise HTTPException(status_code=400, detail="Password must be 4-20 alphanumeric characters")

    exists = await db.scalar(select(func.count()).where(User.name == username))
    if exists:
        raise HTTPException(status_code=409, detail="Username already taken")
    email_exists = await db.scalar(select(func.count()).where(User.email == body.email.lower()))
    if email_exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password_compat(username, body.password, settings.pass_type)

    max_id = await db.scalar(select(func.max(User.ID))) or 0
    new_id = ((max_id // 16) + 1) * 16

    client_ip = request.client.host if request.client else ""
    user = User(
        ID=new_id, name=username, passwd=hashed,
        email=body.email.lower(),
        idnumber=client_ip,
        truename="", Prompt="", answer="",
        creatime=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    return {"success": True}
