import json
import logging
from datetime import datetime
from io import StringIO
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability import ObservabilityMiddleware, logger


@pytest.fixture
def log_stream():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)

    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        handler.close()


def read_logs(stream):
    return [
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if line.strip()
    ]


def test_structured_request_log(client, log_stream):
    response = client.get("/health")

    assert response.status_code == 200

    record = read_logs(log_stream)[-1]

    required_fields = {
        "timestamp",
        "level",
        "event",
        "method",
        "path",
        "status_code",
        "result",
        "request_id",
        "duration_ms",
    }

    assert required_fields <= record.keys()
    assert record["level"] == "INFO"
    assert record["event"] == "http_request"
    assert record["method"] == "GET"
    assert record["path"] == "/health"
    assert record["status_code"] == 200
    assert record["result"] == "success"
    assert record["duration_ms"] >= 0

    datetime.fromisoformat(record["timestamp"])
    UUID(record["request_id"])

    assert record["request_id"] == response.headers["X-Request-ID"]


def test_unique_request_ids(client):
    first = client.get("/health")
    second = client.get("/health")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_client_errors_are_logged(client, log_stream):
    response = client.get("/rooms")
    assert response.status_code == 401

    record = read_logs(log_stream)[-1]

    assert record["level"] == "WARNING"
    assert record["result"] == "client_error"
    assert record["status_code"] == 401

    response = client.get("/unknown-test-route")
    assert response.status_code == 404

    record = read_logs(log_stream)[-1]

    assert record["path"] == "unmatched"
    assert record["status_code"] == 404


def test_secrets_are_not_logged(client, log_stream):
    password = "lab8-test-password-marker"
    token = "lab8-test-token-marker"
    cookie = "lab8-test-cookie-marker"
    query = "lab8-test-query-marker"

    response = client.post(
        f"/auth/login?token={query}",
        json={
            "username": "observability_test",
            "password": password,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Cookie": f"session={cookie}",
            "X-Request-ID": token,
        },
    )

    assert response.status_code == 401

    output = log_stream.getvalue()

    for secret in (password, token, cookie, query):
        assert secret not in output

    record = read_logs(log_stream)[-1]
    assert record["path"] == "/auth/login"
    assert record["request_id"] == response.headers["X-Request-ID"]


def test_server_error_does_not_leak_secret(log_stream):
    test_app = FastAPI()
    test_app.add_middleware(ObservabilityMiddleware)

    secret = uuid4().hex

    @test_app.get("/failure")
    def failure():
        raise RuntimeError(secret)

    with TestClient(test_app) as test_client:
        response = test_client.get("/failure")

    assert response.status_code == 500
    assert secret not in response.text
    assert secret not in log_stream.getvalue()

    record = read_logs(log_stream)[-1]

    assert record["level"] == "ERROR"
    assert record["event"] == "http_request_exception"
    assert record["result"] == "server_error"
    assert record["status_code"] == 500
    assert record["request_id"] == response.headers["X-Request-ID"]
