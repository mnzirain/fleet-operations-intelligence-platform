import hashlib
import hmac
import json
import time

from tests.constants import TEST_WEBHOOK_SECRET


def make_signed_webhook_request(
    payload: dict,
    *,
    timestamp: int | None = None,
) -> tuple[bytes, dict[str, str]]:
    """Serialize a payload and create headers for a signed webhook request."""
    if timestamp is None:
        timestamp = int(time.time())

    body = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    signed_message = str(timestamp).encode("utf-8") + b"." + body

    signature = hmac.new(
        TEST_WEBHOOK_SECRET.encode("utf-8"),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Timestamp": str(timestamp),
        "X-Webhook-Signature": f"sha256={signature}",
    }

    return body, headers
