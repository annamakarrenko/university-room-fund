#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT="/opt/urf-cd"
readonly REGISTRY="ghcr.io/annamakarrenko/university-room-fund"
readonly ENV_FILE="${ROOT}/.env.staging"
readonly COMPOSE_FILE="${ROOT}/compose.staging.yaml"
readonly LAST_GOOD="${ROOT}/last_good.sha"
readonly LOCK_FILE="${ROOT}/deploy.lock"
readonly BASE_URL="http://127.0.0.1:18080"

usage() {
    echo "Usage: cd_deploy.sh {check|deploy|rollback} <40-character-commit-sha>"
    exit 2
}

[[ $# -eq 2 ]] || usage
[[ "$1" == "check" || "$1" == "deploy" || "$1" == "rollback" ]] || usage
[[ "$2" =~ ^[0-9a-f]{40}$ ]] || {
    echo "FAIL: invalid release SHA"
    exit 2
}

if [[ "$EUID" -ne 0 ]]; then
    echo "FAIL: root privileges required"
    exit 1
fi

ACTION="$1"
RELEASE_SHA="$2"
IMAGE_REF="${REGISTRY}:${RELEASE_SHA}"

umask 077
exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    echo "FAIL: another deployment is running"
    exit 1
fi

compose() {
    docker compose \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        "$@"
}

echo "=== LAB6 CD ==="
echo "Action: $ACTION"
echo "Release: $RELEASE_SHA"
echo "PASS: deployment lock acquired"

if [[ "$ACTION" == "rollback" ]]; then
    echo "=== ROLLBACK VALIDATION ==="

    PREVIOUS_GOOD="$(cat "${ROOT}/previous_good.sha")"

    if [[ "$PREVIOUS_GOOD" != "$RELEASE_SHA" ]]; then
        echo "FAIL: rollback target is not previous good release"
        exit 1
    fi

    if ! docker image inspect "$IMAGE_REF" >/dev/null 2>&1; then
        echo "FAIL: previous image is not available locally"
        exit 1
    fi

    echo "PASS: rollback target verified"
else
    echo "=== REGISTRY CHECK ==="

    if ! docker manifest inspect "$IMAGE_REF" >/dev/null 2>&1; then
        echo "FAIL: image unavailable in GHCR"
        exit 1
    fi

    echo "PASS: image exists in GHCR"
fi

if [[ "$ACTION" == "check" ]]; then
    echo "PASS: release preflight completed"
    exit 0
fi

echo "=== CURRENT RELEASE ==="

PREVIOUS_SHA="$(cat "$LAST_GOOD")"

[[ "$PREVIOUS_SHA" =~ ^[0-9a-f]{40}$ ]] || {
    echo "FAIL: invalid last_good.sha"
    exit 1
}

CURRENT_IMAGE="$(
    docker inspect urf-staging-app-1 \
        --format '{{.Config.Image}}'
)"

EXPECTED_CURRENT="${REGISTRY}:${PREVIOUS_SHA}"

if [[ "$CURRENT_IMAGE" != "$EXPECTED_CURRENT" ]]; then
    echo "FAIL: current container differs from last good release"
    exit 1
fi

CURRENT_HEALTH="$(
    docker inspect urf-staging-app-1 \
        --format '{{.State.Health.Status}}'
)"

if [[ "$CURRENT_HEALTH" != "healthy" ]]; then
    echo "FAIL: current staging is not healthy"
    exit 1
fi

echo "Previous good release: $PREVIOUS_SHA"

echo "=== PULL RELEASE IMAGE ==="

if [[ "$ACTION" == "deploy" ]]; then
    docker pull "$IMAGE_REF"
else
    echo "Using locally cached rollback image"
fi

echo "PASS: image downloaded"

echo "=== PREPARE FAILURE RECOVERY ==="

ENV_BACKUP="$(mktemp "${ROOT}/.env.staging.backup.XXXXXX")"
chmod 600 "$ENV_BACKUP"
cp -p "$ENV_FILE" "$ENV_BACKUP"

DEPLOY_ACCEPTED=0
DEPLOY_STARTED=0

recover_on_exit() {
    local exit_code=$?
    trap - EXIT

    if [[ "$DEPLOY_ACCEPTED" -eq 0 ]]; then
        echo "FAIL: release was not accepted"

        if [[ -f "$ENV_BACKUP" ]]; then
            cp -p "$ENV_BACKUP" "$ENV_FILE"
            echo "RECOVERY: previous configuration restored"
        fi

        if [[ "$DEPLOY_STARTED" -eq 1 ]]; then
            echo "=== AUTOMATIC RECOVERY ==="

            local compatible=0

            if [[ "$PREVIOUS_SHA" == "4fa1fef8d53bb5f24e27b7b8c8037aa18da46130" &&
                  "$RELEASE_SHA" == "43432826e7359d02471dc02115c5ef51d1716f0e" ]]; then
                compatible=1
            fi

            if [[ "$PREVIOUS_SHA" == "43432826e7359d02471dc02115c5ef51d1716f0e" &&
                  "$RELEASE_SHA" == "4fa1fef8d53bb5f24e27b7b8c8037aa18da46130" ]]; then
                compatible=1
            fi

            if [[ "$compatible" -eq 1 ]] &&
               docker image inspect "${REGISTRY}:${PREVIOUS_SHA}" >/dev/null 2>&1; then

                echo "RECOVERY: restoring compatible release $PREVIOUS_SHA"

                if compose up -d \
                    --no-build \
                    --pull never \
                    --no-deps \
                    --force-recreate \
                    --wait \
                    --wait-timeout 360 \
                    app &&
                   [[ "$(docker inspect urf-staging-app-1 --format '{{.Config.Image}}')" == "${REGISTRY}:${PREVIOUS_SHA}" ]] &&
                   [[ "$(docker inspect urf-staging-app-1 --format '{{.State.Health.Status}}')" == "healthy" ]] &&
                   python3 "${ROOT}/staging_smoke.py" \
                       --base-url "$BASE_URL" \
                       --expected-sha "$PREVIOUS_SHA"; then

                    echo "AUTO ROLLBACK SUCCESS: $PREVIOUS_SHA"
                else
                    echo "CRITICAL: automatic rollback failed"
                    echo "CRITICAL: manual intervention required"
                fi
            else
                echo "RECOVERY BLOCKED: database compatibility not verified"
                echo "NOTICE: manual recovery required"
            fi
        fi

        echo "NOTICE: database restoration was not performed"
    fi

    rm -f "$ENV_BACKUP"
    exit "$exit_code"
}

trap recover_on_exit EXIT

echo "=== UPDATE RELEASE CONFIG ==="

python3 - "$ENV_FILE" "$IMAGE_REF" "$RELEASE_SHA" <<'PY'
import os
import pathlib
import sys
import tempfile

path = pathlib.Path(sys.argv[1])
image_ref = sys.argv[2]
sha = sys.argv[3]

content = path.read_text()
lines = content.splitlines(keepends=True)

for key, value in (
    ("IMAGE_REF", image_ref),
    ("RELEASE_SHA", sha),
):
    matches = [
        i for i, line in enumerate(lines)
        if line.startswith(key + "=")
    ]
    if len(matches) != 1:
        raise SystemExit(f"FAIL: expected exactly one {key} entry")
    i = matches[0]
    lines[i] = f"{key}={value}\n"

fd, temp_name = tempfile.mkstemp(
    prefix=".env.staging.",
    dir=path.parent,
    text=True,
)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.writelines(lines)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_name, path)
except BaseException:
    pathlib.Path(temp_name).unlink(missing_ok=True)
    raise
PY

compose config --quiet

echo "=== START STAGING ==="

DEPLOY_STARTED=1

compose up -d \
    --no-build \
    --pull never \
    --wait \
    --wait-timeout 360

echo "=== VERIFY CONTAINER IMAGE ==="

ACTUAL_IMAGE="$(
    docker inspect urf-staging-app-1 \
        --format '{{.Config.Image}}'
)"

[[ "$ACTUAL_IMAGE" == "$IMAGE_REF" ]] || {
    echo "FAIL: running image does not match requested release"
    exit 1
}

echo "PASS: correct image running"

echo "=== VERIFY HEALTH ==="

[[ "$(
    docker inspect urf-staging-app-1 \
        --format '{{.State.Health.Status}}'
)" == "healthy" ]] || {
    echo "FAIL: staging is unhealthy"
    exit 1
}

echo "PASS: Docker healthcheck"

echo "=== SMOKE TEST ==="

python3 "${ROOT}/staging_smoke.py" \
    --base-url "$BASE_URL" \
    --expected-sha "$RELEASE_SHA"

echo "=== ACCEPT RELEASE ==="

CURRENT_TMP="$(mktemp "${ROOT}/last_good.XXXXXX")"
PREVIOUS_TMP="$(mktemp "${ROOT}/previous_good.XXXXXX")"

printf '%s\n' "$RELEASE_SHA" > "$CURRENT_TMP"
printf '%s\n' "$PREVIOUS_SHA" > "$PREVIOUS_TMP"

chmod 600 "$CURRENT_TMP" "$PREVIOUS_TMP"

mv -f "$PREVIOUS_TMP" "${ROOT}/previous_good.sha"
mv -f "$CURRENT_TMP" "$LAST_GOOD"

DEPLOY_ACCEPTED=1

echo "PASS: release accepted"
echo "PASS: release history updated"

if [[ "$ACTION" == "rollback" ]]; then
    echo "ROLLBACK SUCCESS: $RELEASE_SHA"
else
    echo "DEPLOY SUCCESS: $RELEASE_SHA"
fi
