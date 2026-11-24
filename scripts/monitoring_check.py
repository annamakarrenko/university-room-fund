import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "monitoring"


def check(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


def main():
    compose = yaml.safe_load(
        (ROOT / "compose.yaml").read_text()
    )
    services = compose["services"]

    check(
        set(services) == {
            "prometheus", "grafana",
            "node-exporter", "cadvisor",
        },
        "All four monitoring services configured",
    )

    for name, service in services.items():
        check(
            re.search(
                r"@sha256:[a-f0-9]{64}$",
                service["image"],
            ) is not None,
            f"{name}: pinned image digest",
        )

        check(
            all(
                port.startswith("127.0.0.1:")
                for port in service.get("ports", [])
            ),
            f"{name}: no public ports",
        )

        check(
            not service.get("privileged", False),
            f"{name}: privileged mode disabled",
        )

        check(
            all(
                key in service
                for key in ("mem_limit", "cpus", "pids_limit")
            ),
            f"{name}: resource limits configured",
        )

    for name in ("node-exporter", "cadvisor"):
        check(
            not services[name].get("ports"),
            f"{name}: no published ports",
        )

    check(
        compose["networks"]["monitoring"]["internal"],
        "Internal monitoring network",
    )

    grafana = services["grafana"]["environment"]

    check(
        grafana["GF_AUTH_ANONYMOUS_ENABLED"] == "false",
        "Grafana anonymous access disabled",
    )

    check(
        grafana["GF_USERS_ALLOW_SIGN_UP"] == "false",
        "Grafana public registration disabled",
    )

    check(
        grafana["GF_SECURITY_ADMIN_PASSWORD"]
        == "${GRAFANA_ADMIN_PASSWORD:?required}",
        "Grafana password supplied externally",
    )

    prometheus = yaml.safe_load(
        (ROOT / "prometheus/prometheus.yml").read_text()
    )

    jobs = {
        item["job_name"]
        for item in prometheus["scrape_configs"]
    }

    check(
        jobs == {
            "prometheus", "urf-app", "urf-staging",
            "node-exporter", "cadvisor",
        },
        "All five scrape jobs configured",
    )

    rules = yaml.safe_load(
        (ROOT / "prometheus/rules/alerts.yml").read_text()
    )

    alerts = {
        rule["alert"]
        for group in rules["groups"]
        for rule in group["rules"]
    }

    check(
        {
            "ApplicationDown",
            "DatabaseUnavailable",
            "HighServerErrorRate",
            "HostDiskSpaceLow",
            "HostMemoryLow",
        }.issubset(alerts),
        "All five alert rules configured",
    )

    datasource = yaml.safe_load(
        (
            ROOT
            / "grafana/provisioning/datasources/prometheus.yml"
        ).read_text()
    )["datasources"][0]

    check(
        datasource["uid"] == "urf-prometheus"
        and datasource["url"] == "http://prometheus:9090",
        "Grafana datasource configured",
    )

    dashboard = json.loads(
        (
            ROOT / "grafana/dashboards/urf-overview.json"
        ).read_text()
    )

    variables = {
        item["name"]: item
        for item in dashboard["templating"]["list"]
    }

    check(
        variables["environment"]["query"] == "lab8-test,staging",
        "Dashboard supports both environments",
    )

    check(
        compose["networks"]["staging"]["external"]
        and compose["networks"]["staging"]["name"]
        == "urf-staging_frontend"
        and "staging" in services["prometheus"]["networks"],
        "Prometheus connected to staging network",
    )

    panels = dashboard["panels"]

    check(
        len(panels) == 12,
        "Dashboard contains 12 panels",
    )

    check(
        len({panel["id"] for panel in panels}) == 12,
        "Dashboard panel IDs are unique",
    )

    check(
        all(
            panel["datasource"]["uid"] == "urf-prometheus"
            for panel in panels
        ),
        "All panels use provisioned datasource",
    )

    check(
        all(
            target.get("expr")
            for panel in panels
            for target in panel["targets"]
        ),
        "All panels contain PromQL queries",
    )

    check(
        not list(ROOT.rglob(".env")),
        "No .env files in monitoring directory",
    )

    print("Monitoring policy checks passed")


if __name__ == "__main__":
    main()
