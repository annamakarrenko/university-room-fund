def register_user(client, username="anna_test"):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "password123",
        },
    )


def test_health_and_web_interface(client):
    health_response = client.get("/health")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"

    page_response = client.get("/")

    assert page_response.status_code == 200
    assert "UniSpace" in page_response.text


def test_authentication_workflow(client):
    unauthorized_response = client.get("/buildings")

    assert unauthorized_response.status_code == 401

    register_response = register_user(client)

    assert register_response.status_code == 201
    assert register_response.json()["username"] == "anna_test"
    assert "password_hash" not in register_response.json()

    current_user_response = client.get("/auth/me")

    assert current_user_response.status_code == 200
    assert current_user_response.json()["username"] == "anna_test"

    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 204
    assert client.get("/buildings").status_code == 401

    wrong_password_response = client.post(
        "/auth/login",
        json={
            "username": "anna_test",
            "password": "wrong-password",
        },
    )

    assert wrong_password_response.status_code == 401

    login_response = client.post(
        "/auth/login",
        json={
            "username": "anna_test",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200
    assert client.get("/buildings").status_code == 200


def test_room_fund_workflow(client):
    assert register_user(client).status_code == 201

    building_response = client.post(
        "/buildings",
        json={
            "name": "Главный корпус",
            "address": "Университетская улица, 1",
        },
    )

    assert building_response.status_code in {200, 201}
    building_id = building_response.json()["id"]

    department_response = client.post(
        "/departments",
        json={
            "name": "Кафедра информационных технологий",
        },
    )

    assert department_response.status_code in {200, 201}
    department_id = department_response.json()["id"]

    invalid_room_response = client.post(
        "/rooms",
        json={
            "number": "101",
            "area": 0,
            "capacity": 30,
            "building_id": building_id,
            "department_id": department_id,
        },
    )

    assert invalid_room_response.status_code == 422

    room_data = {
        "number": "101",
        "area": 45.5,
        "capacity": 30,
        "building_id": building_id,
        "department_id": department_id,
    }

    room_response = client.post(
        "/rooms",
        json=room_data,
    )

    assert room_response.status_code in {200, 201}
    room_id = room_response.json()["id"]

    duplicate_response = client.post(
        "/rooms",
        json=room_data,
    )

    assert duplicate_response.status_code == 409

    rooms_response = client.get("/rooms")

    assert rooms_response.status_code == 200
    assert len(rooms_response.json()) == 1
    assert rooms_response.json()[0]["number"] == "101"

    updated_room = {
        **room_data,
        "area": 50.5,
        "capacity": 35,
    }

    update_response = client.put(
        f"/rooms/{room_id}",
        json=updated_room,
    )

    assert update_response.status_code == 200
    assert update_response.json()["area"] == 50.5
    assert update_response.json()["capacity"] == 35

    delete_response = client.delete(
        f"/rooms/{room_id}",
    )

    assert delete_response.status_code in {200, 204}
    assert client.get("/rooms").json() == []