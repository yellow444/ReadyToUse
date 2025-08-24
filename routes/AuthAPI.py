from fastapi import APIRouter
from pydantic import BaseModel
import os
import json
import base64
import hmac
import hashlib
import requests

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "secret")

class AuthRequest(BaseModel):
    email: str
    password: str


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_token(email: str, password: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"email": email, "password": password}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)
    return f"{message}.{signature_b64}", True


@router.post("/token")
def get_token(auth: AuthRequest):
    token, iferr = _create_token(auth.email, auth.password)
    if iferr == False:
        return {"error": "Invalid credentials"}
    response = requests.post(
        "http://localhost:8005/UserId/",
        headers={"Content-Type": "application/json"},
        json={"token": token},
        timeout=90,
    )
    response.raise_for_status()
    user = response.json()
    try:
        if user.get("ID") == 1:
            return {"token": token}
    except Exception:
        return {"error": "Invalid credentials"}
    return {"error": "Invalid credentials"}
