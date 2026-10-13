import pytest
from pydantic import ValidationError

from app.schemas import RoomCreate, UserRegister


def test_room_area_must_be_positive():
    with pytest.raises(ValidationError):
        RoomCreate(
            number="101",
            area=0,
            capacity=20,
            building_id=1,
            department_id=1,
        )


def test_room_area_cannot_be_negative():
    with pytest.raises(ValidationError):
        RoomCreate(
            number="101",
            area=-1,
            capacity=20,
            building_id=1,
            department_id=1,
        )


def test_room_capacity_cannot_be_negative():
    with pytest.raises(ValidationError):
        RoomCreate(
            number="101",
            area=30,
            capacity=-1,
            building_id=1,
            department_id=1,
        )


def test_room_capacity_can_be_zero():
    room = RoomCreate(
        number="101",
        area=30,
        capacity=0,
        building_id=1,
        department_id=1,
    )

    assert room.capacity == 0


def test_username_too_short():
    with pytest.raises(ValidationError):
        UserRegister(
            username="ab",
            password="password123",
        )


def test_password_too_short():
    with pytest.raises(ValidationError):
        UserRegister(
            username="anna",
            password="1234567",
        )

def test_room_number_cannot_be_empty():
    with pytest.raises(ValidationError):
        RoomCreate(
            number="",
            area=30,
            capacity=20,
            building_id=1,
            department_id=1,
        )


def test_room_number_cannot_exceed_20_characters():
    with pytest.raises(ValidationError):
        RoomCreate(
            number="123456789012345678901",
            area=30,
            capacity=20,
            building_id=1,
            department_id=1,
        )


def test_room_number_with_20_characters_is_allowed():
    room = RoomCreate(
        number="12345678901234567890",
        area=30,
        capacity=20,
        building_id=1,
        department_id=1,
    )

    assert len(room.number) == 20