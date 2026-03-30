import os
from flask import Flask, send_from_directory

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

# ---------------------------------------------------------------------------
# Minimal routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the main HTML page."""
    return send_from_directory(app.template_folder, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve static assets such as CSS, JS, and images."""
    return send_from_directory(app.static_folder, filename)


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run on all interfaces to be reachable from Docker, etc.
    app.run(host="0.0.0.0", port=5000, debug=True)