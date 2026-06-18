from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.routers import auth, accounts, characters, game, maps, gshop, items, server, activity_log
from app.auth.sessions import read_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


_CSRF_EXEMPT = {"/api/login", "/api/logout", "/api/register"}
_MUTATING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # CSRF double-submit cookie check on all mutating API routes
        if request.method in _MUTATING_METHODS and request.url.path not in _CSRF_EXEMPT:
            cookie_token = request.cookies.get("csrf_token")
            header_token = request.headers.get("X-CSRF-Token")
            import secrets as _sec
            if not cookie_token or not header_token or not _sec.compare_digest(cookie_token, header_token):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)

        response: Response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response


app = FastAPI(title="pwadmin-py", lifespan=lifespan)
app.add_middleware(SecurityHeadersMiddleware)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(characters.router)
app.include_router(game.router)
app.include_router(maps.router)
app.include_router(gshop.router)
app.include_router(items.router)
app.include_router(server.router)
app.include_router(activity_log.router)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/account")
async def account_page(request: Request):
    session = read_session(request) or {}
    return templates.TemplateResponse(request, "account/index.html", {"user_id": session.get("id", 0), "is_admin": session.get("is_admin", False)})


@app.get("/gshop")
async def gshop_page(request: Request):
    return templates.TemplateResponse(request, "gshop/index.html")


@app.get("/server")
async def server_page(request: Request):
    return templates.TemplateResponse(request, "server/index.html")


