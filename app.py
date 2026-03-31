import os
import jwt
import datetime
import logging
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Flask, jsonify, request, abort, g
from flask_bcrypt import Bcrypt

# Optional AWS SDK for Parameter Store and CloudWatch
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    boto3 = None
    BotoCoreError = ClientError = Exception

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
    """Create a boto3 SSM client if boto3 is available.
    The client will automatically use the IAM role attached to the instance/container.
    """
    if boto3 is None:
        return None
    try:
        return boto3.client('ssm')
    except BotoCoreError:
        return None

_ssm_client = _get_ssm_client()


def _fetch_parameter(name: str) -> str | None:
    """Fetch a parameter from AWS Parameter Store.
    Returns the parameter value as a string, or None if it cannot be retrieved.
    """
    if _ssm_client is None:
        return None
    try:
        response = _ssm_client.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except (BotoCoreError, ClientError):
        return None


def get_config(key: str, default: str | None = None) -> str | None:
    """Retrieve configuration value.
    Order of precedence:
    1. Environment variable
    2. AWS Parameter Store (parameter name matches the key)
    3. Provided default
    """
    # 1. Environment variable
    value = os.getenv(key)
    if value:
        return value
    # 2. Parameter Store
    value = _fetch_parameter(key)
    if value:
        return value
    # 3. Default
    return default

# Application configuration
app.config["SECRET_KEY"] = get_config("SECRET_KEY", "super-secret-key")
app.config["JWT_SECRET_KEY"] = get_config("JWT_SECRET_KEY", "jwt-super-secret")
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_EXP_DELTA_SECONDS"] = 3600  # 1 hour
app.config["SECURITY_PASSWORD_SALT"] = get_config("SECURITY_PASSWORD_SALT", "email-salt")

# Determine deployment environment (blue/green). Default to 'blue' if not set.
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV", "blue").lower()

# In‑memory user store: email -> {password_hash, is_verified}
users = {}

# Serializer for email verification tokens
email_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_jwt(email: str) -> str:
    """Generate a JWT token for the given email."""
    payload = {
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"])
    }
    token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm=app.config["JWT_ALGORITHM"])
    return token

def token_required(f):
    """Decorator to protect routes with JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # JWT can be passed in the Authorization header as Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        try:
            data = jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=[app.config["JWT_ALGORITHM"]])
            g.current_user = data["email"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok", "environment": DEPLOYMENT_ENV}), 200

@app.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Expected JSON payload: {"email": "...", "password": "..."}
    """
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"message": "Email and password required"}), 400

    email = data["email"].strip().lower()
    if email in users:
        return jsonify({"message": "User already exists"}), 400

    password_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    users[email] = {"password_hash": password_hash, "is_verified": False}

    # Generate verification token
    token = email_serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])
    verification_url = f"{request.host_url}verify/{token}"
    # In a real app you would send this URL via email.
    # For this simplified version we just return it.
    return jsonify({"message": "User registered. Verify email.", "verification_url": verification_url}), 201

@app.route("/verify/<token>", methods=["GET"])
def verify_email(token):
    """Verify a user's email using the token."""
    try:
        email = email_serializer.loads(
            token,
            salt=app.config["SECURITY_PASSWORD_SALT"],
            max_age=3600  # 1 hour validity
        )
    except SignatureExpired:
        return jsonify({"message": "Verification link expired"}), 400
    except BadSignature:
        return jsonify({"message": "Invalid verification token"}), 400

    user = users.get(email)
    if not user:
        return jsonify({"message": "User not found"}), 404

    user["is_verified"] = True
    return jsonify({"message": "Email verified successfully"}), 200

@app.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT.
    Expected JSON payload: {"email": "...", "password": "..."}
    """
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"message": "Email and password required"}), 400

    email = data["email"].strip().lower()
    user = users.get(email)
    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user["password_hash"], data["password"]):
        return jsonify({"message": "Invalid credentials"}), 401

    if not user.get("is_verified"):
        return jsonify({"message": "Email not verified"}), 403

    token = generate_jwt(email)
    return jsonify({"token": token}), 200

@app.route("/protected", methods=["GET"])
@token_required
def protected():
    """Example protected endpoint."""
    return jsonify({"message": f"Hello, {g.current_user}! This is a protected route."}), 200

# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Enable debug mode if FLASK_ENV is set to development
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=5000, debug=debug)