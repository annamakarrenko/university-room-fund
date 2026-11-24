from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1] / "infrastructure"


def check(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    print(f"PASS: {message}")


def load(path):
    return yaml.safe_load(path.read_text())


def main():
    common = load(ROOT / "group_vars/all.yml")
    templates = ROOT / "roles/application/templates"

    for name in ("development", "staging"):
        inventory = ROOT / "inventories" / name
        variables = load(inventory / "group_vars/all/vars.yml")
        variables = {**common, **variables}

        vault = inventory / "group_vars/all/vault.yml"
        check(
            vault.read_text().startswith("$ANSIBLE_VAULT;1.1;AES256\n"),
            f"{name}: encrypted Vault",
        )

        env = Environment(undefined=StrictUndefined)
        template = env.from_string(
            (templates / "compose.yaml.j2").read_text()
        )
        compose = yaml.safe_load(template.render(**variables))
        services = compose["services"]

        check(
            not services["db"].get("ports"),
            f"{name}: no published database ports",
        )
        check(
            services["app"]["ports"]
            == [f"127.0.0.1:{variables['app_host_port']}:8000"],
            f"{name}: application binds to loopback",
        )
        check(
            services["app"]["user"] == "10001:10001",
            f"{name}: non-root application",
        )
        check(
            compose["networks"]["backend"]["internal"] is True,
            f"{name}: internal database network",
        )

        for service in services.values():
            check(
                "@sha256:" in service["image"],
                f"{name}: pinned image",
            )

    tasks = load(ROOT / "roles/application/tasks/main.yml")
    secret_task = next(
        t for t in tasks if t["name"] == "Deploy application secrets"
    )

    check(
        secret_task["ansible.builtin.template"]["mode"] == "0600",
        "restricted secret file permissions",
    )
    check(
        secret_task.get("no_log") is True
        and secret_task.get("diff") is False,
        "secret output protection",
    )

    ssh = (ROOT / "roles/ssh/templates/00-urf-hardening.conf.j2").read_text()

    for setting in (
        "PermitRootLogin no",
        "PasswordAuthentication no",
        "PubkeyAuthentication yes",
        "KbdInteractiveAuthentication no",
    ):
        check(setting in ssh.splitlines(), f"SSH: {setting}")

    firewall = load(ROOT / "roles/firewall/tasks/main.yml")
    rules = [t["community.general.ufw"] for t in firewall]

    check(
        any(
            r.get("direction") == "incoming"
            and r.get("policy") == "deny"
            for r in rules
        ),
        "firewall denies incoming traffic",
    )
    check(
        any(r.get("state") == "enabled" for r in rules),
        "firewall enabled",
    )

    forbidden = {
        "shell",
        "raw",
        "ansible.builtin.shell",
        "ansible.builtin.raw",
    }

    for path in (ROOT / "roles").rglob("*.yml"):
        for task in load(path):
            check(
                not forbidden.intersection(task),
                f"no shell or raw: {task['name']}",
            )

    print("Infrastructure policy checks passed")


if __name__ == "__main__":
    main()
