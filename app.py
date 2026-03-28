from flask import Flask, request, jsonify, url_for, redirect
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os

# ---------------------------------------------------------------------------
# Flask application setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
# In a real deployment, load these from environment variables or a config file
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-secret-key')
# Flask‑Mail configuration (using console backend for demonstration)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 1025))  # default to a local debug server
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'false').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'no-reply@example.com')

mail = Mail(app)
bcrypt = Bcrypt(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# ---------------------------------------------------------------------------
# In‑memory user store
# ---------------------------------------------------------------------------
# Structure: {email: {"hashed_password": bytes, "full_name": str, "is_verified": bool}}
users_db = {}

# ---------------------------------------------------------------------------
# Flask‑Login user model
# ---------------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, email):
        self.id = email
        self.email = email
        user_record = users_db.get(email)
        self.full_name = user_record.get('full_name') if user_record else ''
        self.is_verified = user_record.get('is_verified') if user_record else False

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
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# ---------------------------------------------------------------------------
# Helper functions for password handling and token management
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> bytes:
    """Hash a plain password using Flask‑Bcrypt and return the bytes."""
    return bcrypt.generate_password_hash(plain_password)

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """Check a plain password against a stored hash."""
    return bcrypt.check_password_hash(hashed_password, plain_password)

def generate_verification_token(email: str) -> str:
    """Create a time‑limited token for email verification."""
    return serializer.dumps(email)

def confirm_verification_token(token: str, expiration: int = 3600) -> str:
    """Validate a verification token and return the associated email.
    Raises a ValueError if the token is invalid or expired.
    """
    try:
        email = serializer.loads(token, max_age=expiration)
    except SignatureExpired:
        raise ValueError('Verification token expired')
    except BadSignature:
        raise ValueError('Invalid verification token')
    return email

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'detail': 'Invalid JSON payload'}), 400
    email = data.get('email', '').lower()
    password = data.get('password')
    full_name = data.get('full_name', '')
    if not email or not password:
        return jsonify({'detail': 'Email and password are required'}), 400
    if email in users_db:
        return jsonify({'detail': 'User already exists'}), 400
    hashed = hash_password(password)
    users_db[email] = {
        'hashed_password': hashed,
        'full_name': full_name,
        'is_verified': False
    }
    # Send verification email
    token = generate_verification_token(email)
    verification_url = url_for('verify_email', token=token, _external=True)
    try:
        msg = Message('Verify Your Account', recipients=[email])
        msg.body = f'Please click the link to verify your account: {verification_url}'
        mail.send(msg)
    except Exception as e:
        # In a development environment without a real mail server, fallback to console output
        print(f'Verification link for {email}: {verification_url}')
    return jsonify({'msg': 'User registered successfully. Please check your email to verify the account.'})

@app.route('/verify-email')
def verify_email():
    token = request.args.get('token')
    if not token:
        return jsonify({'detail': 'Missing token'}), 400
    try:
        email = confirm_verification_token(token)
    except ValueError as ve:
        return jsonify({'detail': str(ve)}), 400
    user_record = users_db.get(email)
    if not user_record:
        return jsonify({'detail': 'User not found'}), 404
    user_record['is_verified'] = True
    return jsonify({'msg': 'Email verified successfully. You may now log in.'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'detail': 'Invalid JSON payload'}), 400
    email = data.get('email', '').lower()
    password = data.get('password')
    if not email or not password:
        return jsonify({'detail': 'Email and password are required'}), 400
    user_record = users_db.get(email)
    if not user_record:
        return jsonify({'detail': 'Invalid credentials'}), 401
    if not user_record.get('is_verified'):
        return jsonify({'detail': 'Email not verified'}), 403
    if not verify_password(password, user_record['hashed_password']):
        return jsonify({'detail': 'Invalid credentials'}), 401
    user = User(email)
    login_user(user)
    return jsonify({'msg': 'Logged in successfully'})

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return jsonify({'msg': 'Logged out successfully'})

# Example protected route
@app.route('/profile')
@login_required
def profile():
    return jsonify({
        'email': current_user.email,
        'full_name': current_user.full_name,
        'is_verified': current_user.is_verified
    })

# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # For development purposes only; use a proper WSGI server in production
    app.run(host='0.0.0.0', port=8000, debug=True)
