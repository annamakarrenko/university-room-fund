from fastapi import FastAPI

from app.database import Base, engine
from app.routers.buildings import router as buildings_router
from app.routers.departments import router as departments_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="University Room Fund",
    description="API для учета аудиторного фонда университета",
    version="0.1.0",
)

app.include_router(buildings_router)
app.include_router(departments_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "university-room-fund",
    }