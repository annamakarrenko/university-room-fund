from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.buildings import router as buildings_router
from app.routers.departments import router as departments_router
from app.routers.rooms import router as rooms_router

Base.metadata.create_all(bind=engine)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="University Room Fund",
    description="API для учета аудиторного фонда университета",
    version="0.1.0",
)

app.include_router(buildings_router)
app.include_router(departments_router)
app.include_router(rooms_router)
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "university-room-fund",
    }
