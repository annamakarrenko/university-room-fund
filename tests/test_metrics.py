import math

from prometheus_client.parser import text_string_to_metric_families
from sqlalchemy.exc import OperationalError


def metric_value(client, name, labels=None):
    response = client.get("/metrics")
    assert response.status_code == 200

    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            if sample.name != name:
                continue

            if labels is None or sample.labels == labels:
                return sample.value

    return 0.0


def test_metrics_endpoint(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["Content-Type"]
    assert "urf_application_up 1.0" in response.text
    assert "urf_database_up 1.0" in response.text

    for name in (
        "urf_http_requests_total",
        "urf_http_errors_total",
        "urf_http_request_duration_seconds",
        "urf_rooms_total",
    ):
        assert name in response.text


def test_request_counter(client):
    labels = {
        "method": "GET",
        "path": "/version",
        "status_code": "200",
    }

    before = metric_value(
        client, "urf_http_requests_total", labels
    )

    assert client.get("/version").status_code == 200

    after = metric_value(
        client, "urf_http_requests_total", labels
    )

    assert after == before + 1


def test_error_counter(client):
    labels = {
        "method": "GET",
        "path": "unmatched",
        "status_code": "404",
    }

    before = metric_value(
        client, "urf_http_errors_total", labels
    )

    assert client.get("/metrics-test-unknown").status_code == 404

    after = metric_value(
        client, "urf_http_errors_total", labels
    )

    assert after == before + 1


def test_request_duration_histogram(client):
    labels = {
        "method": "GET",
        "path": "/version",
    }

    before = metric_value(
        client,
        "urf_http_request_duration_seconds_count",
        labels,
    )

    assert client.get("/version").status_code == 200

    after = metric_value(
        client,
        "urf_http_request_duration_seconds_count",
        labels,
    )

    assert after == before + 1

    assert metric_value(
        client,
        "urf_http_request_duration_seconds_sum",
        labels,
    ) > 0


def test_database_readiness(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "ok"
    assert metric_value(client, "urf_database_up") == 1


def test_database_unavailable(client, monkeypatch):
    def unavailable_database():
        raise OperationalError(
            "database unavailable", {}, RuntimeError()
        )

    monkeypatch.setattr(
        "app.routers.monitoring.SessionLocal",
        unavailable_database,
    )

    assert client.get("/health").status_code == 200

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"

    assert metric_value(client, "urf_database_up") == 0

    assert math.isnan(
        metric_value(client, "urf_rooms_total")
    )


def test_business_rooms_metric(client):
    from app.database import SessionLocal
    from app.models import Building, Department, Room

    assert metric_value(client, "urf_rooms_total") == 0

    with SessionLocal() as db:
        building = Building(
            name="Test building",
            address="Test address",
        )
        department = Department(name="Test department")

        db.add_all([building, department])
        db.flush()

        room = Room(
            number="101",
            area=45.0,
            capacity=30,
            building_id=building.id,
            department_id=department.id,
            room_type="classroom",
            is_active=True,
        )

        db.add(room)
        db.commit()

        room_id = room.id

    assert metric_value(client, "urf_rooms_total") == 1

    with SessionLocal() as db:
        db.delete(db.get(Room, room_id))
        db.commit()

    assert metric_value(client, "urf_rooms_total") == 0
