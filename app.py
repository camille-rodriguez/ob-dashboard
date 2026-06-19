"""Flask web application – Orangebox Dashboard."""

import json
import os
import re
from pathlib import Path
from flask import Flask, render_template

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        env_path = Path(__file__).with_name(".env")
        if not env_path.exists():
            return
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_dotenv()

from network_utils import is_host_reachable
from maas_client import get_maas_status

app = Flask(__name__)


def _parse_hosts(value: str) -> list[str]:
    hosts: list[str] = []
    for chunk in value.replace("\n", ",").split(","):
        host = chunk.strip()
        if host:
            hosts.append(host)
    return hosts


def _alphanum_key(value: str) -> list:
    parts = re.split(r"(\d+)", value.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def _load_orangeboxes_file(file_path: str) -> list[dict]:
    if not file_path:
        return []

    path = Path(file_path)
    if not path.is_absolute():
        path = Path(__file__).with_name(file_path)

    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw, list):
        return []

    orangeboxes: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        hostname = str(item.get("hostname", "")).strip()
        ip = str(item.get("ip", "")).strip()
        if not hostname and not ip:
            continue
        orangeboxes.append(
            {
                "hostname": hostname,
                "ip": ip,
            }
        )
    return orangeboxes


def _get_config() -> dict:
    ob_file = os.environ.get("ORANGEBOXES_FILE", "orangeboxes.json").strip()
    orangeboxes = _load_orangeboxes_file(ob_file)

    ob_hosts = _parse_hosts(os.environ.get("OB_HOSTS", ""))
    ob_host = os.environ.get("OB_HOST", "").strip()
    if not orangeboxes:
        if not ob_hosts and ob_host:
            ob_hosts = [ob_host]
        orangeboxes = [{"hostname": "", "ip": host} for host in ob_hosts]

    return {
        "ob_host": ob_host,
        "ob_hosts": ob_hosts,
        "orangeboxes": orangeboxes,
        "orangeboxes_file": ob_file,
        "maas_url": os.environ.get("MAAS_URL", ""),
        "maas_api_key": os.environ.get("MAAS_API_KEY", ""),
    }


@app.route("/")
def index():
    cfg = _get_config()
    inventory = cfg["orangeboxes"]

    sorted_inventory = sorted(
        inventory,
        key=lambda box: _alphanum_key(box["hostname"] or box["ip"]),
    )

    orangeboxes = [
        {
            "hostname": box["hostname"],
            "ip": box["ip"],
            "probe": box["ip"] or box["hostname"],
            "powered_on": is_host_reachable(box["ip"] or box["hostname"]),
        }
        for box in sorted_inventory
        if box["ip"] or box["hostname"]
    ]

    # MAAS status
    maas_status = get_maas_status(
        maas_url=cfg["maas_url"],
        api_key=cfg["maas_api_key"],
    )

    return render_template(
        "index.html",
        ob_host=cfg["ob_host"],
        ob_hosts=cfg["ob_hosts"],
        orangeboxes=orangeboxes,
        orangeboxes_file=cfg["orangeboxes_file"],
        maas_reachable=maas_status["reachable"],
        maas_error=maas_status["error"],
        machine_counts=maas_status["machine_counts"],
    )


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
