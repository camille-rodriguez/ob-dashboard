"""Flask web application – Orangebox Dashboard."""

import os
from flask import Flask, render_template

from network_utils import is_host_reachable
from maas_client import get_maas_status

app = Flask(__name__)


def _get_config() -> dict:
    return {
        "ob_host": os.environ.get("OB_HOST", ""),
        "maas_url": os.environ.get("MAAS_URL", ""),
        "maas_api_key": os.environ.get("MAAS_API_KEY", ""),
    }


@app.route("/")
def index():
    cfg = _get_config()
    ob_host = cfg["ob_host"]

    # Power status: ping the orangebox
    powered_on = is_host_reachable(ob_host) if ob_host else False

    # MAAS status
    maas_status = get_maas_status(
        maas_url=cfg["maas_url"],
        api_key=cfg["maas_api_key"],
    )

    return render_template(
        "index.html",
        ob_host=ob_host,
        powered_on=powered_on,
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
