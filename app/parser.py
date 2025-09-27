
# parser.py
import datetime
import json
import logging
import os
import tempfile
import uuid
from contextlib import contextmanager
from ipaddress import ip_address

import fcntl
from .config import (
    ACTIVE_SESSIONS_PATH,
    HISTORY_LOG_PATH,
    LOCAL_TZ,
    STATUS_LOG_PATH,
)


logger = logging.getLogger(__name__)

def format_duration(seconds):
    return str(datetime.timedelta(seconds=seconds))

def validate_active_sessions(data):
    if not isinstance(data, dict):
        return {}

    required_fields = {"ip", "vpn_ip", "connected_at", "bytes_received", "bytes_sent", "session_id"}
    validated = {}

    for common_name, session in data.items():
        if not isinstance(common_name, str) or not isinstance(session, dict):
            continue

        if not required_fields.issubset(session.keys()):
            continue

        try:
            bytes_received = int(session["bytes_received"])
            bytes_sent = int(session["bytes_sent"])
        except (TypeError, ValueError):
            continue

        validated[common_name] = {
            **session,
            "bytes_received": bytes_received,
            "bytes_sent": bytes_sent,
        }

    return validated


def load_active_sessions(path: str = ACTIVE_SESSIONS_PATH):
    target_path = os.path.abspath(path)

    if os.path.exists(target_path):
        try:
            with open(target_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

        return validate_active_sessions(data)
    return {}


def save_active_sessions(sessions, path: str = ACTIVE_SESSIONS_PATH):
    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", dir=directory, delete=False) as tmp_file:
        json.dump(sessions, tmp_file)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())

    os.replace(tmp_file.name, target_path)


@contextmanager
def history_log(path: str = HISTORY_LOG_PATH):
    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    with open(target_path, "a") as logf:
        fcntl.flock(logf, fcntl.LOCK_EX)
        try:
            yield logf
        finally:
            logf.flush()
            os.fsync(logf.fileno())
            fcntl.flock(logf, fcntl.LOCK_UN)

def _split_real_address(address: str):
    if not address:
        return "", ""

    value = address.strip()

    if value.startswith("["):
        if "]:" in value:
            ip_part, port_part = value.split("]:", 1)
            return ip_part.lstrip("["), port_part
        return value.strip("[]"), ""

    try:
        ip_address(value)
        return value, ""
    except ValueError:
        if ":" in value:
            ip_part, port_part = value.rsplit(":", 1)
            if port_part.isdigit():
                try:
                    ip_address(ip_part)
                    return ip_part, port_part
                except ValueError:
                    pass
        return value, ""


def parse_status_log(filepath=STATUS_LOG_PATH):
    clients = []
    active_sessions = load_active_sessions()
    current_common_names = set()
    vpn_ip_map = {}
    new_sessions = []
    client_records = []
    now = datetime.datetime.now(LOCAL_TZ)

    try:
        with open(filepath, "r") as f:
            section = None

            for raw_line in f:
                line = raw_line.strip()

                if raw_line.startswith("Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since"):
                    section = "clients"
                    continue

                if raw_line.startswith("ROUTING TABLE"):
                    section = "routing"
                    continue

                if raw_line.startswith("GLOBAL STATS"):
                    section = None
                    continue

                if not line:
                    if section in {"clients", "routing"}:
                        section = None
                    continue

                if section == "routing":
                    parts = line.split(",")
                    if len(parts) >= 2:
                        vpn_ip = parts[0]
                        common_name = parts[1]
                        vpn_ip_map[common_name] = vpn_ip
                    continue

                if section == "clients":
                    parts = line.split(",")
                    if len(parts) < 5:
                        continue

                    common_name = parts[0]
                    real_ip, port = _split_real_address(parts[1])
                    bytes_received = int(parts[2])
                    bytes_sent = int(parts[3])
                    connected_since = parts[4]

                    naive_dt = datetime.datetime.strptime(connected_since, "%Y-%m-%d %H:%M:%S")
                    connected_dt = LOCAL_TZ.localize(naive_dt)
                    time_online = format_duration(int((now - connected_dt).total_seconds()))

                    client_records.append(
                        {
                            "common_name": common_name,
                            "real_ip": real_ip,
                            "port": port,
                            "bytes_received": bytes_received,
                            "bytes_sent": bytes_sent,
                            "connected_since": connected_since,
                            "time_online": time_online,
                        }
                    )

                    current_common_names.add(common_name)

                    if common_name not in active_sessions:
                        session_id = str(uuid.uuid4())
                        active_sessions[common_name] = {
                            "ip": real_ip,
                            "vpn_ip": None,
                            "connected_at": connected_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "bytes_received": bytes_received,
                            "bytes_sent": bytes_sent,
                            "port": port,
                            "session_id": session_id,
                        }
                        new_sessions.append(common_name)
                    else:
                        active_sessions[common_name]["bytes_received"] = bytes_received
                        active_sessions[common_name]["bytes_sent"] = bytes_sent
                        active_sessions[common_name]["ip"] = real_ip
                        active_sessions[common_name]["port"] = port

        for record in client_records:
            common_name = record["common_name"]
            vpn_ip = vpn_ip_map.get(common_name)
            record["vpn_ip"] = vpn_ip
            clients.append(record)

            if common_name in active_sessions:
                active_sessions[common_name]["vpn_ip"] = vpn_ip

        for common_name in new_sessions:
            session = active_sessions.get(common_name)
            if not session:
                continue

            vpn_ip = vpn_ip_map.get(common_name) or ""
            port = session.get("port") or ""

            session["vpn_ip"] = vpn_ip or None

            with history_log() as logf:
                logf.write(
                    f"{session['connected_at']},{common_name},{session['ip']},{session['session_id']},,,,{vpn_ip},{port}\n"
                )

        disconnected = [cn for cn in list(active_sessions) if cn not in current_common_names]
        for cn in disconnected:
            session = active_sessions[cn]
            rx = round(session["bytes_received"] / (1024 * 1024), 2)
            tx = round(session["bytes_sent"] / (1024 * 1024), 2)
            disconnect_time = now.strftime("%Y-%m-%d %H:%M:%S")
            vpn_ip = session.get("vpn_ip") or ""
            port = session.get("port") or ""

            with history_log() as logf:
                logf.write(
                    f"{session['connected_at']},{cn},{session['ip']},{session['session_id']},{rx},{tx},{vpn_ip},{port},{disconnect_time}\n"
                )

            del active_sessions[cn]
    except Exception:  # pragma: no cover - safeguard logging
        logger.exception("Error parsing status log")

    save_active_sessions(active_sessions)
    return clients
