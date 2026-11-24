from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse, Response

from app.database import SessionLocal
from app.metrics import DATABASE_UP, REGISTRY, ROOMS_TOTAL
from app.models import Room

router = APIRouter(tags=["Monitoring"])


def collect_database_metrics():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            count = db.scalar(
                select(func.count()).select_from(Room)
            )

        DATABASE_UP.set(1)
        ROOMS_TOTAL.set(count)
        return True

    except SQLAlchemyError:
        DATABASE_UP.set(0)
        ROOMS_TOTAL.set(float("nan"))
        return False


@router.get("/ready", include_in_schema=False)
def readiness():
    if collect_database_metrics():
        return {
            "status": "ready",
            "database": "ok",
        }

    return JSONResponse(
        {
            "status": "not_ready",
            "database": "unavailable",
        },
        status_code=503,
    )


@router.get("/metrics", include_in_schema=False)
def metrics():
    collect_database_metrics()

    return Response(
        content=generate_latest(REGISTRY),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
