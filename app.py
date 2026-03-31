import os
import datetime
import logging
from functools import wraps
from typing import Callable, Any, Dict

import jwt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import (
    Flask,
    jsonify,
    request,
    abort,
)
from flask_bcrypt import Bcrypt

# Optional AWS SDK for Parameter Store (kept for compatibility)
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    boto3 = None
    BotoCoreError = ClientError = Exception

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
import db  # SQLAlchemy integration for PostgreSQL / SQLite fallback (now a minimal stub)

# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=".",   # Serve static files (style.css, etc.) from project root
    template_folder=".",  # Serve HTML files from project root
)

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# ---------------------------------------------------------------------------
# Configuration loading (environment variables -> AWS Parameter Store)
# ---------------------------------------------------------------------------

def _get_ssm_client():
    """Create a boto3 SSM client if boto3 is available."""
    if boto3 is None:
        return None
    try:
        return boto3.client('ssm')
    except BotoCoreError:
        return None

_ssm_client = _get_ssm_client()


def _fetch_parameter(name: str) -> str | None:
    """Fetch a parameter from AWS Parameter Store."""
    if _ssm_client is None:
        return None
    try:
        response = _ssm_client.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except (BotoCoreError, ClientError):
        return None


def get_config(key: str, default: str | None = None) -> str | None:
    """Retrieve configuration value from env, then Parameter Store, then default."""
    value = os.getenv(key)
    if value:
        return value
    value = _fetch_parameter(key)
    if value:
        return value
    return default

# Application configuration
app.config["SECRET_KEY"] = get_config("SECRET_KEY", "super-secret-key")
app.config["JWT_SECRET_KEY"] = get_config("JWT_SECRET_KEY", "jwt-super-secret")
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_EXP_DELTA_SECONDS"] = 3600  # 1 hour
app.config["SECURITY_PASSWORD_SALT"] = get_config(
    "SECURITY_PASSWORD_SALT", "email-salt"
)

# In‑memory user store: email -> {password_hash: str, is_verified: bool}
users: Dict[str, Dict[str, Any]] = {}

# Serializer for email verification tokens
email_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_verification_token(email: str) -> str:
    """Create a time‑limited token for email verification."""
    return email_serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])


def confirm_verification_token(token: str, expiration: int = 3600) -> str:
    """Validate a verification token and return the embedded email.

    Raises:
        SignatureExpired: token is valid but expired.
        BadSignature: token is invalid.
    """
    return email_serializer.loads(
        token,
        salt=app.config["SECURITY_PASSWORD_SALT"],
        max_age=expiration,
    )


def token_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(
                token,
                app.config["JWT_SECRET_KEY"],
                algorithms=[app.config["JWT_ALGORITHM"]],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        # Attach user info to request context if needed
        request.user = payload.get('sub')
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON payload"}), 400
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    if email in users:
        return jsonify({"message": "User already exists"}), 400
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    users[email] = {"password_hash": pw_hash, "is_verified": False}
    token = generate_verification_token(email)
    # In a real app we would email this token. Here we just return it.
    return jsonify({"message": "User registered. Verify email.", "verification_token": token}), 201

@app.route('/verify/<token>', methods=['GET'])
def verify_email(token: str):
    try:
        email = confirm_verification_token(token)
    except SignatureExpired:
        return jsonify({"message": "Verification link expired"}), 400
    except BadSignature:
        return jsonify({"message": "Invalid verification token"}), 400
    user = users.get(email)
    if not user:
        return jsonify({"message": "User not found"}), 404
    if user["is_verified"]:
        return jsonify({"message": "User already verified"}), 200
    user["is_verified"] = True
    return jsonify({"message": "Email verified successfully"}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid JSON payload"}), 400
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    user = users.get(email)
    if not user:
        return jsonify({"message": "Invalid credentials"}), 401
    if not user["is_verified"]:
        return jsonify({"message": "Email not verified"}), 403
    if not bcrypt.check_password_hash(user["password_hash"], password):
        return jsonify({"message": "Invalid credentials"}), 401
    payload = {
        "sub": email,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"]),
    }
    token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm=app.config["JWT_ALGORITHM"])
    return jsonify({"access_token": token}), 200

# Example protected route
@app.route('/protected', methods=['GET'])
@token_required
def protected():
    return jsonify({"message": f"Hello, {request.user}! This is a protected endpoint."}), 200

# ---------------------------------------------------------------------------
# Root endpoint – serve the static index.html for convenience
# ---------------------------------------------------------------------------

@app.route('/')
def root():
    return app.send_static_file('index.html')

# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Enable simple logging for debugging
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)), debug=True)
