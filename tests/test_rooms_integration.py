def register_user(client, username="integration_user"):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "password123",
        },
    )


def create_building(client, name="Корпус А"):
    response = client.post(
        "/buildings",
        json={
            "name": name,
            "address": "Москва, ул. Тестовая, 1",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_department(client, name="Кафедра тестирования"):
    response = client.post(
        "/departments",
        json={
            "name": name,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_room_with_missing_building_returns_404(client):
    assert register_user(client).status_code == 201

    department_id = create_department(client)

    response = client.post(
        "/rooms",
        json={
            "number": "101",
            "area": 30,
            "capacity": 20,
            "building_id": 9999,
            "department_id": department_id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Building not found"


def test_room_with_missing_department_returns_404(client):
    assert register_user(client).status_code == 201

    building_id = create_building(client)

    response = client.post(
        "/rooms",
        json={
            "number": "101",
            "area": 30,
            "capacity": 20,
            "building_id": building_id,
            "department_id": 9999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Department not found"


def test_duplicate_room_number_in_same_building_returns_409(client):
    assert register_user(client).status_code == 201

    building_id = create_building(client)
    department_id = create_department(client)

    room = {
        "number": "101",
        "area": 30,
        "capacity": 20,
        "building_id": building_id,
        "department_id": department_id,
    }

    first_response = client.post("/rooms", json=room)
    second_response = client.post("/rooms", json=room)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_same_room_number_allowed_in_different_buildings(client):
    assert register_user(client).status_code == 201

    building_1 = create_building(client, "Корпус А")
    building_2 = create_building(client, "Корпус Б")
    department_id = create_department(client)

    room_1 = {
        "number": "101",
        "area": 30,
        "capacity": 20,
        "building_id": building_1,
        "department_id": department_id,
    }

    room_2 = {
        "number": "101",
        "area": 25,
        "capacity": 15,
        "building_id": building_2,
        "department_id": department_id,
    }

    response_1 = client.post("/rooms", json=room_1)
    response_2 = client.post("/rooms", json=room_2)

    assert response_1.status_code == 201
    assert response_2.status_code == 201


def test_get_missing_room_returns_404(client):
    assert register_user(client).status_code == 201

    response = client.get("/rooms/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"