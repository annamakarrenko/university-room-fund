# Infrastructure management

University Room Fund infrastructure is managed using Ansible.

## Requirements

- Ubuntu 24.04 LTS
- Ansible Core 2.16.3
- SSH access to managed nodes
- Python 3 on managed nodes
- sudo privileges

## Environments

| Environment | Host | Address | Application port |
|---|---|---|---|
| Development | urf-lab7 | 192.168.56.105 | 18081 |
| Staging | urf-app | 192.168.56.10 | 18080 |

## Configuration

- group_vars/all.yml: common parameters
- inventories/*/group_vars/: environment parameters
- inventories/*/host_vars/: node-specific parameters
- roles/: reusable infrastructure roles
- site.yml: main infrastructure playbook

SSH private keys and plaintext secrets must not be committed.

## Verification

Run commands from the infrastructure directory.

    ansible-inventory --graph
    ansible app_servers -m ansible.builtin.ping --ask-vault-pass
    ansible-playbook site.yml --syntax-check --ask-vault-pass

## Development deployment

    ansible-playbook site.yml -K --ask-vault-pass

Repeated execution must not introduce unnecessary changes.

Staging deployment is disabled by default to protect
the existing environment.

## Infrastructure roles

- common: hostname and base packages
- users: restricted application user and group
- ssh: key-based authentication and SSH hardening
- docker: Docker Engine and Compose installation
- firewall: restricted incoming traffic
- application: directories, configuration, secrets and containers

## Ansible dependencies

    ansible-galaxy collection install -r requirements.yml

## Secrets

Environment secrets are encrypted using Ansible Vault.
Vault files are stored in inventories/*/group_vars/all/vault.yml.
The Vault password and SSH private keys are stored outside Git.
The generated application .env file has permissions 0600.

## Bootstrap prerequisites

Install Ubuntu Server with Python 3 and OpenSSH.
Create the deployadmin user with sudo access.
Configure trusted SSH keys before running the playbook.

## Deployment properties

- Application and database images are pinned by digest.
- The application container runs with UID 10001.
- PostgreSQL has no published host port.
- The application binds to the loopback interface.
- Successful migrations are not rerun without a reason.
- Repeated deployment must produce changed=0.

## Development health check

Run on urf-lab7:

    curl -fsS http://127.0.0.1:18081/health

## Infrastructure acceptance requirements

- Application ports must bind to the loopback interface.
- Database ports must not be published.
- Application containers must run without root privileges.
- Container images must be pinned by digest.
- Secrets must be encrypted in Git and protected on hosts.
- SSH must use key-based authentication.
- Incoming traffic must be denied by default.
- Infrastructure roles must avoid shell and raw tasks.
- Repeated execution must produce no unnecessary changes.
- Application health must be verified after deployment.
- Critical infrastructure changes require code owner approval.

## Local policy checks

Run from the repository root:

    make infrastructure-check
    make infrastructure-policy-test

## Infrastructure CI

The infrastructure-check.yml workflow validates inventories,
playbook syntax, security policies and negative policy tests.

CI validation does not require real Vault passwords or access
to managed servers.

## Configuration drift recovery

Change the permissions of the empty development backups
directory from 0700 to 0755.

Run the Ansible playbook again and verify that permissions
return to 0700 and the application remains healthy.

A subsequent execution must report changed=0 and failed=0.
