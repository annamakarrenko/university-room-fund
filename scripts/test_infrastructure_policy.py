import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    (
        "Database port exposure",
        "roles/application/templates/compose.yaml.j2",
        '    image: "{{ postgres_image }}"',
        '    image: "{{ postgres_image }}"\n'
        '    ports:\n'
        '      - "5432:5432"',
        "no published database ports",
    ),
    (
        "Root application user",
        "roles/application/templates/compose.yaml.j2",
        '    user: "10001:10001"',
        '    user: "0:0"',
        "non-root application",
    ),
    (
        "Public application binding",
        "inventories/development/group_vars/all/vars.yml",
        'app_bind_address: "127.0.0.1"',
        'app_bind_address: "0.0.0.0"',
        "application binds to loopback",
    ),
    (
        "Insecure secret permissions",
        "roles/application/tasks/main.yml",
        "mode: '0600'",
        "mode: '0644'",
        "restricted secret file permissions",
    ),
    (
        "Unencrypted Vault",
        "inventories/development/group_vars/all/vault.yml",
        "$ANSIBLE_VAULT;1.1;AES256",
        "UNENCRYPTED",
        "encrypted Vault",
    ),
]


def main():
    for name, relative, old, new, expected in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            shutil.copytree(
                ROOT / "infrastructure",
                target / "infrastructure",
            )
            (target / "scripts").mkdir()
            script = target / "scripts/infrastructure_check.py"
            shutil.copy2(
                ROOT / "scripts/infrastructure_check.py",
                script,
            )

            path = target / "infrastructure" / relative
            content = path.read_text()

            if old not in content:
                raise SystemExit(f"FAIL: mutation missing: {name}")

            path.write_text(content.replace(old, new, 1))

            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                check=False,
            )

            if (
                result.returncode == 0
                or f"FAIL: " not in result.stderr
                or expected not in result.stderr
            ):
                raise SystemExit(f"FAIL: {name}")

            print(f"PASS: rejected {name}")

    print(f"All {len(CASES)} unsafe changes rejected")


if __name__ == "__main__":
    main()
