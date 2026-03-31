import os
import time
import pytest
from app import app, bcrypt, email_serializer, get_config

# Ensure the Flask app is in testing mode
app.config['TESTING'] = True
client = app.test_client()

def test_get_config_uses_environment_variable(monkeypatch):
    monkeypatch.setenv('CUSTOM_KEY', 'env_value')
    # get_config should return the env value when set
    assert get_config('CUSTOM_KEY', 'default') == 'env_value'

def test_get_config_falls_back_to_default_when_missing(monkeypatch):
    # Ensure the variable is not set
    monkeypatch.delenv('MISSING_KEY', raising=False)
    assert get_config('MISSING_KEY', 'default_fallback') == 'default_fallback'

def test_password_hash_and_check():
    password = 'StrongP@ssw0rd!'
    # Generate hash using the bcrypt instance from the app
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    # Verify that the hash matches the original password
    assert bcrypt.check_password_hash(pw_hash, password) is True
    # Wrong password should fail
    assert bcrypt.check_password_hash(pw_hash, 'wrong') is False

def test_email_token_generation_and_validation():
    email = 'user@example.com'
    # Create a token that expires in 5 seconds for the test
    token = email_serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])
    # Immediately load the token and verify the email matches
    loaded_email = email_serializer.loads(
        token,
        salt=app.config['SECURITY_PASSWORD_SALT'],
        max_age=5
    )
    assert loaded_email == email

    # Simulate expiration by sleeping longer than max_age
    time.sleep(6)
    with pytest.raises(Exception) as exc_info:
        email_serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=5
        )
    # The exception should be either SignatureExpired or BadSignature
    assert any(cls.__name__ in str(exc_info.value) for cls in (SignatureExpired, BadSignature))
