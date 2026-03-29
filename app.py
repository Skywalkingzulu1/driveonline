import os
import datetime
import re
from functools import wraps

import jwt
from flask import Flask, request, jsonify, redirect, url_for, render_template_string
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
app = Flask(__name__)

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
def validate_email(email: str) -> bool:
    """Simple regex based email validation."""
    email_regex = r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
    return re.match(email_regex, email) is not None


def validate_password(password: str) -> bool:
    """Enforce a minimum password length."""
    return len(password) >= 8


def validate_full_name(name: str) -> bool:
    """Full name must be non‑empty and reasonably short."""
    return bool(name.strip()) and len(name.strip()) <= 100


# ---------------------------------------------------------------------------
# Registration endpoint
# ---------------------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    """
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "strongpassword",
        "full_name": "John Doe"
    }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    # Input validation
    if not email or not validate_email(email):
        return jsonify({"error": "Invalid or missing email address"}), 400
    if not password or not validate_password(password):
        return (
            jsonify(
                {"error": "Password must be at least 8 characters long"}
            ),
            400,
        )
    if not full_name or not validate_full_name(full_name):
        return jsonify({"error": "Invalid full name"}), 400

    if email in users_db:
        return jsonify({"error": "User already exists"}), 400

    # Secure password hashing
    hashed_pw = bcrypt.generate_password_hash(password)

    # Store user
    users_db[email] = {
        "hashed_password": hashed_pw,
        "full_name": full_name,
        "is_verified": False,
        "role": "user",
    }

    # (Optional) Send verification email here using `mail` and `serializer`

    return jsonify({"message": "User registered successfully"}), 201


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------
@app.route("/login", methods=["POST"])
def login():
    """
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "strongpassword"
    }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user_record = users_db.get(email)
    if not user_record:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user_record["hashed_password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    user = User(email)
    login_user(user)

    return jsonify({"message": "Logged in successfully"}), 200


# ---------------------------------------------------------------------------
# Example protected route
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return jsonify(
        {
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
        }
    )


# ---------------------------------------------------------------------------
# Logout endpoint
# ---------------------------------------------------------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200


# ---------------------------------------------------------------------------
# Run the application
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)