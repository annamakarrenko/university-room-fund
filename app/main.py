import os

from fastapi import Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.auth import get_current_user
from app.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.buildings import router as buildings_router
from app.routers.departments import router as departments_router
from app.routers.rooms import router as rooms_router

Base.metadata.create_all(bind=engine)

session_secret = os.getenv("SESSION_SECRET")

if not session_secret:
    raise RuntimeError("SESSION_SECRET is not configured")

app = FastAPI(
    title="University Room Fund",
    description="API для учета аудиторного фонда университета",
    version="0.1.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 8,
)

app.include_router(auth_router)

authentication_required = [Depends(get_current_user)]

app.include_router(
    buildings_router,
    dependencies=authentication_required,
)
app.include_router(
    departments_router,
    dependencies=authentication_required,
)
app.include_router(
    rooms_router,
    dependencies=authentication_required,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "university-room-fund",
    }