import os
import jwt
import datetime
import stripe
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Flask, send_from_directory, jsonify, request, g, abort

# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=".",   # Serve static files (style.css, etc.) from project root
    template_folder=".",  # Serve HTML files from project root
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-super-secret")
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_EXP_DELTA_SECONDS"] = 3600  # 1 hour

# Email verification configuration
app.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT", "email-salt")

# Stripe configuration
app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY", "")
app.config["STRIPE_PRICE_ID"] = os.getenv("STRIPE_PRICE_ID", "")
stripe.api_key = app.config["STRIPE_SECRET_KEY"]

# In‑memory user store (email -> dict)
users = {}

# Serializer for email verification tokens
email_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])


# ---------------------------------------------------------------------------
# JWT Helper Functions
# ---------------------------------------------------------------------------
def _generate_token(payload: dict) -> str:
    """Generate a JWT token with an expiration time."""
    exp = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=app.config["JWT_EXP_DELTA_SECONDS"]
    )
    payload.update({"exp": exp})
    token = jwt.encode(
        payload,
        app.config["JWT_SECRET_KEY"],
        algorithm=app.config["JWT_ALGORITHM"],
    )
    # PyJWT may return bytes in older versions; ensure string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _decode_token(token: str):
    """Decode and verify a JWT token. Returns payload or raises jwt exceptions."""
    return jwt.decode(
        token,
        app.config["JWT_SECRET_KEY"],
        algorithms=[app.config["JWT_ALGORITHM"]],
    )


def jwt_required(fn):
    """Decorator to protect routes with JWT authentication."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        else:
            token = request.args.get("token")
        if not token:
            return jsonify({"msg": "Missing or malformed Authorization header"}), 401
        try:
            payload = _decode_token(token)
            g.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"msg": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"msg": "Invalid token"}), 401
        return fn(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Email verification helpers
# ---------------------------------------------------------------------------
def generate_confirmation_token(email: str) -> str:
    """Create a signed token for email verification."""
    return email_serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])


def confirm_token(token: str, expiration: int = 3600) -> str:
    """Validate a token and return the original email if valid."""
    try:
        email = email_serializer.loads(
            token,
            salt=app.config["SECURITY_PASSWORD_SALT"],
            max_age=expiration,
        )
    except SignatureExpired:
        raise SignatureExpired("Token expired")
    except BadSignature:
        raise BadSignature("Invalid token")
    return email


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    """
    Expected JSON:
    {
        "email": "user@example.com",
        "password": "plain-text-password"
    }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    if email in users:
        return jsonify({"msg": "User already exists"}), 400

    # Store user (password stored in plain text for demo purposes only)
    users[email] = {"password": password, "verified": False}

    # Generate verification token (in a real app this would be emailed)
    token = generate_confirmation_token(email)

    return (
        jsonify(
            {
                "msg": "User registered successfully. Verify email using the token.",
                "verification_token": token,
            }
        ),
        201,
    )


@app.route("/verify_email", methods=["GET"])
def verify_email():
    token = request.args.get("token")
    if not token:
        return jsonify({"msg": "Verification token is required"}), 400

    try:
        email = confirm_token(token)
    except SignatureExpired:
        return jsonify({"msg": "Verification token has expired"}), 400
    except BadSignature:
        return jsonify({"msg": "Invalid verification token"}), 400

    user = users.get(email)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    user["verified"] = True
    return jsonify({"msg": "Email verified successfully"}), 200


@app.route("/login", methods=["POST"])
def login():
    """
    Expected JSON:
    {
        "email": "user@example.com",
        "password": "plain-text-password"
    }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = users.get(email)
    if not user or user["password"] != password:
        return jsonify({"msg": "Invalid credentials"}), 401

    if not user.get("verified"):
        return jsonify({"msg": "Email not verified"}), 403

    token = _generate_token({"email": email})
    return jsonify({"token": token}), 200


@app.route("/protected", methods=["GET"])
@jwt_required
def protected():
    """Example protected endpoint."""
    payload = g.get("jwt_payload", {})
    return jsonify({"msg": "Access granted", "payload": payload}), 200


# ---------------------------------------------------------------------------
# Static file serving (fallback to index.html for SPA)
# ---------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_static(path):
    """
    Serve static files from the project root. If the requested file does not exist,
    fall back to serving index.html (useful for single‑page applications).
    """
    if path != "" and os.path.isfile(path):
        return send_from_directory(".", path)
    return send_from_directory(".", "index.html")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"msg": "Resource not found"}), 404


if __name__ == "__main__":
    # Enable debug mode when running directly
    app.run(host="0.0.0.0", port=5000, debug=True)