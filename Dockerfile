FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup \
    --no-create-home --shell /usr/sbin/nologin appuser

COPY requirements.lock .

RUN python -m pip install --no-cache-dir \
    --require-hashes -r requirements.lock

COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup alembic.ini .

USER 10001:10001

EXPOSE 8000

STOPSIGNAL SIGTERM

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
