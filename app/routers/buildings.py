from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building
from app.schemas import BuildingCreate, BuildingResponse, BuildingUpdate

router = APIRouter(
    prefix="/buildings",
    tags=["Buildings"],
)

@router.post(
    "",
    response_model=BuildingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_building(
    data: BuildingCreate,
    db: Session = Depends(get_db),
):
    building = Building(
        name=data.name,
        address=data.address,
    )

    db.add(building)
    db.commit()
    db.refresh(building)

    return building

@router.get("", response_model=list[BuildingResponse])
def get_buildings(db: Session = Depends(get_db)):
    return db.query(Building).all()

@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(
    building_id: int,
    db: Session = Depends(get_db),
):
    building = db.get(Building, building_id)

    if building is None:
        raise HTTPException(
            status_code=404,
            detail="Building not found",
        )

    return building

@router.put("/{building_id}", response_model=BuildingResponse)
def update_building(
    building_id: int,
    data: BuildingUpdate,
    db: Session = Depends(get_db),
):
    building = db.get(Building, building_id)

    if building is None:
        raise HTTPException(
            status_code=404,
            detail="Building not found",
        )

    building.name = data.name
    building.address = data.address

    db.commit()
    db.refresh(building)

    return building


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_building(
    building_id: int,
    db: Session = Depends(get_db),
):
    building = db.get(Building, building_id)

    if building is None:
        raise HTTPException(
            status_code=404,
            detail="Building not found",
        )

    db.delete(building)
    db.commit()