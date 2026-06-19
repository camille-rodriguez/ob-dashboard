"""MAAS API client for querying machine states."""

import os
import time
import uuid
from typing import Optional
from collections import Counter
from urllib.parse import quote

import requests


# MAAS API key format: "<consumer_key>:<consumer_token>:<secret>"
_MAAS_API_KEY = os.environ.get("MAAS_API_KEY", "")
_MAAS_URL = os.environ.get("MAAS_URL", "")  # e.g. http://10.0.0.1:5240/MAAS

MACHINE_STATES = ("ready", "allocated", "broken", "deploying", "deployed")


def _build_auth_headers(api_key: str) -> Optional[dict]:
    """Build a MAAS OAuth 1.0 PLAINTEXT Authorization header, or return None."""
    api_key = api_key.strip()
    if not api_key:
        return None
    parts = [part.strip() for part in api_key.split(":", 2)]
    if len(parts) != 3 or not all(parts):
        return None
    consumer_key, consumer_token, secret = parts
    oauth_signature = quote(f"&{secret}", safe="")
    header_value = (
        f'OAuth oauth_version="1.0",'
        f' oauth_signature_method="PLAINTEXT",'
        f' oauth_consumer_key="{consumer_key}",'
        f' oauth_token="{consumer_token}",'
        f' oauth_signature="{oauth_signature}",'
        f' oauth_nonce="{uuid.uuid4().hex}",'
        f' oauth_timestamp="{int(time.time())}"'
    )
    return {"Authorization": header_value}


def get_maas_status(
    maas_url: str = _MAAS_URL, api_key: str = _MAAS_API_KEY, timeout: int = 5
) -> dict:
    """
    Query the MAAS API and return a status dictionary::

        {
            "reachable": bool,
            "error": str | None,
            "machine_counts": {
                "ready": int,
                "deployed": int,
                "deploying": int,
                "allocated": int,
                "broken": int,
            },
        }
    """
    result: dict = {
        "reachable": False,
        "error": None,
        "machine_counts": {state: 0 for state in MACHINE_STATES},
    }

    if not maas_url:
        result["error"] = "MAAS_URL is not configured."
        return result

    headers = _build_auth_headers(api_key)
    if api_key and headers is None:
        result["error"] = (
            "MAAS_API_KEY is not configured correctly. Expected "
            "<consumer_key>:<consumer_token>:<secret>."
        )
        return result

    api_base = maas_url.rstrip("/") + "/api/2.0"
    machines_url = api_base + "/machines/"

    try:
        resp = requests.get(machines_url, headers=headers, timeout=timeout)
        print(f"[resp] {machines_url}")
        resp.raise_for_status()
        result["reachable"] = True
        machines = resp.json()
        counts: Counter = Counter()
        for machine in machines:
            status = machine.get("status_name", "").lower()
            if status in MACHINE_STATES:
                counts[status] += 1
        result["machine_counts"] = {state: counts[state] for state in MACHINE_STATES}
    except requests.exceptions.ConnectionError as exc:
        result["error"] = f"Cannot connect to MAAS: {exc}"
    except requests.exceptions.Timeout:
        result["error"] = "MAAS API request timed out."
    except requests.exceptions.HTTPError as exc:
        result["reachable"] = True  # server responded, but with an error
        body = exc.response.text[:500] if exc.response is not None else ""
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        print(f"[maas_client] HTTP {status_code} from {machines_url}")
        print(f"[maas_client] Response body: {body}")
        result["error"] = f"MAAS API error: {exc}" + (f" — {body}" if body else "")
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"Unexpected error: {exc}"

    return result
