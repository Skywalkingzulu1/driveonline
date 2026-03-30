import os
from flask import Flask, send_from_directory, jsonify, abort

# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=".",   # Serve static files (style.css, etc.) from project root
    template_folder=".",  # Serve HTML files from project root
)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-super-secret")
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_EXP_DELTA_SECONDS"] = 3600  # 1 hour

# AWS credentials (optional – default to empty strings if not provided)
app.config["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
app.config["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# ---------------------------------------------------------------------------
# Minimal routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the main HTML page."""
    return send_from_directory(app.template_folder, "index.html")

# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    """Return a simple health status for the service."""
    return jsonify({"status": "healthy"}), 200

# ---------------------------------------------------------------------------
# Verification endpoints (gracefully handle missing AWS credentials)
# ---------------------------------------------------------------------------
def _aws_status():
    """Internal helper to determine AWS credential status."""
    access_key = app.config.get("AWS_ACCESS_KEY_ID")
    secret_key = app.config.get("AWS_SECRET_ACCESS_KEY")
    return "configured" if access_key and secret_key else "missing"


@app.route("/verify-aws")
def verify_aws():
    """Return a JSON indicating whether AWS credentials are present.
    This endpoint replaces any previous verification logic that raised an
    "Unknown verification error" when the credentials were absent.
    """
    status = _aws_status()
    return jsonify({"aws_credentials": status})


@app.route("/verify")
def verify():
    """Alias for /verify-aws to maintain backward compatibility with
    callers that expect a generic verification endpoint.
    """
    status = _aws_status()
    return jsonify({"aws_credentials": status})

# ---------------------------------------------------------------------------
# Static file serving (catch‑all). Placed after API routes to avoid shadowing.
# ---------------------------------------------------------------------------
@app.route("/<path:filename>")
def static_files(filename):
    """Serve static assets such as CSS, JS, and images if they exist.
    If the requested file does not exist, return a 404.
    """
    static_path = os.path.join(app.static_folder, filename)
    if os.path.isfile(static_path):
        return send_from_directory(app.static_folder, filename)
    else:
        abort(404)

# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run Flask on 0.0.0.0:8000 to match Docker configuration
    app.run(host="0.0.0.0", port=8000)