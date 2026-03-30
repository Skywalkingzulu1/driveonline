import os
import datetime
import re
from functools import wraps
from typing import Callable, Any, Dict

import jwt
from flask import (
    Flask,
    request,
    jsonify,
    redirect,
    url_for,
    render_template_string,
    send_from_directory,
    g,
)
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
users_db: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Flask‑Login user model (kept for possible UI integration)
# ---------------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, email: str):
        self.id = email
        self.email = email
        record = users_db.get(email, {})
        self.full_name = record.get("full_name", "")
        self.is_verified = record.get("is_verified", False)
        self.role = record.get("role", "user")

    @staticmethod
    def get(email: str):
        if email in users_db:
            return User(email)
        return None

# ---------------------------------------------------------------------------
# Login manager configuration
# ---------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------------------------------------------------------------------
# Helper functions for JWT handling
# ---------------------------------------------------------------------------
def generate_jwt(email: str, role: str) -> str:
    """Create a JWT token for a given user."""
    payload = {
        "sub": email,
        "role": role,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"]),
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(
        payload,
        app.config["JWT_SECRET_KEY"],
        algorithm=app.config["JWT_ALGORITHM"],
    )
    # PyJWT >=2 returns a string, older versions return bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_jwt(token: str) -> Dict[str, Any]:
    """Decode a JWT token and return its payload."""
    return jwt.decode(
        token,
        app.config["JWT_SECRET_KEY"],
        algorithms=[app.config["JWT_ALGORITHM"]],
    )


def jwt_required(fn: Callable) -> Callable:
    """Decorator that ensures a valid JWT is present in the Authorization header."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"msg": "Missing or malformed Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_jwt(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"msg": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"msg": "Invalid token"}), 401

        # Attach user info to Flask's global context for downstream use
        g.current_user_email = payload["sub"]
        g.current_user_role = payload.get("role", "user")
        return fn(*args, **kwargs)

    return wrapper


def role_required(required_role: str):
    """Decorator that checks the JWT payload for a specific role."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not hasattr(g, "current_user_role"):
                return jsonify({"msg": "User role not found"}), 403
            if g.current_user_role != required_role:
                return (
                    jsonify(
                        {
                            "msg": f"Insufficient permissions: requires {required_role}"
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Authentication Endpoints (JWT based)
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    """
    Register a new user.
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text-password",
        "full_name": "John Doe",
        "role": "admin"   # optional, defaults to "user"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON payload"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password")
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "user").strip().lower()

    # Basic validation
    if not email or not password or not full_name:
        return jsonify({"msg": "email, password and full_name are required"}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"msg": "Invalid email format"}), 400
    if email in users_db:
        return jsonify({"msg": "User already exists"}), 409

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    users_db[email] = {
        "hashed_password": hashed_pw,
        "full_name": full_name,
        "is_verified": True,  # Skipping email verification for this demo
        "role": role,
    }

    return jsonify({"msg": "User registered successfully"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT.
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text-password"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON payload"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"msg": "email and password are required"}), 400

    user_record = users_db.get(email)
    if not user_record:
        return jsonify({"msg": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user_record["hashed_password"], password):
        return jsonify({"msg": "Invalid credentials"}), 401

    token = generate_jwt(email, user_record.get("role", "user"))
    return jsonify({"access_token": token}), 200


# ---------------------------------------------------------------------------
# Example protected route demonstrating role‑based access
# ---------------------------------------------------------------------------
@app.route("/api/admin/dashboard", methods=["GET"])
@jwt_required
@role_required("admin")
def admin_dashboard():
    """Only accessible to users with the 'admin' role."""
    return jsonify(
        {
            "msg": f"Welcome to the admin dashboard, {g.current_user_email}!",
            "role": g.current_user_role,
        }
    ), 200


@app.route("/api/user/profile", methods=["GET"])
@jwt_required
def user_profile():
    """Accessible to any authenticated user."""
    user = users_db.get(g.current_user_email, {})
    return jsonify(
        {
            "email": g.current_user_email,
            "full_name": user.get("full_name", ""),
            "role": user.get("role", "user"),
        }
    ), 200


# ---------------------------------------------------------------------------
# Existing Flask‑Login routes (kept for compatibility – optional)
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login_page():
    # Placeholder for a traditional login page if needed.
    return jsonify({"msg": "Login page placeholder"}), 200


@app.route("/logout")
@login_required
def logout_page():
    logout_user()
    return jsonify({"msg": "Logged out"}), 200


# ---------------------------------------------------------------------------
# Static file serving (unchanged)
# ---------------------------------------------------------------------------
@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)


if __name__ == "__main__":
    # Run the Flask development server
    app.run(host="0.0.0.0", port=5000, debug=True)