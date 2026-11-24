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
    ansible app_servers -m ansible.builtin.ping
    ansible-playbook site.yml --syntax-check

## Development deployment

    ansible-playbook site.yml -K

Repeated execution must not introduce unnecessary changes.

Staging deployment is disabled by default to protect
the existing environment.
