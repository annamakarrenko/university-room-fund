# Lab 8 — Incident report

## Incident

Date: 2026-11-24
Environment: staging
Service: University Room Fund
Release: 2a260c38ac7e4927dc855e7b1bf76042927429d6

A controlled PostgreSQL outage was simulated by stopping
the staging database container.

## Timeline (UTC)

- 15:15:33 — application and database operational.
- 15:15:37 — PostgreSQL stopped.
- 15:15:47 — readiness endpoint returned HTTP 503.
- DatabaseUnavailable alert entered FIRING state.
- PostgreSQL logs confirmed an administrative shutdown.
- Application logs confirmed readiness failure.
- Database container was restarted.
- 15:21:51 — readiness endpoint returned HTTP 200.
- Monitoring returned to normal state.

## Symptoms

- GET /health returned HTTP 200.
- GET /ready returned HTTP 503.
- urf_application_up was 1.
- urf_database_up was 0.
- urf_rooms_total was NaN.
- Grafana displayed database availability as DOWN.
- Prometheus raised a critical DatabaseUnavailable alert.

## Root cause

The PostgreSQL container was intentionally stopped during
a controlled incident exercise.

The application process remained operational, but database
connectivity and application readiness were lost.

## Recovery

The database container was restarted.

PostgreSQL readiness was verified using pg_isready.
Application health and readiness returned HTTP 200.
Database availability returned to 1.
The alert returned to INACTIVE.

No database restoration was required.

## Delivery process improvement

The existing staging smoke test was extended with an explicit
readiness check before the functional user scenario.

The check requires:

- HTTP 200 from /ready.
- status equal to ready.
- database equal to ok.

A failed readiness check terminates the smoke test with
a non-zero exit code.

This prevents the existing CD script from accepting a release
when the application is running but PostgreSQL is unavailable.

## Verification

A repeated controlled database outage confirmed:

- GET /health returned HTTP 200.
- GET /ready returned HTTP 503.
- The improved smoke test failed with exit code 1.
- Database availability was restored after restart.

Four automated regression tests were added to verify
readiness failure handling.

Final local verification:

- 54 automated tests passed.
- Application code coverage: 88.70%.
- Ruff: passed.
- Bandit: no issues identified.

## Remaining deployment step

The improved smoke test must be reviewed, merged into main
and installed on the staging CD host before it becomes
part of the active delivery process.
