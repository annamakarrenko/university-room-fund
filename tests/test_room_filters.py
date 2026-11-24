from uuid import uuid4

import pytest


@pytest.fixture
def room_dataset(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "filter_user",
            "password": uuid4().hex,
        },
    )
    assert response.status_code == 201

    buildings = []

    for name in ("Building A", "Building B"):
        response = client.post(
            "/buildings",
            json={
                "name": name,
                "address": "Test address",
            },
        )
        assert response.status_code == 201
        buildings.append(response.json()["id"])

    response = client.post(
        "/departments",
        json={"name": "Test department"},
    )
    assert response.status_code == 201
    department_id = response.json()["id"]

    rooms = [
        ("101", 20, "classroom", True, buildings[0]),
        ("102", 40, "classroom", True, buildings[0]),
        ("103", 60, "laboratory", False, buildings[0]),
        ("201", 50, "classroom", True, buildings[1]),
        ("202", 10, "laboratory", False, buildings[1]),
    ]

    for number, capacity, room_type, active, building in rooms:
        response = client.post(
            "/rooms",
            json={
                "number": number,
                "area": 50,
                "capacity": capacity,
                "room_type": room_type,
                "is_active": active,
                "building_id": building,
                "department_id": department_id,
            },
        )
        assert response.status_code == 201

    return buildings


def room_numbers(client, params=None):
    response = client.get("/rooms", params=params)
    assert response.status_code == 200

    return {room["number"] for room in response.json()}


def test_rooms_without_filters(client, room_dataset):
    assert room_numbers(client) == {
        "101", "102", "103", "201", "202",
    }


def test_filter_min_capacity(client, room_dataset):
    assert room_numbers(
        client, {"min_capacity": 40}
    ) == {"102", "103", "201"}


def test_filter_room_type(client, room_dataset):
    assert room_numbers(
        client, {"room_type": "laboratory"}
    ) == {"103", "202"}


def test_filter_active_rooms(client, room_dataset):
    assert room_numbers(
        client, {"is_active": "true"}
    ) == {"101", "102", "201"}


def test_filter_inactive_rooms(client, room_dataset):
    assert room_numbers(
        client, {"is_active": "false"}
    ) == {"103", "202"}


def test_filter_building(client, room_dataset):
    assert room_numbers(
        client, {"building_id": room_dataset[1]}
    ) == {"201", "202"}


def test_combined_filters(client, room_dataset):
    assert room_numbers(
        client,
        {
            "min_capacity": 30,
            "room_type": "classroom",
            "is_active": "true",
            "building_id": room_dataset[0],
        },
    ) == {"102"}


def test_filter_without_matches(client, room_dataset):
    assert room_numbers(
        client, {"min_capacity": 1000}
    ) == set()


@pytest.mark.parametrize(
    "params",
    [
        {"min_capacity": -1},
        {"min_capacity": "invalid"},
        {"building_id": 0},
        {"building_id": -1},
        {"room_type": ""},
        {"room_type": "x" * 31},
        {"is_active": "invalid"},
    ],
)
def test_invalid_filter_parameters(client, room_dataset, params):
    response = client.get("/rooms", params=params)
    assert response.status_code == 422


def test_filters_require_authentication(client):
    response = client.get(
        "/rooms",
        params={"min_capacity": 30},
    )
    assert response.status_code == 401
