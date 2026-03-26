import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Dict

app = FastAPI()

# In‑memory user store: {email: {"hashed_password": bytes, "full_name": str}}
users_db: Dict[str, Dict[str, any]] = {}

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def hash_password(plain_password: str) -> bytes:
    """Hash a plain password using bcrypt.
    Returns the hashed password as bytes.
    """
    # bcrypt.gensalt() generates a salt with a default work factor (12)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """Verify a plain password against the stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

@app.post("/register")
def register(payload: RegisterRequest):
    email = payload.email.lower()
    if email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = hash_password(payload.password)
    users_db[email] = {
        "hashed_password": hashed,
        "full_name": payload.full_name or ""
    }
    return {"msg": "User registered successfully"}

@app.post("/login")
def login(payload: LoginRequest):
    email = payload.email.lower()
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"msg": "Login successful", "full_name": user["full_name"]}

# Optional: a simple health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}
