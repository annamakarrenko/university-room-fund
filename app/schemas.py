from pydantic import BaseModel, ConfigDict, Field

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

class DepartmentCreate(BaseModel):
    name: str

class DepartmentUpdate(BaseModel):
    name: str

class DepartmentResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class RoomCreate(BaseModel):
    number: str
    area: float = Field(gt=0)
    capacity: int = Field(ge=0)
    building_id: int
    department_id: int


class RoomUpdate(BaseModel):
    number: str
    area: float = Field(gt=0)
    capacity: int = Field(ge=0)
    building_id: int
    department_id: int


class RoomResponse(BaseModel):
    id: int
    number: str
    area: float
    capacity: int
    building_id: int
    department_id: int

    model_config = ConfigDict(from_attributes=True)
