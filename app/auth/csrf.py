import secrets
from fastapi import Request, HTTPException


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def validate_csrf(request: Request) -> None:
    """Validate CSRF for state-changing requests via double-submit cookie pattern."""
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")
    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
