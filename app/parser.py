
# parser.py
import datetime
import json
import os
import tempfile
import uuid
from contextlib import contextmanager

import fcntl
from .config import (
    ACTIVE_SESSIONS_PATH,
    HISTORY_LOG_PATH,
    LOCAL_TZ,
    STATUS_LOG_PATH,
)

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

def parse_status_log(filepath=STATUS_LOG_PATH):
    clients = []
    active_sessions = load_active_sessions()
    current_common_names = set()
    vpn_ip_map = {}

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
#Moved here
        now = datetime.datetime.now(LOCAL_TZ)
        routing_section = False
        for line in lines:
            if line.startswith("ROUTING TABLE"):
                routing_section = True
                continue
            if routing_section:
                if line.strip() == "" or line.startswith("GLOBAL STATS"):
                    break
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    vpn_ip = parts[0]
                    common_name = parts[1]
                    vpn_ip_map[common_name] = vpn_ip

        client_section = False
        for line in lines:
            if line.startswith("Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since"):
                client_section = True
                continue
            if client_section:
                if line.strip() == "" or line.startswith("ROUTING TABLE"):
                    break
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    common_name = parts[0]
# ??????????? ?????????? ????????
                    real_address = parts[1]
                    if real_address.count(':') > 1:
                        real_ip = real_address  # IPv6, ???????? ??? ?????
                        port = None
                    else:
                        real_ip, port = real_address.rsplit(":", 1) if ":" in real_address else (real_address, None)
                    bytes_received = int(parts[2])
                    bytes_sent = int(parts[3])
                    connected_since = parts[4]
                    naive_dt = datetime.datetime.strptime(connected_since, "%Y-%m-%d %H:%M:%S")
                    connected_dt = LOCAL_TZ.localize(naive_dt)
#
#                    now = datetime.datetime.now(LOCAL_TZ)
                    time_online = format_duration(int((now - connected_dt).total_seconds()))
                    vpn_ip = vpn_ip_map.get(common_name)

                    clients.append({
                        'common_name': common_name,
                        'vpn_ip': vpn_ip,
                        'real_ip': real_ip,
                        'port': port,
                        'bytes_received': bytes_received,
                        'bytes_sent': bytes_sent,
                        'connected_since': connected_since,
                        'time_online': time_online
                    })
                    current_common_names.add(common_name)

                    if common_name not in active_sessions:
                        session_id = str(uuid.uuid4())
                        active_sessions[common_name] = {
                            "ip": real_ip,
                            "vpn_ip": vpn_ip,
                            "connected_at": connected_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "bytes_received": bytes_received,
                            "bytes_sent": bytes_sent,
                            "port": port,
                            "session_id": session_id
                        }
                        with history_log() as logf:
                            logf.write(
                                f"{active_sessions[common_name]['connected_at']},{common_name},{real_ip},{session_id},,,,{vpn_ip},{port}\n"
                            )
                    else:
                        active_sessions[common_name]["bytes_received"] = bytes_received
                        active_sessions[common_name]["bytes_sent"] = bytes_sent

        disconnected = [cn for cn in active_sessions if cn not in current_common_names]
        for cn in disconnected:
            session = active_sessions[cn]
            rx = round(session["bytes_received"] / (1024 * 1024), 2)
            tx = round(session["bytes_sent"] / (1024 * 1024), 2)
            disconnect_time = now.strftime("%Y-%m-%d %H:%M:%S")
            with history_log() as logf:
                logf.write(
                    f"{session['connected_at']},{cn},{session['ip']},{session['session_id']},{rx},{tx},{session.get('vpn_ip')},{session.get('port')},{disconnect_time}\n"
                )
#               logf.write(f"{session['connected_at']},{cn},{session['ip']},{session['session_id']},{rx},{tx},{session.get('vpn_ip')},{session.get('port')},{disconnect_time}\n")
            del active_sessions[cn]
# {session['connected_at']}
    except Exception as e:
        print(f"Error parsing log: {e}")

    save_active_sessions(active_sessions)
    return clients
