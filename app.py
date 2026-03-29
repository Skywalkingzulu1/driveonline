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

def send_reset_email(to_email, token):
    """Send password‑reset email containing a verification link."""
    reset_url = url_for('reset_password', token=token, _external=True)
    html = render_template_string('''
        <p>Hello,</p>
        <p>You requested a password reset. Click the link below to set a new password:</p>
        <p><a href="{{ reset_url }}">{{ reset_url }}</a></p>
        <p>If you did not request this, please ignore this email.</p>
    ''', reset_url=reset_url)

    msg = Message(subject="Password Reset Request",
                  recipients=[to_email],
                  html=html)
    mail.send(msg)


# ---------------------------------------------------------------------------
# Routes for password reset
# ---------------------------------------------------------------------------

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Render a form to request a password reset and handle its submission."""
    if request.method == 'GET':
        return render_template_string('''
            <h2>Reset Password</h2>
            <form method="post">
                <label for="email">Enter your email address:</label><br>
                <input type="email" id="email" name="email" required><br><br>
                <button type="submit">Send Reset Link</button>
            </form>
        ''')

    # POST handling
    email = request.form.get('email')
    if not email or email not in users_db:
        # For security, do not reveal whether the email exists.
        return jsonify({"message": "If the email is registered, a reset link will be sent."}), 200

    # Generate a time‑limited token (valid for 1 hour)
    token = serializer.dumps(email, salt='password-reset-salt')
    try:
        send_reset_email(email, token)
    except Exception as e:
        # In production you would log the exception.
        return jsonify({"error": "Failed to send email."}), 500

    return jsonify({"message": "If the email is registered, a reset link will be sent."}), 200


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Validate token and allow the user to set a new password."""
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        return render_template_string('<p>The reset link has expired.</p>'), 400
    except BadSignature:
        return render_template_string('<p>Invalid reset link.</p>'), 400

    if request.method == 'GET':
        return render_template_string('''
            <h2>Set New Password</h2>
            <form method="post">
                <label for="password">New Password:</label><br>
                <input type="password" id="password" name="password" required><br><br>
                <label for="confirm">Confirm Password:</label><br>
                <input type="password" id="confirm" name="confirm" required><br><br>
                <button type="submit">Reset Password</button>
            </form>
        ''')

    # POST handling – update password
    password = request.form.get('password')
    confirm = request.form.get('confirm')
    if not password or not confirm or password != confirm:
        return render_template_string('<p>Passwords do not match.</p>'), 400

    # Hash the new password and store it
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    users_db[email]['hashed_password'] = hashed

    return render_template_string('<p>Password has been reset successfully.</p>'), 200


# ---------------------------------------------------------------------------
# Example placeholder routes (login, register, etc.)
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    return render_template_string('<h1>Welcome to Drive Online</h1>')

# The rest of your existing routes (login, register, etc.) would follow here.

if __name__ == '__main__':
    app.run(debug=True)