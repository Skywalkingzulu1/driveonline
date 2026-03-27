import os
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional

from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = FastAPI()

# Initialize Flask-Bcrypt (no Flask app needed for hashing)
bcrypt = Bcrypt()

# Secret key for token generation – in production use a secure env variable
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
serializer = URLSafeTimedSerializer(SECRET_KEY)

# In‑memory user store: {email: {"hashed_password": bytes, "full_name": str, "is_verified": bool}}
users_db: Dict[str, Dict[str, Any]] = {}

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def hash_password(plain_password: str) -> bytes:
    """
    Hash a plain password using Flask‑Bcrypt.
    Returns the hashed password as bytes.
    """
    # generate_password_hash returns a bytes object by default
    return bcrypt.generate_password_hash(plain_password)

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """
    Verify a plain password against the stored Flask‑Bcrypt hash.
    """
    return bcrypt.check_password_hash(hashed_password, plain_password)

def generate_verification_token(email: str) -> str:
    """
    Create a time‑limited token for email verification.
    """
    return serializer.dumps(email)

def confirm_verification_token(token: str, expiration: int = 3600) -> str:
    """
    Validate a verification token and return the associated email.
    Raises HTTPException if token is invalid or expired.
    """
    try:
        email = serializer.loads(token, max_age=expiration)
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Verification token expired")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    return email

@app.post("/register")
def register(payload: RegisterRequest):
    email = payload.email.lower()
    if email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = hash_password(payload.password)
    users_db[email] = {
        "hashed_password": hashed,
        "full_name": payload.full_name or "",
        "is_verified": False
    }

    # Generate verification token and (placeholder) send email
    token = generate_verification_token(email)
    verification_link = f"http://localhost:8000/verify-email?token={token}"
    # In a real application, send this link via email.
    print(f"Verification link for {email}: {verification_link}")

    return {"msg": "User registered successfully. Please check your email to verify the account."}

@app.get("/verify-email")
def verify_email(token: str = Query(..., description="Verification token sent to user's email")):
    email = confirm_verification_token(token)
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["is_verified"]:
        return {"msg": "Account already verified."}
    user["is_verified"] = True
    return {"msg": "Email verified successfully. You can now log in."}

@app.post("/login")
def login(payload: LoginRequest):
    email = payload.email.lower()
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")
    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"msg": "Login successful", "full_name": user["full_name"]}

# Optional: a simple health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}