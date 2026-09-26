# pyrefly: ignore [missing-import]
import pytest

from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """
    Fresh FastAPI application for every test.
    """

    app = create_app()

    return TestClient(app)
