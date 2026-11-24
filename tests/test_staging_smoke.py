import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from scripts import staging_smoke

RELEASE_SHA = "a" * 40
BASE_URL = "http://127.0.0.1:18080"


@pytest.mark.parametrize(
    "readiness",
    [
        {"status": "not_ready", "database": "unavailable"},
        {"status": "ready", "database": "unavailable"},
        {"status": "not_ready", "database": "ok"},
    ],
)
def test_smoke_rejects_invalid_readiness(readiness):
    opener = MagicMock()
    health_response = MagicMock()
    ready_response = MagicMock()

    health_response.status = 200
    health_response.read.return_value = json.dumps(
        {"status": "ok"}
    ).encode()

    ready_response.status = 200
    ready_response.read.return_value = json.dumps(
        readiness
    ).encode()

    opener.open.return_value.__enter__.side_effect = [
        health_response,
        ready_response,
    ]

    with (
        patch(
            "sys.argv",
            [
                "staging_smoke.py",
                "--base-url", BASE_URL,
                "--expected-sha", RELEASE_SHA,
            ],
        ),
        patch(
            "urllib.request.build_opener",
            return_value=opener,
        ),
        pytest.raises(
            RuntimeError,
            match="Application or database is not ready",
        ),
    ):
        staging_smoke.main()

    assert opener.open.call_count == 2


def test_smoke_rejects_database_http_503():
    opener = MagicMock()
    health_response = MagicMock()

    health_response.status = 200
    health_response.read.return_value = b'{"status":"ok"}'

    opener.open.side_effect = [
        MagicMock(
            __enter__=MagicMock(
                return_value=health_response
            )
        ),
        HTTPError(
            BASE_URL + "/ready",
            503,
            "Service Unavailable",
            None,
            None,
        ),
    ]

    with (
        patch(
            "sys.argv",
            [
                "staging_smoke.py",
                "--base-url", BASE_URL,
                "--expected-sha", RELEASE_SHA,
            ],
        ),
        patch(
            "urllib.request.build_opener",
            return_value=opener,
        ),
        pytest.raises(
            RuntimeError,
            match="GET /ready: HTTP 503",
        ),
    ):
        staging_smoke.main()

    assert opener.open.call_count == 2
