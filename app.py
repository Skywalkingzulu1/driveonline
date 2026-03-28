import os
import datetime
from functools import wraps

import jwt
from flask import Flask, request, jsonify, redirect, url_for
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
def hash_password(plain_password: str) -> bytes:
    """Hash a plain password using Flask‑Bcrypt."""
    return bcrypt.generate_password_hash(plain_password)


def check_password(hashed: bytes, plain_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.check_password_hash(hashed, plain_password)


def generate_jwt(user: User) -> str:
    """Create a JWT token containing user email and role."""
    payload = {
        "sub": user.email,
        "role": user.role,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"]),
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm=app.config["JWT_ALGORITHM"])
    # PyJWT returns str in >=2.0, bytes in older versions – ensure str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_jwt(token: str):
    """Decode and verify a JWT token."""
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


def role_required(required_role):
    """Decorator to enforce role‑based access on a view."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Prefer JWT token if supplied
            auth_header = request.headers.get("Authorization", "")
            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

            if token:
                payload = decode_jwt(token)
                if not payload:
                    return jsonify({"msg": "Invalid or expired token"}), 401
                if payload.get("role") != required_role:
                    return jsonify({"msg": "Insufficient permissions"}), 403
                # Attach user info to request context if needed
                request.user_email = payload.get("sub")
                request.user_role = payload.get("role")
                return f(*args, **kwargs)

            # Fallback to Flask‑Login session
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if getattr(current_user, "role", None) != required_role:
                return jsonify({"msg": "Insufficient permissions"}), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    """
    Expected JSON:
    {
        "email": "...",
        "password": "...",
        "full_name": "...",
        "role": "admin" (optional, defaults to "user")
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON body"}), 400

    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name", "")
    role = data.get("role", "user")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    if email in users_db:
        return jsonify({"msg": "User already exists"}), 400

    hashed = hash_password(password)
    users_db[email] = {
        "hashed_password": hashed,
        "full_name": full_name,
        "is_verified": True,  # In a real app, you'd send a verification email
        "role": role,
    }

    # Auto‑login after registration
    user = User(email)
    login_user(user)

    token = generate_jwt(user)
    return jsonify({"msg": "Registration successful", "token": token}), 201


@app.route("/login", methods=["POST"])
def login():
    """
    Expected JSON:
    {
        "email": "...",
        "password": "..."
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Missing JSON body"}), 400

    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400

    user_record = users_db.get(email)
    if not user_record:
        return jsonify({"msg": "Invalid credentials"}), 401

    if not check_password(user_record["hashed_password"], password):
        return jsonify({"msg": "Invalid credentials"}), 401

    user = User(email)
    login_user(user)

    token = generate_jwt(user)
    return jsonify({"msg": "Login successful", "token": token}), 200


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"msg": "Logged out"}), 200


@app.route("/protected", methods=["GET"])
@login_required
def protected():
    """A simple protected endpoint accessible to any logged‑in user."""
    return jsonify(
        {
            "msg": f"Hello, {current_user.full_name or current_user.email}! You are authenticated.",
            "email": current_user.email,
            "role": current_user.role,
        }
    ), 200


@app.route("/admin", methods=["GET"])
@role_required("admin")
def admin_panel():
    """Endpoint only accessible to users with the 'admin' role."""
    return jsonify(
        {
            "msg": f"Welcome to the admin panel, {current_user.full_name or current_user.email}.",
            "email": current_user.email,
            "role": current_user.role,
        }
    ), 200


# ---------------------------------------------------------------------------
# Example email verification (placeholder)
# ---------------------------------------------------------------------------
def send_verification_email(email):
    token = serializer.dumps(email, salt="email-verify")
    verify_url = url_for("verify_email", token=token, _external=True)
    msg = Message("Verify your email", recipients=[email])
    msg.body = f"Please click the link to verify your email: {verify_url}"
    mail.send(msg)


@app.route("/verify/<token>")
def verify_email(token):
    try:
        email = serializer.loads(token, salt="email-verify", max_age=3600)
    except (SignatureExpired, BadSignature):
        return jsonify({"msg": "Invalid or expired verification link"}), 400

    user = users_db.get(email)
    if user:
        user["is_verified"] = True
        return jsonify({"msg": "Email verified successfully"}), 200
    return jsonify({"msg": "User not found"}), 404


# ---------------------------------------------------------------------------
# Run the app (development only)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)