from fastapi import APIRouter

router = APIRouter(
    prefix="/rooms",
    tags=["Rooms"],
)


@router.get("/ping")
def rooms_ping():
    return {
        "status": "ok",
        "module": "rooms",
    }
