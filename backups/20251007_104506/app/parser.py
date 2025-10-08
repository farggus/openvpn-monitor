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

    with open(target_path, "a+") as logf:
        fcntl.flock(logf, fcntl.LOCK_EX)
        try:
            logf.seek(0)
            try:
                entries = json.load(logf)
            except (json.JSONDecodeError, OSError):
                entries = []

            if not isinstance(entries, list):
                entries = []

            yield entries

            logf.seek(0)
            logf.truncate()
            json.dump(entries, logf, ensure_ascii=False, indent=2)
            logf.write("\n")
            logf.flush()
            os.fsync(logf.fileno())
        finally:
            fcntl.flock(logf, fcntl.LOCK_UN)


@contextmanager
def active_sessions_lock(path: str = ACTIVE_SESSIONS_PATH):
    """Prevent concurrent modifications of the active sessions state."""

    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path)
    os.makedirs(directory, exist_ok=True)

    lock_path = f"{target_path}.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


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
    current_common_names = set()
    vpn_ip_map = {}
    new_sessions = []
    client_records = []

    try:
        with active_sessions_lock():
            active_sessions = load_active_sessions()
            now = datetime.datetime.now(LOCAL_TZ)

            with open(filepath, "r") as f:
                section = None

                for raw_line in f:
                    line = raw_line.strip()

                    if raw_line.startswith(
                        "Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since"
                    ):
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
                            vpn_ip = parts[0].strip()
                            common_name = parts[1].strip()

                            entry = vpn_ip_map.setdefault(common_name, {"ipv4": None, "ipv6": None})

                            try:
                                ip_obj = ip_address(vpn_ip)
                            except ValueError:
                                # Fallback to the previous behaviour – store the value in the
                                # first available slot so we don't lose potentially useful
                                # information even if it isn't a valid IP.
                                if entry["ipv4"] is None:
                                    entry["ipv4"] = vpn_ip
                                elif entry["ipv6"] is None:
                                    entry["ipv6"] = vpn_ip
                                continue

                            if ip_obj.version == 4:
                                entry["ipv4"] = vpn_ip
                            else:
                                entry["ipv6"] = vpn_ip
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
                                "vpn_ipv4": None,
                                "vpn_ipv6": None,
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
                vpn_ip_entry = vpn_ip_map.get(common_name, {})
                vpn_ipv4 = vpn_ip_entry.get("ipv4") if isinstance(vpn_ip_entry, dict) else None
                vpn_ipv6 = vpn_ip_entry.get("ipv6") if isinstance(vpn_ip_entry, dict) else None

                vpn_ip = vpn_ipv4 or vpn_ipv6

                record["vpn_ip"] = vpn_ip
                record["vpn_ipv4"] = vpn_ipv4
                record["vpn_ipv6"] = vpn_ipv6
                clients.append(record)

                if common_name in active_sessions:
                    active_sessions[common_name]["vpn_ip"] = vpn_ip
                    active_sessions[common_name]["vpn_ipv4"] = vpn_ipv4
                    active_sessions[common_name]["vpn_ipv6"] = vpn_ipv6

            for common_name in new_sessions:
                session = active_sessions.get(common_name)
                if not session:
                    continue

                vpn_ip_entry = vpn_ip_map.get(common_name)
                if isinstance(vpn_ip_entry, dict):
                    vpn_ipv4 = vpn_ip_entry.get("ipv4") or ""
                    vpn_ipv6 = vpn_ip_entry.get("ipv6") or ""
                else:
                    value = vpn_ip_entry or ""
                    vpn_ipv4 = value
                    vpn_ipv6 = ""
                    try:
                        if value:
                            ip_obj = ip_address(value)
                            if ip_obj.version == 6:
                                vpn_ipv4, vpn_ipv6 = "", value
                    except ValueError:
                        pass
                vpn_ip = vpn_ipv4 or vpn_ipv6 or ""
                port = session.get("port") or ""

                session["vpn_ip"] = vpn_ip or None
                session["vpn_ipv4"] = vpn_ipv4 or None
                session["vpn_ipv6"] = vpn_ipv6 or None

                with history_log() as entries:
                    entries.append(
                        {
                            "timestamp": session["connected_at"],
                            "name": common_name,
                            "ip": session.get("ip"),
                            "session_id": session["session_id"],
                            "rx": None,
                            "tx": None,
                            "vpn_ip": vpn_ip or None,
                            "vpn_ipv4": vpn_ipv4 or None,
                            "vpn_ipv6": vpn_ipv6 or None,
                            "port": port or None,
                            "session_end": None,
                        }
                    )

            disconnected = [cn for cn in list(active_sessions) if cn not in current_common_names]
            for cn in disconnected:
                session = active_sessions[cn]
                rx = round(session["bytes_received"] / (1024 * 1024), 2)
                tx = round(session["bytes_sent"] / (1024 * 1024), 2)
                disconnect_time = now.strftime("%Y-%m-%d %H:%M:%S")
                vpn_ip = session.get("vpn_ip") or ""
                port = session.get("port") or ""
                vpn_ipv4 = session.get("vpn_ipv4") or ""
                vpn_ipv6 = session.get("vpn_ipv6") or ""

                if not vpn_ipv4 and not vpn_ipv6 and vpn_ip:
                    try:
                        ip_obj = ip_address(vpn_ip)
                    except ValueError:
                        pass
                    else:
                        if ip_obj.version == 4:
                            vpn_ipv4 = vpn_ip
                        else:
                            vpn_ipv6 = vpn_ip

                with history_log() as entries:
                    entries.append(
                        {
                            "timestamp": session["connected_at"],
                            "name": cn,
                            "ip": session.get("ip"),
                            "session_id": session["session_id"],
                            "rx": rx,
                            "tx": tx,
                            "vpn_ip": vpn_ip or None,
                            "vpn_ipv4": vpn_ipv4 or None,
                            "vpn_ipv6": vpn_ipv6 or None,
                            "port": port or None,
                            "session_end": disconnect_time,
                        }
                    )

                del active_sessions[cn]

            save_active_sessions(active_sessions)
    except Exception:  # pragma: no cover - safeguard logging
        logger.exception("Error parsing status log")

    return clients
