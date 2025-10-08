# routes.py
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Flask, g, jsonify, render_template, request

from .config import ACTIVE_SESSIONS_PATH, HISTORY_LOG_PATH, SERVER_STATUS_PATH
from .parser import load_active_sessions, parse_status_log
from .traffic_collector import get_metrics_for_period


logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)


def is_valid_datetime(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def _parse_optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
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


def _normalize_history_entry(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    required_fields = ("timestamp", "name", "ip", "session_id")

    if not all(raw.get(field) for field in required_fields):
        return None

    timestamp = str(raw["timestamp"])
    session_end_raw = raw.get("session_end")
    session_end = session_end_raw if isinstance(session_end_raw, str) and is_valid_datetime(session_end_raw) else None

    vpn_ipv4 = (raw.get("vpn_ipv4") or "").strip()
    vpn_ipv6 = (raw.get("vpn_ipv6") or "").strip()
    vpn_ip = (raw.get("vpn_ip") or "").strip() or vpn_ipv4 or vpn_ipv6
    port = raw.get("port")
    if port is not None:
        port = str(port)

    # Extract location data
    location = raw.get("location")
    if not isinstance(location, dict):
        location = {
            "city": None,
            "country": None,
            "latitude": None,
            "longitude": None
        }

    entry: Dict[str, Any] = {
        "timestamp": timestamp,
        "name": str(raw.get("name", "")),
        "ip": str(raw.get("ip", "")),
        "session_id": str(raw.get("session_id", "")),
        "rx": _parse_optional_float(raw.get("rx")),
        "tx": _parse_optional_float(raw.get("tx")),
        "vpn_ip": vpn_ip,
        "vpn_ipv4": vpn_ipv4 or (vpn_ip if "." in vpn_ip else ""),
        "vpn_ipv6": vpn_ipv6 or (vpn_ip if ":" in vpn_ip else ""),
        "port": port or "",
        "session_end": session_end,
        "duration": _calculate_duration(timestamp, session_end),
        "location": location,
    }

    return entry


def _load_history_entries() -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []

    if not os.path.exists(HISTORY_LOG_PATH):
        return entries

    with open(HISTORY_LOG_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                entry = _normalize_history_entry(item)
                if entry:
                    entries.append(entry)

    return entries


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def _aggregate_client_stats() -> List[Dict[str, Any]]:
    history_entries = _load_history_entries()
    clients_map: Dict[str, Dict[str, Any]] = {}

    def _ensure_client(name: str) -> Dict[str, Any]:
        if name not in clients_map:
            clients_map[name] = {
                "name": name,
                "is_online": False,
                "sessions": 0,
                "total_rx_mb": 0.0,
                "total_tx_mb": 0.0,
                "total_duration_seconds": 0,
                "last_seen": None,
                "_closed_sessions": set(),
                "_has_active_session": False,
            }
        return clients_map[name]

    for entry in history_entries:
        info = _ensure_client(entry["name"])

        session_end = entry.get("session_end")
        if session_end:
            session_id = entry.get("session_id")
            if session_id:
                info["_closed_sessions"].add(session_id)
            else:
                info["_closed_sessions"].add((entry.get("timestamp"), session_end))

        if entry["rx"] is not None:
            info["total_rx_mb"] += entry["rx"]
        if entry["tx"] is not None:
            info["total_tx_mb"] += entry["tx"]

        start_dt = _parse_datetime(entry["timestamp"])
        end_dt = _parse_datetime(entry["session_end"])
        if start_dt and end_dt and end_dt >= start_dt:
            info["total_duration_seconds"] += int((end_dt - start_dt).total_seconds())

        for candidate in (entry.get("session_end"), entry.get("timestamp")):
            candidate_dt = _parse_datetime(candidate)
            if not candidate_dt:
                continue
            current_last_seen = info.get("last_seen")
            if current_last_seen is None or candidate_dt > current_last_seen:
                info["last_seen"] = candidate_dt

    active_clients = _get_cached_clients()
    now = datetime.now()

    for client in active_clients:
        name = client.get("common_name")
        if not name:
            continue

        info = _ensure_client(name)
        info["is_online"] = True
        info["_has_active_session"] = True

        connected_since = _parse_datetime(client.get("connected_since"))
        if connected_since and now >= connected_since:
            info["total_duration_seconds"] += int((now - connected_since).total_seconds())

        bytes_received = client.get("bytes_received", 0)
        bytes_sent = client.get("bytes_sent", 0)

        info["total_rx_mb"] += bytes_received / (1024 * 1024)
        info["total_tx_mb"] += bytes_sent / (1024 * 1024)

        info["last_seen"] = now

        info["current_session"] = {
            "connected_since": client.get("connected_since"),
            "time_online": client.get("time_online"),
            "ip": client.get("real_ip"),
            "port": client.get("port"),
            "vpn_ip": client.get("vpn_ip"),
            "vpn_ipv4": client.get("vpn_ipv4"),
            "vpn_ipv6": client.get("vpn_ipv6"),
            "bytes_received_gb": round(bytes_received / (1024 ** 3), 3),
            "bytes_sent_gb": round(bytes_sent / (1024 ** 3), 3),
        }

    clients_list: List[Dict[str, Any]] = []

    for client in clients_map.values():
        closed_sessions = client.pop("_closed_sessions", set())
        has_active_session = client.pop("_has_active_session", False)
        client["sessions"] = len(closed_sessions) + (1 if has_active_session else 0)

        total_duration = client.get("total_duration_seconds", 0)
        client["total_duration_human"] = str(timedelta(seconds=total_duration))
        client["total_rx_gb"] = round(client.get("total_rx_mb", 0.0) / 1024, 3)
        client["total_tx_gb"] = round(client.get("total_tx_mb", 0.0) / 1024, 3)

        last_seen_dt = client.get("last_seen")
        client["last_seen"] = (
            last_seen_dt.strftime("%Y-%m-%d %H:%M:%S") if isinstance(last_seen_dt, datetime) else None
        )

        client.pop("total_rx_mb", None)
        client.pop("total_tx_mb", None)

        clients_list.append(client)

    clients_list.sort(key=lambda c: c["name"].lower())
    return clients_list


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
        # Load active sessions to enrich with location data
        active_sessions = load_active_sessions(ACTIVE_SESSIONS_PATH)

        # Add location from active_sessions to each client
        for client in clients:
            common_name = client.get("common_name")
            if common_name and common_name in active_sessions:
                session = active_sessions[common_name]
                client["location"] = session.get("location", {
                    "city": None,
                    "country": None,
                    "latitude": None,
                    "longitude": None
                })
            else:
                client["location"] = {
                    "city": None,
                    "country": None,
                    "latitude": None,
                    "longitude": None
                }

        return jsonify({"clients": clients})
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("[api_clients] Error while fetching clients")
        return _json_error("Failed to fetch clients")


@app.route("/api/history")
def get_history():
    try:
        entries = _load_history_entries()
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


@app.route("/api/clients/summary")
def get_clients_summary():
    try:
        clients = _aggregate_client_stats()
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("[clients-summary] Failed to build clients summary")
        return _json_error("Failed to build clients summary")

    return jsonify({"clients": clients})


@app.route("/api/traffic-metrics")
def get_traffic_metrics():
    """
    Get historical traffic metrics for charts.

    Query parameters:
    - client: Optional client name to filter by
    - period: Time period in minutes (default: 30, options: 30, 60, 180, 360, 720)
    """
    try:
        client_name = request.args.get("client")
        period_str = request.args.get("period", "30")

        # Parse and validate period
        try:
            period_minutes = int(period_str)
        except (TypeError, ValueError):
            return _json_error("Invalid period parameter", 400, code="invalid_parameter")

        # Validate period is one of allowed values
        allowed_periods = [30, 60, 180, 360, 720]
        if period_minutes not in allowed_periods:
            return _json_error(
                f"Period must be one of {allowed_periods}",
                400,
                code="invalid_parameter"
            )

        # Get metrics
        metrics = get_metrics_for_period(
            client_name=client_name if client_name else None,
            minutes=period_minutes
        )

        return jsonify({
            "metrics": metrics,
            "period_minutes": period_minutes,
            "client": client_name
        })

    except Exception:  # pragma: no cover - defensive logging
        logger.exception("[traffic-metrics] Failed to fetch traffic metrics")
        return _json_error("Failed to fetch traffic metrics")


if __name__ == "__main__":
    app.run()
