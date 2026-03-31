import pytest
from app import app as flask_app

@pytest.fixture
def client():
    """Create a Flask test client for use in tests."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "JWT_SECRET_KEY": "test-jwt-secret",
    })
    with flask_app.test_client() as client:
        yield client
