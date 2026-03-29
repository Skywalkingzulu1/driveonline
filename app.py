import os
import datetime
import re
from functools import wraps

import jwt
from flask import Flask, request, jsonify, redirect, url_for, render_template_string, send_from_directory
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=".",  # Serve static files (style.css, etc.) from project root
    template_folder=".",  # Serve HTML files from project root
)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-super-secret")
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_EXP_DELTA_SECONDS"] = 3600  # 1 hour

# Flask‑Mail configuration (using console backend for demonstration)
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "localhost")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 1025))
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
    "MAIL_DEFAULT_SENDER", "no-reply@example.com"
)

mail = Mail(app)
bcrypt = Bcrypt(app)
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ---------------------------------------------------------------------------
# In‑memory user store
# ---------------------------------------------------------------------------
# Structure:
# {
#   email: {
#       "hashed_password": bytes,
#       "full_name": str,
#       "is_verified": bool,
#       "role": str
#   }
# }
users_db = {}

# ---------------------------------------------------------------------------
# Flask‑Login user model
# ---------------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, email):
        self.id = email
        self.email = email
        record = users_db.get(email, {})
        self.full_name = record.get("full_name", "")
        self.is_verified = record.get("is_verified", False)
        self.role = record.get("role", "user")

    @staticmethod
    def get(email):
        if email in users_db:
            return User(email)
        return None

# ---------------------------------------------------------------------------
# Login manager configuration
# ---------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def generate_jwt(email: str) -> str:
    """Create a JWT for the given email."""
    payload = {
        "sub": email,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"]),
    }
    token = jwt.encode(
        payload,
        app.config["JWT_SECRET_KEY"],
        algorithm=app.config["JWT_ALGORITHM"],
    )
    # PyJWT returns bytes in older versions; ensure string
    return token if isinstance(token, str) else token.decode("utf-8")


def verify_jwt(token: str) -> dict | None:
    """Validate a JWT and return its payload, or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            app.config["JWT_SECRET_KEY"],
            algorithms=[app.config["JWT_ALGORITHM"]],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to protect routes with JWT authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"msg": "Missing or invalid Authorization header"}), 401
        token = auth_header.split()[1]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({"msg": "Invalid or expired token"}), 401
        # Attach user email to request context
        request.user_email = payload["sub"]
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Serve the main dashboard page."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
        return render_template_string(html)
    except FileNotFoundError:
        return "<h1>Index page not found</h1>", 404


@app.route("/static/<path:filename>")
def static_files(filename):
    """Serve static assets like CSS."""
    return send_from_directory(".", filename)


# ----- Registration ---------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    """
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text",
        "full_name": "John Doe"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON payload"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    if not email or not password or not full_name:
        return jsonify({"msg": "Email, password and full_name are required"}), 400

    if email in users_db:
        return jsonify({"msg": "User already exists"}), 409

    hashed = bcrypt.generate_password_hash(password)
    users_db[email] = {
        "hashed_password": hashed,
        "full_name": full_name,
        "is_verified": False,
        "role": "user",
    }

    # In a real app, send verification email here.
    return jsonify({"msg": "User registered successfully"}), 201


# ----- Login ---------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    """
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON payload"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user_record = users_db.get(email)
    if not user_record:
        return jsonify({"msg": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user_record["hashed_password"], password):
        return jsonify({"msg": "Invalid credentials"}), 401

    user = User(email)
    login_user(user)

    token = generate_jwt(email)
    return jsonify({"access_token": token, "msg": "Login successful"}), 200


# ----- Logout ---------------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"msg": "Logged out"}), 200


# ----- Protected example ----------------------------------------------------
@app.route("/api/profile", methods=["GET"])
@token_required
def profile():
    email = request.user_email
    user = users_db.get(email)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    return jsonify(
        {
            "email": email,
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "is_verified": user.get("is_verified"),
        }
    ), 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"msg": "Resource not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"msg": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Run the application
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Enable debug mode only in development
    app.run(host="0.0.0.0", port=5000, debug=True)