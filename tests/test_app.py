import os

os.environ["DATABASE_URL"] = "sqlite:///./test_university_fund.db"
os.environ["COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_function():
    client.cookies.clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    engine.dispose()
    try:
        os.remove("test_university_fund.db")
    except FileNotFoundError:
        pass


def register_user(username="student"):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "display_name": "Тестовый пользователь",
            "password": "strong-password",
        },
    )


def test_front_page_and_health_are_public():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "ok"


def test_crud_requires_authentication():
    response = client.get("/buildings")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_register_current_user_and_logout():
    response = register_user()
    assert response.status_code == 201
    assert response.json()["username"] == "student"
    assert "urf_session" in client.cookies

    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_login_rejects_wrong_password_and_accepts_correct_password():
    register_user()
    client.post("/auth/logout")

    wrong = client.post(
        "/auth/login",
        json={"username": "student", "password": "wrong-password"},
    )
    assert wrong.status_code == 401

    success = client.post(
        "/auth/login",
        json={"username": "student", "password": "strong-password"},
    )
    assert success.status_code == 200
    assert success.json()["display_name"] == "Тестовый пользователь"


def test_complete_room_fund_scenario_and_unique_room_rule():
    register_user()
    building = client.post(
        "/buildings",
        json={"name": "Главный корпус", "address": "Университетская, 1"},
    )
    department = client.post(
        "/departments",
        json={"name": "Кафедра информатики"},
    )
    assert building.status_code == 201
    assert department.status_code == 201

    room_data = {
        "number": "А-101",
        "area": 48.5,
        "capacity": 30,
        "building_id": building.json()["id"],
        "department_id": department.json()["id"],
    }
    room = client.post("/rooms", json=room_data)
    duplicate = client.post("/rooms", json=room_data)

    assert room.status_code == 201
    assert duplicate.status_code == 409
    assert client.get("/rooms").json()[0]["area"] == 48.5
    assert len(client.get(f"/buildings/{building.json()['id']}/rooms").json()) == 1


def test_room_validation_rejects_invalid_values():
    register_user()
    response = client.post(
        "/rooms",
        json={
            "number": "101",
            "area": 0,
            "capacity": -1,
            "building_id": 1,
            "department_id": 1,
        },
    )
    assert response.status_code == 422


def test_building_with_rooms_cannot_be_deleted():
    register_user()
    building = client.post(
        "/buildings",
        json={"name": "Корпус Б", "address": "Университетская, 2"},
    ).json()
    department = client.post(
        "/departments",
        json={"name": "Учебный отдел"},
    ).json()
    client.post(
        "/rooms",
        json={
            "number": "201",
            "area": 35,
            "capacity": 24,
            "building_id": building["id"],
            "department_id": department["id"],
        },
    )

    response = client.delete(f"/buildings/{building['id']}")
    assert response.status_code == 409
