import os
import datetime
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
def send_confirmation_email(to_email):
    """Generate a token and send a confirmation email."""
    token = serializer.dumps(to_email, salt="email-confirm")
    confirm_url = url_for("confirm_email", token=token, _external=True)
    html_body = render_template_string(
        """
        <p>Hello,</p>
        <p>Thank you for registering. Please click the link below to verify your email address:</p>
        <p><a href="{{ confirm_url }}">{{ confirm_url }}</a></p>
        <p>If you did not sign up, you can ignore this email.</p>
        """,
        confirm_url=confirm_url,
    )
    msg = Message(
        subject="Please confirm your email",
        recipients=[to_email],
        html=html_body,
    )
    mail.send(msg)


def token_required(f):
    """Decorator to protect routes that require a verified email."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not getattr(current_user, "is_verified", False):
            return jsonify({"error": "Email not verified"}), 403
        return f(*args, **kwargs)

    return decorated_function


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    """
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text-password",
        "full_name": "John Doe"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if email in users_db:
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    users_db[email] = {
        "hashed_password": hashed_pw,
        "full_name": full_name,
        "is_verified": False,
        "role": "user",
    }

    # Send verification email
    try:
        send_confirmation_email(email)
    except Exception as e:
        # In a real app you would log this
        return jsonify({"error": f"Failed to send verification email: {str(e)}"}), 500

    return jsonify({"message": "User registered. Please check your email to verify your account."}), 201


@app.route("/confirm/<token>")
def confirm_email(token):
    try:
        email = serializer.loads(token, salt="email-confirm", max_age=3600)
    except SignatureExpired:
        return jsonify({"error": "The confirmation link has expired."}), 400
    except BadSignature:
        return jsonify({"error": "Invalid confirmation token."}), 400

    user_record = users_db.get(email)
    if not user_record:
        return jsonify({"error": "User not found."}), 404

    if user_record.get("is_verified"):
        return jsonify({"message": "Account already verified."}), 200

    user_record["is_verified"] = True
    return jsonify({"message": "Email verified successfully. You can now log in."}), 200


@app.route("/login", methods=["POST"])
def login():
    """
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text-password"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    email = data.get("email")
    password = data.get("password")

    user_record = users_db.get(email)
    if not user_record:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user_record["hashed_password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user_record.get("is_verified", False):
        return jsonify({"error": "Email not verified"}), 403

    user = User(email)
    login_user(user)
    return jsonify({"message": "Logged in successfully"}), 200


@app.route("/protected")
@token_required
def protected_route():
    return jsonify({"message": f"Hello, {current_user.full_name}. This is a protected route."})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})


if __name__ == "__main__":
    app.run(debug=True)