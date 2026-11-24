# University Room Fund observability

## Components

- Prometheus: application and infrastructure metrics.
- Grafana: provisioned dashboard with 12 panels.
- Node Exporter: host CPU, memory and filesystem metrics.
- cAdvisor: Docker container CPU and memory metrics.

## Deployment prerequisites

The lab8-test application must be running and connected
to the urf-lab8-test_frontend Docker network.

All monitoring images are pinned by SHA256 digest.

Create a password file outside the repository:

    mkdir -p ~/.config/urf-monitoring
    chmod 700 ~/.config/urf-monitoring
    (
      umask 077
      printf 'GRAFANA_ADMIN_PASSWORD=%s\n' \
        "$(openssl rand -hex 24)" \
        > ~/.config/urf-monitoring/.env
    )

Do not overwrite the password file for an existing installation.

## Start monitoring

Run from the repository root:

    sudo docker compose \
      --env-file "$HOME/.config/urf-monitoring/.env" \
      -f monitoring/compose.yaml up -d

## Access

Prometheus and Grafana bind to the host loopback interface.
Remote access is provided through SSH port forwarding.

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

Node Exporter and cAdvisor do not publish host ports.

## Dashboard

The dashboard is automatically provisioned from JSON.

It displays application and database availability, HTTP traffic,
errors, p95 response time, host resources, container resources,
and the total number of university rooms.

## Alert rules

- ApplicationDown
- DatabaseUnavailable
- HighServerErrorRate
- HostDiskSpaceLow
- HostMemoryLow

Alert states are available in Prometheus.

## Validation

    make monitoring-check

GitHub Actions also validates Docker Compose configuration,
Prometheus configuration and alert rules.

## Security

Grafana credentials are stored outside Git with mode 0600.
Anonymous access and public registration are disabled.

Docker and containerd sockets provide sensitive access to
the host container runtime, even with read-only mounts.
The cAdvisor configuration is intended for a trusted
laboratory environment.

Monitoring containers have CPU, memory and PID limits.
Prometheus retention is limited to seven days and 1 GB.

## Failure demonstration

The test application was intentionally stopped.
Prometheus detected the unavailable target and activated
the ApplicationDown alert.

Grafana displayed DOWN for application availability.
The application was restarted and both health endpoints
returned HTTP 200.

All alert rules returned to the inactive state.
