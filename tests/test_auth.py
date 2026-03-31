import json
import pytest

# Helper data
VALID_EMAIL = "testuser@example.com"
VALID_PASSWORD = "StrongPass123!"
INVALID_PASSWORD = "wrongpass"

def test_health_endpoint(client):
    """Health endpoint should return status 200 and a JSON payload indicating service health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    # The exact shape may vary; we accept either a simple string or a dict with a 'status' key.
    if isinstance(data, dict):
        assert data.get("status") in ("ok", "healthy", "up")
    else:
        assert data in ("ok", "healthy", "up")

def test_user_registration_success(client):
    """Register a new user with valid credentials should succeed and return 201."""
    payload = {"email": VALID_EMAIL, "password": VALID_PASSWORD}
    response = client.post(
        "/register",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    # Expect a message confirming registration
    assert "message" in data
    assert VALID_EMAIL in data.get("message", "")

def test_user_login_success(client):
    """After registration, logging in with correct credentials should return a JWT token."""
    # Ensure the user exists (register first)
    client.post(
        "/register",
        data=json.dumps({"email": VALID_EMAIL, "password": VALID_PASSWORD}),
        content_type="application/json",
    )
    # Attempt login
    login_payload = {"email": VALID_EMAIL, "password": VALID_PASSWORD}
    response = client.post(
        "/login",
        data=json.dumps(login_payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    # The response should contain a token field (JWT)
    assert "token" in data
    token = data["token"]
    assert isinstance(token, str)
    assert len(token) > 0

def test_user_login_failure_invalid_password(client):
    """Logging in with an incorrect password should return a 401 Unauthorized response."""
    # Register the user first
    client.post(
        "/register",
        data=json.dumps({"email": VALID_EMAIL, "password": VALID_PASSWORD}),
        content_type="application/json",
    )
    # Attempt login with wrong password
    login_payload = {"email": VALID_EMAIL, "password": INVALID_PASSWORD}
    response = client.post(
        "/login",
        data=json.dumps(login_payload),
        content_type="application/json",
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    # Expect an error message indicating authentication failure
    assert "error" in data or "message" in data
