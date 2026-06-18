import secrets
from fastapi import Request, HTTPException


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def validate_csrf(request: Request, token: str) -> None:
    session_token = request.cookies.get("csrf_token")
    if not session_token or not secrets.compare_digest(session_token, token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
