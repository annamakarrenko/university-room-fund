from pydantic import BaseModel, ConfigDict, Field


class BuildingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)

class BuildingResponse(BaseModel):
    id: int
    name: str
    address: str

    model_config = ConfigDict(from_attributes=True)

class BuildingUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class DepartmentUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class DepartmentResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class RoomCreate(BaseModel):
    number: str = Field(min_length=1, max_length=20)
    area: float = Field(gt=0)
    capacity: int = Field(ge=0)
    building_id: int
    department_id: int


class RoomUpdate(BaseModel):
    number: str = Field(min_length=1, max_length=20)
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


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)
