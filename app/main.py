from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.routers import auth, accounts, characters, game, maps, gshop, items, server, activity_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="pwadmin-py", lifespan=lifespan)
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
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/account")
async def account_page(request: Request):
    return templates.TemplateResponse("account/index.html", {"request": request})


@app.get("/gshop")
async def gshop_page(request: Request):
    return templates.TemplateResponse("gshop/index.html", {"request": request})


@app.get("/server")
async def server_page(request: Request):
    return templates.TemplateResponse("server/index.html", {"request": request})


@app.get("/item-builder")
async def item_builder_page(request: Request):
    return templates.TemplateResponse("item_builder/index.html", {"request": request})
