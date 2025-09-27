#routes.py
from flask import Flask, render_template, jsonify
from .config import HISTORY_LOG_PATH, SERVER_STATUS_PATH
from .parser import parse_status_log
import os
import json
from datetime import datetime

#app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'), static_folder=None)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['DEBUG'] = True


def is_valid_datetime(value):
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except:
        return False

@app.route('/')
def index():
    return render_template("index.html")

#@app.route('/api/clients')
#def api_clients():
#    clients = parse_status_log()
#    return jsonify({"clients": clients})

@app.route('/api/clients')
def api_clients():
    try:
        clients = parse_status_log()
        return jsonify({"clients": clients})
    except Exception as e:
        print(f"[api_clients] Error: {e}")
        return jsonify({"error": "Failed to fetch clients"}), 500


@app.route('/api/history')
def get_history():
    entries = []
    try:
        if os.path.exists(HISTORY_LOG_PATH):
            with open(HISTORY_LOG_PATH, "r") as f:
                for line in f:
                    parts = line.strip().split(',')[:9]
                    if len(parts) == 9 and parts[4] and parts[5] and is_valid_datetime(parts[8]):
                        entry = {
                            "timestamp": parts[0],
                            "name": parts[1],
                            "ip": parts[2],
                            "session_id": parts[3],
                            "rx": parts[4],
                            "tx": parts[5],
                            "vpn_ip": parts[6],
                            "port": parts[7],
                            "session_end": parts[8],
                            "duration": str(
                                datetime.strptime(parts[8], "%Y-%m-%d %H:%M:%S") -
                                datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                            )
                        }
                        entries.append(entry)
    except Exception as e:
        print(f"Error reading history log: {e}")
    return jsonify(entries)

@app.route('/api/server-status')
def get_server_status():
    try:
        with open(SERVER_STATUS_PATH, "r") as f:
            data = json.load(f)

        # ?? ????????? ?????? "Yes" ? ?????? ????????
        pingable = data.get("pingable")
        if isinstance(pingable, str):
            data["pingable"] = pingable.lower() == "yes"

    except Exception as e:
        print(f"[server-status] Failed to read or parse JSON: {e}")
        data = {
            "status": "Unknown",
            "uptime": "Unknown",
            "local_ip": "0.0.0.0",
            "pingable": False
        }

    try:
        clients = parse_status_log()
        total_rx = sum(c.get("bytes_received", 0) for c in clients)
        total_tx = sum(c.get("bytes_sent", 0) for c in clients)
    except Exception as e:
        print(f"[server-status] Failed to parse status log: {e}")
        clients = []
        total_rx = 0
        total_tx = 0

    data.update({
        "mode": "server",
        "clients": len(clients),
        "total_rx": round(total_rx / 1024 / 1024, 2),
        "total_tx": round(total_tx / 1024 / 1024, 2),
    })

    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)

## test
