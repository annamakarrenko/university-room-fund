"""Check a deployed University Room Fund release."""

import argparse
import json
import secrets
import urllib.error
import urllib.request
from http.cookiejar import CookieJar


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:18080",
    )
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar())
    )

    def request(method, path, payload=None, expected=200):
        body = None
        headers = {}

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            base_url + path,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with opener.open(req, timeout=10) as response:
                status = response.status
                content = response.read()
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"{method} {path}: HTTP {error.code}"
            ) from error

        if status != expected:
            raise RuntimeError(
                f"{method} {path}: expected {expected}, got {status}"
            )

        return json.loads(content) if content else None

    print("Checking health...")
    health = request("GET", "/health")
    assert health["status"] == "ok"
    print("PASS: health")

    print("Checking version...")
    version = request("GET", "/version")
    assert version["version"] == args.expected_sha, (
        "Release SHA mismatch"
    )
    print("PASS: version")

    username = "smoke_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(20)

    print("Registering test user...")
    user = request(
        "POST",
        "/auth/register",
        {"username": username, "password": password},
        expected=201,
    )
    assert user["username"] == username
    print("PASS: registration")

    print("Creating building...")
    building = request(
        "POST",
        "/buildings",
        {
            "name": "Lab6 Smoke Building",
            "address": "Staging test",
        },
        expected=201,
    )
    building_id = building["id"]

    print("Creating department...")
    department = request(
        "POST",
        "/departments",
        {"name": "Lab6 Smoke Department"},
        expected=201,
    )
    department_id = department["id"]

    print("Creating room...")
    room = request(
        "POST",
        "/rooms",
        {
            "number": "SMOKE-101",
            "area": 45.5,
            "capacity": 30,
            "building_id": building_id,
            "department_id": department_id,
        },
        expected=201,
    )

    print("Reading room...")
    actual = request("GET", f"/rooms/{room['id']}")
    assert actual["number"] == "SMOKE-101"
    assert actual["area"] == 45.5
    assert actual["building_id"] == building_id
    assert actual["department_id"] == department_id
    print("PASS: main user scenario")

    print("Cleaning up test records...")
    request("DELETE", f"/rooms/{room['id']}", expected=204)
    request("DELETE", f"/buildings/{building_id}", expected=204)
    request("DELETE", f"/departments/{department_id}", expected=204)
    print("PASS: cleanup")

    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
