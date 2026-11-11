#!/usr/bin/env python3
"""Lab 4: validate Docker security and operational requirements."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []


def check(condition, message):
    if condition:
        print(f"[PASS] {message}")
    else:
        print(f"[FAIL] {message}")
        errors.append(message)


def run(*command):
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def pinned_image(value):
    return bool(
        re.fullmatch(
            r"[^\s@]+@sha256:[0-9a-f]{64}",
            value or "",
        )
    ) and ":latest@" not in value.lower()


def main():
    print("=== LAB 4 CONTAINER CHECK ===", flush=True)

    dockerfile = ROOT / "Dockerfile"
    ignore_file = ROOT / ".dockerignore"
    lock_file = ROOT / "requirements.lock"

    check(dockerfile.is_file(), "Dockerfile exists")
    check(ignore_file.is_file(), ".dockerignore exists")
    check(lock_file.is_file(), "requirements.lock exists")

    if not all(p.is_file() for p in
               (dockerfile, ignore_file, lock_file)):
        return 1

    docker_text = dockerfile.read_text()
    ignore_rules = set(ignore_file.read_text().splitlines())
    lock_text = lock_file.read_text()

    from_lines = re.findall(
        r"^\s*FROM\s+(\S+)",
        docker_text,
        re.MULTILINE | re.IGNORECASE,
    )

    check(
        bool(from_lines) and all(
            pinned_image(image) for image in from_lines
        ),
        "Base images pinned by SHA256; latest forbidden",
    )

    users = re.findall(
        r"^\s*USER\s+(.+)$",
        docker_text,
        re.MULTILINE | re.IGNORECASE,
    )

    check(
        bool(users) and users[-1].strip() == "10001:10001",
        "Dockerfile uses non-root UID 10001",
    )

    check(
        bool(re.search(
            r"^\s*STOPSIGNAL\s+SIGTERM\s*$",
            docker_text,
            re.MULTILINE | re.IGNORECASE,
        )),
        "SIGTERM configured",
    )

    check(
        bool(re.search(
            r'^\s*CMD\s+\[\s*"python"',
            docker_text,
            re.MULTILINE | re.IGNORECASE,
        )),
        "Application uses exec-form CMD",
    )

    check(
        "--require-hashes" in docker_text
        and "requirements.lock" in docker_text
        and "--hash=sha256:" in lock_text,
        "Dependencies installed with SHA256 validation",
    )

    check(
        ".env" in ignore_rules
        and ".env.*" in ignore_rules
        and "backups" in ignore_rules
        and ".git" in ignore_rules,
        "Secrets, backups and Git excluded from build context",
    )

    check(
        not re.search(
            r"^\s*(COPY|ADD)\s+.*(?:\.env|id_rsa|\.pem)",
            docker_text,
            re.MULTILINE | re.IGNORECASE,
        ),
        "Dockerfile does not copy known secret files",
    )

    check(
        "SESSION_SECRET=" not in docker_text
        and "DB_PASSWORD=" not in docker_text
        and "POSTGRES_PASSWORD=" not in docker_text,
        "No application secrets defined in Dockerfile",
    )

    result = run("docker", "compose", "config", "--format", "json")

    if result.returncode != 0:
        check(False, "Compose configuration is valid")
        print("Compose configuration failed; inspect with docker compose config -q")
        return 1

    check(True, "Compose configuration is valid")
    config = json.loads(result.stdout)

    services = config.get("services", {})
    networks = config.get("networks", {})
    volumes = config.get("volumes", {})

    check(
        {"app", "db", "migrate"}.issubset(services),
        "Required services exist",
    )

    if not {"app", "db", "migrate"}.issubset(services):
        return 1

    app = services["app"]
    db = services["db"]
    migrate = services["migrate"]

    check(
        pinned_image(db.get("image", "")),
        "PostgreSQL image pinned by SHA256",
    )

    check(
        not db.get("ports"),
        "Database has no published ports",
    )

    app_ports = app.get("ports", [])
    check(
        len(app_ports) == 1
        and str(app_ports[0].get("published")) == "8000"
        and app_ports[0].get("host_ip") == "127.0.0.1",
        "Only application port 8000 published on loopback",
    )

    for name, service in (("app", app), ("db", db)):
        health = service.get("healthcheck") or {}
        check(
            bool(health.get("test"))
            and not health.get("disable", False)
            and health.get("test") != ["NONE"],
            f"{name} healthcheck enabled",
        )

    check(
        bool(db.get("volumes"))
        and any(
            v.get("type") == "volume"
            for v in db["volumes"]
        ),
        "PostgreSQL uses persistent volume",
    )

    check(
        bool(volumes),
        "Named volumes configured",
    )

    backend = next(
        (v for k, v in networks.items()
         if k == "backend" or k.endswith("_backend")),
        {},
    )

    check(
        backend.get("internal") is True,
        "Backend network is internal",
    )

    def network_names(service):
        return set((service.get("networks") or {}).keys())

    check(
        "backend" in network_names(db)
        and "backend" in network_names(app)
        and "frontend" in network_names(app),
        "Application and database networks configured",
    )

    db_dependency = migrate.get("depends_on", {}).get("db", {})
    migrate_dependency = app.get("depends_on", {}).get("migrate", {})

    check(
        db_dependency.get("condition") == "service_healthy"
        and migrate_dependency.get("condition")
        == "service_completed_successfully",
        "Startup order: database, migrations, application",
    )

    for name, service in services.items():
        check(
            service.get("mem_limit") is not None
            and float(service.get("cpus", 0)) > 0,
            f"{name} CPU and memory limits configured",
        )

    check(
        all(
            service.get("pids_limit", 0) > 0
            for service in (app, db)
        ),
        "PID limits configured",
    )

    check(
        bool(app.get("environment", {}).get("SESSION_SECRET"))
        and bool(app.get("environment", {}).get("DATABASE_URL")),
        "Application environment variables configured",
    )

    check(
        app.get("user", "10001:10001")
        not in ("0", "0:0", "root", "root:root"),
        "Compose does not override app user to root",
    )

    inspect = run(
        "docker", "image", "inspect",
        "university-room-fund:lab4",
        "--format", "{{json .Config}}",
    )

    if inspect.returncode == 0:
        image = json.loads(inspect.stdout)
        check(
            image.get("User") == "10001:10001",
            "Built image runs as non-root",
        )
        check(
            image.get("StopSignal") == "SIGTERM",
            "Built image uses SIGTERM",
        )
        image_env = image.get("Env", [])
        check(
            not any(
                item.startswith(
                    ("SESSION_SECRET=", "DB_PASSWORD=",
                     "DATABASE_URL=", "POSTGRES_PASSWORD=")
                )
                for item in image_env
            ),
            "No configured application secrets in image ENV",
        )
    else:
        check(False, "Built application image must exist")

    print()
    if errors:
        print(f"FAILED: {len(errors)} requirement(s) violated")
        return 1

    print("PASSED: container configuration satisfies checked policies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
