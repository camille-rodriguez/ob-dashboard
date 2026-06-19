"""MAAS API client for querying machine states."""

import os
from typing import Optional
from collections import Counter

import requests
from requests_oauthlib import OAuth1


# MAAS API key format: "<consumer_key>:<token_key>:<token_secret>"
_MAAS_API_KEY = os.environ.get("MAAS_API_KEY", "")
_MAAS_URL = os.environ.get("MAAS_URL", "")  # e.g. http://10.0.0.1:5240/MAAS

MACHINE_STATES = ("ready", "deployed", "broken")


def _build_auth() -> Optional[OAuth1]:
    """Build an OAuth1 session from the MAAS API key, or return None."""
    if not _MAAS_API_KEY:
        return None
    parts = _MAAS_API_KEY.split(":")
    if len(parts) != 3:
        return None
    consumer_key, token_key, token_secret = parts
    return OAuth1(
        client_key=consumer_key,
        resource_owner_key=token_key,
        resource_owner_secret=token_secret,
        signature_method="PLAINTEXT",
    )


def get_maas_status(
    maas_url: str = _MAAS_URL, api_key: str = _MAAS_API_KEY, timeout: int = 5
) -> dict:
    """
    Query the MAAS API and return a status dictionary::

        {
            "reachable": bool,
            "error": str | None,
            "machine_counts": {"ready": int, "deployed": int, "broken": int},
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

    auth: Optional[OAuth1] = None
    if api_key:
        parts = api_key.split(":")
        if len(parts) == 3:
            consumer_key, token_key, token_secret = parts
            auth = OAuth1(
                client_key=consumer_key,
                resource_owner_key=token_key,
                resource_owner_secret=token_secret,
                signature_method="PLAINTEXT",
            )

    api_base = maas_url.rstrip("/") + "/api/2.0"
    machines_url = api_base + "/machines/"

    try:
        resp = requests.get(machines_url, auth=auth, timeout=timeout)
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
        result["error"] = f"MAAS API error: {exc}"
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"Unexpected error: {exc}"

    return result
