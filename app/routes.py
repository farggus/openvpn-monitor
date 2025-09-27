# routes.py
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, g, jsonify, render_template

from .config import HISTORY_LOG_PATH, SERVER_STATUS_PATH
from .parser import parse_status_log


logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=None,
)


def is_valid_datetime(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def _parse_optional_float(parts: List[str], index: int) -> Optional[float]:
    if len(parts) <= index:
        return None

    value = parts[index].strip()
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _calculate_duration(start: str, end: Optional[str]) -> Optional[str]:
    if not (is_valid_datetime(start) and end and is_valid_datetime(end)):
        return None

    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    return str(end_dt - start_dt)


def _json_error(message: str, status_code: int = 500, *, code: str = "internal_error"):
    payload = {"error": {"code": code, "message": message}}
    return jsonify(payload), status_code


def _get_cached_clients() -> List[Dict[str, Any]]:
    if "parsed_clients" not in g:
        g.parsed_clients = parse_status_log()
    return g.parsed_clients


def _load_server_status() -> Dict[str, Any]:
    try:
        with open(SERVER_STATUS_PATH, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.exception("[server-status] Failed to read or parse JSON")
        return {
            "status": "Unknown",
            "uptime": "Unknown",
            "local_ip": "0.0.0.0",
            "public_ip": "0.0.0.0",
            "pingable": False,
        }

    pingable = data.get("pingable")
    if isinstance(pingable, str):
        data["pingable"] = pingable.lower() == "yes"

    return data


@app.route("/")
def index():
    return render_template("index.html")


# @app.route('/api/clients')
# def api_clients():
#    clients = parse_status_log()
#    return jsonify({"clients": clients})


@app.route("/api/clients")
def api_clients():
    try:
        clients = _get_cached_clients()
        return jsonify({"clients": clients})
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("[api_clients] Error while fetching clients")
        return _json_error("Failed to fetch clients")


@app.route("/api/history")
def get_history():
    entries: List[Dict[str, Any]] = []
    try:
        if os.path.exists(HISTORY_LOG_PATH):
            with open(HISTORY_LOG_PATH, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) < 4:
                        continue

                    timestamp = parts[0]

                    vpn_ip_legacy = parts[6].strip() if len(parts) > 6 else ""
                    port = parts[7].strip() if len(parts) > 7 else ""
                    raw_session_end = parts[8].strip() if len(parts) > 8 else ""
                    session_end = raw_session_end if is_valid_datetime(raw_session_end) else None
                    vpn_ipv4 = parts[9].strip() if len(parts) > 9 else ""
                    vpn_ipv6 = parts[10].strip() if len(parts) > 10 else ""

                    vpn_ip = vpn_ip_legacy or vpn_ipv4 or vpn_ipv6

                    entry: Dict[str, Any] = {
                        "timestamp": timestamp,
                        "name": parts[1],
                        "ip": parts[2],
                        "session_id": parts[3],
                        "rx": _parse_optional_float(parts, 4),
                        "tx": _parse_optional_float(parts, 5),
                        "vpn_ip": vpn_ip,
                        "vpn_ipv4": vpn_ipv4,
                        "vpn_ipv6": vpn_ipv6,
                        "port": port,
                        "session_end": session_end,
                        "duration": _calculate_duration(timestamp, session_end),
                    }
                    if not entry["vpn_ipv4"] and vpn_ip and "." in vpn_ip:
                        entry["vpn_ipv4"] = vpn_ip
                    if not entry["vpn_ipv6"] and vpn_ip and ":" in vpn_ip:
                        entry["vpn_ipv6"] = vpn_ip
                    entries.append(entry)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Error reading history log")
        return _json_error("Failed to read history log")

    return jsonify(entries)


@app.route("/api/server-status")
def get_server_status():
    data = _load_server_status()

    try:
        clients = _get_cached_clients()
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("[server-status] Failed to parse status log")
        clients = []

    total_rx = sum(c.get("bytes_received", 0) for c in clients)
    total_tx = sum(c.get("bytes_sent", 0) for c in clients)

    data.update(
        {
            "mode": "server",
            "clients": len(clients),
            "total_rx": round(total_rx / 1024 / 1024, 2),
            "total_tx": round(total_tx / 1024 / 1024, 2),
        }
    )

    return jsonify(data)


if __name__ == "__main__":
    app.run()
