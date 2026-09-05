from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building, Department, Room
from app.schemas import RoomCreate, RoomResponse, RoomUpdate

router = APIRouter(
    prefix="/rooms",
    tags=["Rooms"],
)


def validate_references(
    building_id: int,
    department_id: int,
    db: Session,
):
    building = db.get(Building, building_id)
    if building is None:
        raise HTTPException(
            status_code=404,
            detail="Building not found",
        )

    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found",
        )


@router.post(
    "",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room(
    data: RoomCreate,
    db: Session = Depends(get_db),
):
    validate_references(
        data.building_id,
        data.department_id,
        db,
    )

    room = Room(
        number=data.number,
        area=data.area,
        capacity=data.capacity,
        building_id=data.building_id,
        department_id=data.department_id,
    )

    db.add(room)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Room number already exists in this building",
        )

    db.refresh(room)
    return room


@router.get("", response_model=list[RoomResponse])
def get_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
):
    room = db.get(Room, room_id)

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    return room


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    data: RoomUpdate,
    db: Session = Depends(get_db),
):
    room = db.get(Room, room_id)

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    validate_references(
        data.building_id,
        data.department_id,
        db,
    )

    room.number = data.number
    room.area = data.area
    room.capacity = data.capacity
    room.building_id = data.building_id
    room.department_id = data.department_id

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Room number already exists in this building",
        )

    db.refresh(room)
    return room


@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
):
    room = db.get(Room, room_id)

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    db.delete(room)
    db.commit()
