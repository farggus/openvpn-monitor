
# parser.py
import datetime
import json
import os
import uuid
import pytz

LOCAL_TZ = pytz.timezone("Europe/Bucharest")
STATUS_LOG = "/var/log/openvpn/status.log"
HISTORY_LOG = "/var/log/openvpn/session_history.log"
ACTIVE_SESSIONS_FILE = "/var/log/openvpn/active_sessions.json"

def format_duration(seconds):
    return str(datetime.timedelta(seconds=seconds))

def load_active_sessions():
    if os.path.exists(ACTIVE_SESSIONS_FILE):
        with open(ACTIVE_SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_active_sessions(sessions):
    with open(ACTIVE_SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)

def parse_status_log(filepath=STATUS_LOG):
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
                        with open(HISTORY_LOG, "a") as logf:
                            logf.write(f"{active_sessions[common_name]['connected_at']},{common_name},{real_ip},{session_id},,,,{vpn_ip},{port}\n")
                    else:
                        active_sessions[common_name]["bytes_received"] = bytes_received
                        active_sessions[common_name]["bytes_sent"] = bytes_sent

        disconnected = [cn for cn in active_sessions if cn not in current_common_names]
        for cn in disconnected:
            session = active_sessions[cn]
            rx = round(session["bytes_received"] / (1024 * 1024), 2)
            tx = round(session["bytes_sent"] / (1024 * 1024), 2)
            disconnect_time = now.strftime("%Y-%m-%d %H:%M:%S")
            with open(HISTORY_LOG, "a") as logf:
                logf.write(f"{session['connected_at']},{cn},{session['ip']},{session['session_id']},{rx},{tx},{session.get('vpn_ip')},{session.get('port')},{disconnect_time}\n")
#               logf.write(f"{session['connected_at']},{cn},{session['ip']},{session['session_id']},{rx},{tx},{session.get('vpn_ip')},{session.get('port')},{disconnect_time}\n")
            del active_sessions[cn]
# {session['connected_at']}
    except Exception as e:
        print(f"Error parsing log: {e}")

    save_active_sessions(active_sessions)
    return clients
