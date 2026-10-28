PYTHON=.venv/Scripts/python.exe

setup:
	powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

run:
	$(PYTHON) -m uvicorn app.main:app --reload

lint:
	$(PYTHON) -m ruff check .

sast:
	$(PYTHON) -m bandit -r app

quality: lint sast

test:
	$(PYTHON) -m pytest -q

test-report:
	$(PYTHON) -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
	$(PYTHON) -m pytest --junitxml=reports/tests.xml

coverage:
	$(PYTHON) -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/tests.xml --cov-fail-under=40

migrate:
	$(PYTHON) -m alembic upgrade head

migration:
	$(PYTHON) -m alembic revision --autogenerate -m "$(name)"

backup:
	powershell -ExecutionPolicy Bypass -File scripts/backup.ps1

restore:
	powershell -ExecutionPolicy Bypass -File scripts/restore.ps1 -BackupFile "$(BACKUP)"

verify: quality coverage
# Lab 4: Docker container environment

.PHONY: up down container-build container-backup container-restore container-ps

up:
	docker compose up -d --build

down:
	docker compose down

container-build:
	docker compose build

container-ps:
	docker compose ps

container-backup:
	./scripts/container_backup.sh

container-restore:
	@test -n "$(BACKUP)" || (echo "Usage: make container-restore BACKUP=backups/file.dump" && exit 1)
	./scripts/container_restore.sh "$(BACKUP)"
