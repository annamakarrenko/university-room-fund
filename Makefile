PYTHON=.venv/Scripts/python.exe

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

run:
	$(PYTHON) -m uvicorn app.main:app --reload

lint:
	$(PYTHON) -m ruff check .

sast:
	$(PYTHON) -m bandit -r app

test:
	$(PYTHON) -m pytest -q

test-report:
	$(PYTHON) -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
	$(PYTHON) -m pytest --junitxml=reports/tests.xml

coverage:
	$(PYTHON) -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/tests.xml --cov-fail-under=40

verify: lint sast coverage