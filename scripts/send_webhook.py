import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from uuid import uuid4


def main() -> int:
    """Send a signed demonstration fleet event to the API."""
    secret = os.environ.get("FLEET_WEBHOOK_SECRET")

    if not secret or len(secret.strip()) < 32:
        print("Error: A valid FLEET_WEBHOOK_SECRET is required.")
        return 1

    api_url = os.environ.get(
        "FLEET_API_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    vehicle_id = os.environ.get("FLEET_DEMO_VEHICLE_ID")

    if not vehicle_id:
        print("Error: FLEET_DEMO_VEHICLE_ID is not configured.")
        return 1

    event = {
        "source_event_id": f"demo-{uuid4()}",
        "vehicle_id": vehicle_id,
        "event_type": "SPEED",
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": {
            "speed": 85.0,
            "latitude": -26.6731,
            "longitude": 27.9261,
        },
    }

    body = json.dumps(
        event,
        separators=(",", ":"),
    ).encode("utf-8")

    timestamp = str(int(time.time()))
    signed_message = timestamp.encode("utf-8") + b"." + body

    signature = hmac.new(
        secret.strip().encode("utf-8"),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Signature": f"sha256={signature}",
    }

    request = urllib.request.Request(
        url=f"{api_url}/fleet-events/",
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read().decode("utf-8")

            print(f"HTTP status: {response.status}")
            print("Response:")

            try:
                parsed_response = json.loads(response_body)
                print(json.dumps(parsed_response, indent=2))
            except json.JSONDecodeError:
                print(response_body)

            return 0

    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")

        print(f"HTTP error: {exc.code}")
        print("Response:")
        print(response_body)

        return 1

    except urllib.error.URLError as exc:
        print(f"Connection error: {exc.reason}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
