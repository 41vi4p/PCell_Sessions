
from fastapi import FastAPI, HTTPException, Body, Header
from starlette.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import database
import time
import json
import base64
import hmac
import hashlib
import os

app = FastAPI()

# Serving the static HTML files
app.mount("/static", StaticFiles(directory="static"), name="static")


class LoginRequest(BaseModel):
    roll: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    roll: str
    name: str
    email: str


class Email(BaseModel):
    id: str
    sender: str
    subject: str
    timestamp: str
    body: str


class EmailsResponse(BaseModel):
    emails: List[Email]


SECRET_KEY = os.environ.get("CRC_SECRET_KEY", "changeme_secret")
TOKEN_EXP_SECONDS = 60 * 60  # 1 hour


def _b64encode(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(s: str) -> dict:
    padding = "=" * (-len(s) % 4)
    raw = base64.urlsafe_b64decode((s + padding).encode())
    return json.loads(raw.decode())


def create_token(roll: str, expires_in: int = TOKEN_EXP_SECONDS) -> str:
    payload = {"roll": roll, "exp": int(time.time()) + expires_in}
    b64 = _b64encode(payload)
    sig = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def verify_token(token: str) -> Optional[dict]:
    try:
        b64, sig = token.split(".")
        expected = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        payload = _b64decode(b64)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/dashboard")
async def dashboard():
    return FileResponse("static/dashboard.html")


@app.post("/api/login", response_model=LoginResponse)
async def login(data: dict = Body(...)):
    # accept both JSON matching LoginRequest or a plain dict from the frontend
    roll = data.get("roll")
    pwd = data.get("password")
    user = database.get_user(roll)
    if not user or user.get("password") != pwd:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(roll)
    return {
        "access_token": token,
        "roll": roll,
        "name": user.get("name"),
        "email": user.get("email"),
    }


@app.get("/api/get-emails", response_model=EmailsResponse)
async def fetch_emails(authorization: Optional[str] = Header(None)):
    """Requires header: Authorization: Bearer <token>"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = parts[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    roll = payload.get("roll")
    raw_emails = database.get_student_emails(roll)
    emails = [Email(**e) for e in raw_emails]
    return {"emails": emails}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
