import os
import jwt
import datetime
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Flask, jsonify, request, abort

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
app.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT", "email-salt")

# In‑memory user store: email -> {password_hash, is_verified}
users = {}

# Serializer for email verification tokens
email_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ---------------------------------------------------------------------------
# Helper functions for JWT
# ---------------------------------------------------------------------------
def _generate_token(payload: dict) -> str:
    """Generate a JWT token with an expiration time."""
    exp = datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config["JWT_EXP_DELTA_SECONDS"])
    payload.update({"exp": exp})
    token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm=app.config["JWT_ALGORITHM"])
    # PyJWT may return bytes in older versions; ensure string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _decode_token(token: str):
    """Decode a JWT token and return its payload. Raises jwt exceptions on failure."""
    return jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=[app.config["JWT_ALGORITHM"]])


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
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = _decode_token(token)
            # Attach payload to request context for downstream use
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return fn(*args, **kwargs)
    return wrapper

# Example protected route for health check (optional)
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
