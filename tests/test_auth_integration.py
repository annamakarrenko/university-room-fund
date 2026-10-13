def test_protected_endpoint_requires_authentication(client):
    response = client.get("/rooms")

    assert response.status_code == 401


def test_duplicate_username_returns_409(client):
    payload = {
        "username": "anna_test",
        "password": "password123",
    }

    first_response = client.post("/auth/register", json=payload)

    client.post("/auth/logout")

    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_wrong_password_returns_401(client):
    client.post(
        "/auth/register",
        json={
            "username": "anna_test",
            "password": "password123",
        },
    )

    client.post("/auth/logout")

    response = client.post(
        "/auth/login",
        json={
            "username": "anna_test",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401