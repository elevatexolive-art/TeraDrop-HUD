"""Self-hosted proof-of-work CAPTCHA (Cap.js protocol).
Stateless: all state is encoded in HMAC-signed tokens.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.settings import settings

CHALLENGE_DIFFICULTY = 3   # 16^3 = 4096 avg hashes per challenge
CHALLENGE_COUNT = 2        # keep the browser check usable on mobile WebViews
CHALLENGE_EXPIRY_MS = 10 * 60 * 1000
TOKEN_EXPIRY_MS = 5 * 60 * 1000


def _b64e(data: bytes) -> str:
    return urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return urlsafe_b64decode(text + padding)


def _sign(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(settings.bot_token.encode(), raw, hashlib.sha256).digest()
    return f"{_b64e(raw)}.{_b64e(sig)}"


def _verify(token: str) -> dict | None:
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = _b64d(raw_b64)
        expected = hmac.new(settings.bot_token.encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64d(sig_b64), expected):
            return None
        return json.loads(raw)
    except Exception:
        return None


def create_challenge() -> dict:
    challenges = []
    for _ in range(CHALLENGE_COUNT):
        salt = secrets.token_hex(16)
        challenges.append({"salt": salt, "difficulty": CHALLENGE_DIFFICULTY})
    payload = {
        "exp": int(time.time() * 1000) + CHALLENGE_EXPIRY_MS,
        "challenges": challenges,
    }
    return {"token": _sign(payload), "challenges": challenges}


def redeem(challenge_token: str, solutions: list[int]) -> str | None:
    payload = _verify(challenge_token)
    if not payload or payload.get("exp", 0) < time.time() * 1000:
        return None
    challenges = payload.get("challenges", [])
    if len(solutions) != len(challenges):
        return None
    for ch, sol in zip(challenges, solutions):
        digest = hashlib.sha256(f"{ch['salt']}{sol}".encode()).hexdigest()
        if not digest.startswith("0" * ch["difficulty"]):
            return None
    return _sign({"exp": int(time.time() * 1000) + TOKEN_EXPIRY_MS, "ok": True})


def validate(verification_token: str) -> bool:
    payload = _verify(verification_token)
    return bool(payload and payload.get("ok") and payload.get("exp", 0) > time.time() * 1000)
