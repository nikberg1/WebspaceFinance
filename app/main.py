from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import settings
from app.db import init_db

WEBAPP = Path(__file__).resolve().parent.parent / "webapp"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Studio Cash", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=WEBAPP), name="static")


@app.get("/")
def index():
    return FileResponse(WEBAPP / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "dev_mode": settings.dev_mode}
