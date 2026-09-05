from pydantic import BaseModel, ConfigDict

class BuildingCreate(BaseModel):
    name: str
    address: str

class BuildingResponse(BaseModel):
    id: int
    name: str
    address: str

    model_config = ConfigDict(from_attributes=True)

class BuildingUpdate(BaseModel):
    name: str
    address: str