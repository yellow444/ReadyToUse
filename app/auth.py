from __future__ import annotations

import os
import json
import base64
import hmac
import hashlib
from typing import Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from cachetools import TTLCache

from .userid import get_user_id_from_file

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "secret")

_token_cache: TTLCache[Tuple[str, str], str] = TTLCache(maxsize=1024, ttl=60)
_verify_cache: TTLCache[str, dict] = TTLCache(maxsize=1024, ttl=60)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _create_token(email: str, password: str) -> str:
    key = (email, password)
    token = _token_cache.get(key)
    if token is not None:
        return token

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"email": email, "password": password}
    header_b64 = _b64url_encode(json.dumps(
        header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(
        payload, separators=(",", ":")).encode())
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY.encode(),
                         message.encode(), hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    token = f"{message}.{signature_b64}"
    _token_cache[key] = token
    return token


def _verify_token(token: str) -> Optional[dict]:
    cached = _verify_cache.get(token)
    if cached is not None:
        return cached
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        message = f"{header_b64}.{payload_b64}"
        expected = hmac.new(SECRET_KEY.encode(),
                            message.encode(), hashlib.sha256).digest()
        signature = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected, signature):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode())
        _verify_cache[token] = payload
        return payload
    except Exception:
        return None


@router.post("/token")
def get_token(body: dict):
    email = str(body.get("email", ""))
    password = str(body.get("password", ""))
    token = _create_token(email, password)
    if _verify_token(token) is None:
        return ORJSONResponse({"error": "Invalid credentials"}, status_code=403)

    user_id = get_user_id_from_file(token)
    if user_id == 1:
        return ORJSONResponse({"token": token}, status_code=200)
    return ORJSONResponse({"error": "Invalid credentials"}, status_code=403)
