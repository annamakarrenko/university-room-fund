import json
import logging
import sys
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

from app.metrics import observe_request

logger = logging.getLogger("urf.observability")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

HTTP_METHODS = {
    "GET", "POST", "PUT", "PATCH",
    "DELETE", "HEAD", "OPTIONS",
}


class ObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        started_at = perf_counter()
        status_code = 500
        response_started = False
        event = "http_request"

        scope.setdefault("state", {})["request_id"] = request_id

        async def send_response(message):
            nonlocal status_code, response_started

            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                response_started = True

            await send(message)

        try:
            await self.app(scope, receive, send_response)
        # HTTP boundary: prevent sensitive exception details from leaking.
        except Exception:  # noqa: BLE001
            event = "http_request_exception"

            if response_started:
                raise RuntimeError(
                    "Response processing failed"
                ) from None

            response = JSONResponse(
                {"detail": "Internal server error"},
                status_code=500,
            )
            await response(scope, receive, send_response)
        finally:
            route = scope.get("route")
            path = getattr(route, "path", "unmatched")

            method = scope.get("method", "OTHER")
            if method not in HTTP_METHODS:
                method = "OTHER"

            if status_code >= 500 or event == "http_request_exception":
                level = "ERROR"
                result = "server_error"
            elif status_code >= 400:
                level = "WARNING"
                result = "client_error"
            else:
                level = "INFO"
                result = "success"

            duration = perf_counter() - started_at

            observe_request(
                method, path, status_code, duration
            )

            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level,
                "event": event,
                "method": method,
                "path": path,
                "status_code": status_code,
                "result": result,
                "request_id": request_id,
                "duration_ms": round(
                    duration * 1000,
                    3,
                ),
            }

            logger.log(
                getattr(logging, level),
                json.dumps(record, ensure_ascii=False),
            )
