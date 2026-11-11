from fastapi import FastAPI

from app.main import app


def test_ci_smoke_application():
    assert isinstance(app, FastAPI)
