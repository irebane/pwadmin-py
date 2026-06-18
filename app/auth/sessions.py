from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response
from app.config import settings

SESSION_MAX_AGE = 8 * 3600
COOKIE_NAME = "pwa_session"

_signer = URLSafeTimedSerializer(settings.secret_key, salt="session")


def create_session(response: Response, data: dict) -> None:
    token = _signer.dumps(data)
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=False,
    )


def read_session(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return _signer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)
