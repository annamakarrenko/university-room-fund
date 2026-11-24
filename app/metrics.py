from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "urf_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)

HTTP_ERRORS = Counter(
    "urf_http_errors_total",
    "Total HTTP client and server errors",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)

HTTP_DURATION = Histogram(
    "urf_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(
        0.005, 0.01, 0.025, 0.05,
        0.1, 0.25, 0.5, 1,
        2.5, 5, 10,
    ),
    registry=REGISTRY,
)

APPLICATION_UP = Gauge(
    "urf_application_up",
    "Application process availability",
    registry=REGISTRY,
)

DATABASE_UP = Gauge(
    "urf_database_up",
    "Database availability",
    registry=REGISTRY,
)

ROOMS_TOTAL = Gauge(
    "urf_rooms_total",
    "Number of rooms in the database",
    registry=REGISTRY,
)

APPLICATION_UP.set(1)
DATABASE_UP.set(0)
ROOMS_TOTAL.set(float("nan"))


def observe_request(method, path, status_code, duration):
    if path in {"/metrics", "/health", "/ready"}:
        return

    code = str(status_code)

    HTTP_REQUESTS.labels(
        method=method,
        path=path,
        status_code=code,
    ).inc()

    HTTP_DURATION.labels(
        method=method,
        path=path,
    ).observe(duration)

    if status_code >= 400:
        HTTP_ERRORS.labels(
            method=method,
            path=path,
            status_code=code,
        ).inc()
