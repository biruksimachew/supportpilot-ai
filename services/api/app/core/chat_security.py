import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.core.config import settings


class ChatSessionTokenError(ValueError):
    """Raised when a public chat session token is invalid."""


def _get_secret() -> bytes:
    secret = settings.chat_session_secret.encode("utf-8")

    if len(secret) < 32:
        raise RuntimeError(
            "CHAT_SESSION_SECRET must contain at least 32 characters."
        )

    return secret


def _encode(value: bytes) -> str:
    return (
        base64.urlsafe_b64encode(value)
        .decode("ascii")
        .rstrip("=")
    )


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(
        value + padding
    )


def create_chat_session() -> tuple[UUID, str, datetime]:
    session_id = uuid4()

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.chat_session_ttl_minutes
        )
    )

    payload = {
        "sid": str(session_id),
        "exp": int(expires_at.timestamp()),
    }

    payload_encoded = _encode(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )

    signature = hmac.new(
        _get_secret(),
        payload_encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()

    token = (
        f"{payload_encoded}."
        f"{_encode(signature)}"
    )

    return session_id, token, expires_at


def verify_chat_session_token(
    session_id: UUID,
    token: str,
) -> None:
    try:
        payload_encoded, signature_encoded = (
            token.split(".", 1)
        )
    except ValueError as exc:
        raise ChatSessionTokenError(
            "Malformed chat session token."
        ) from exc

    expected_signature = hmac.new(
        _get_secret(),
        payload_encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        supplied_signature = _decode(
            signature_encoded
        )
    except Exception as exc:
        raise ChatSessionTokenError(
            "Malformed chat session signature."
        ) from exc

    if not hmac.compare_digest(
        expected_signature,
        supplied_signature,
    ):
        raise ChatSessionTokenError(
            "Invalid chat session signature."
        )

    try:
        payload = json.loads(
            _decode(payload_encoded)
        )
    except Exception as exc:
        raise ChatSessionTokenError(
            "Malformed chat session payload."
        ) from exc

    if payload.get("sid") != str(session_id):
        raise ChatSessionTokenError(
            "Chat session token does not match session."
        )

    expires_at = payload.get("exp")

    if not isinstance(expires_at, int):
        raise ChatSessionTokenError(
            "Chat session token has invalid expiry."
        )

    if expires_at <= int(time.time()):
        raise ChatSessionTokenError(
            "Chat session has expired."
        )