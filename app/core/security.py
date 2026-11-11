import hashlib
import hmac
import re
import time

from fastapi import Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided_key: str | None = Security(api_key_header)) -> None:
    """Allow a request only if it carries the configured API key."""
    configured_key = settings.fleet_api_key

    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if provided_key is None or not hmac.compare_digest(
        provided_key.encode("utf-8"),
        configured_key.get_secret_value().encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def require_webhook_signature(
    request: Request,
    timestamp_header: str | None = Header(
        default=None,
        alias="X-Webhook-Timestamp",
    ),
    signature_header: str | None = Header(
        default=None,
        alias="X-Webhook-Signature",
    ),
) -> None:
    """Verify the timestamp and HMAC signature of a webhook request."""
    configured_secret = settings.fleet_webhook_secret

    if configured_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook authentication is not configured.",
        )

    if timestamp_header is None or signature_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook authentication headers.",
        )

    if not re.fullmatch(r"[0-9]{1,12}", timestamp_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook timestamp.",
        )

    timestamp = int(timestamp_header)
    current_timestamp = int(time.time())

    if abs(current_timestamp - timestamp) > settings.fleet_webhook_tolerance_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook timestamp is outside the permitted time window.",
        )

    signature_match = re.fullmatch(
        r"sha256=([0-9a-fA-F]{64})",
        signature_header,
    )

    if signature_match is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature format.",
        )

    supplied_signature = signature_match.group(1).lower()

    raw_body = await request.body()

    signed_message = timestamp_header.encode("utf-8") + b"." + raw_body

    expected_signature = hmac.new(
        configured_secret.get_secret_value().encode("utf-8"),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        supplied_signature,
        expected_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )
