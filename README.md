# OpenVPN Monitor

**OpenVPN Monitor** is a lightweight real-time dashboard for tracking OpenVPN server activity and client connections. Built with Flask and Docker, it features interactive charts, maps, history, and mobile-friendly UI.

---

## 🚀 Features

- Live list of connected OpenVPN clients
- Rx/Tx traffic graph per client (Chart.js)
- Interactive client map with IP geolocation (Leaflet + ipapi)
- Session history viewer with date/user filters
- Server status overview: mode, traffic, uptime, clients
- Dark/light theme toggle
- Mobile-responsive interface
- Easy Docker deployment with Traefik reverse proxy

---

## 📁 Project Structure

```
openvpn-monitor/
├── app/
│   ├── __init__.py            # Flask app init
│   ├── routes.py              # API endpoints and views
│   ├── parser.py              # Log parsing and session tracking
│   └── templates/index.html   # Frontend interface
├── logger.py                  # Background log parser (interval-based)
├── supervisord.conf           # Manages app + logger processes
├── Dockerfile                 # Docker build config
├── docker-compose.yml         # Compose + Traefik routes
├── requirements.txt           # Python dependencies
```

---

## ⚙️ Installation (Docker)

### 1. Clone the repository

```bash
git clone git@github.com:your-username/openvpn-monitor.git
cd openvpn-monitor
```

### 2. Start the container

Ensure OpenVPN logs are accessible at `/var/log/openvpn/status.log`.

```bash
docker-compose up --build -d
```

---

## 🔧 Post-install Configuration

### 1. Log directory mount

Verify this volume is properly set in `docker-compose.yml`:

```yaml
volumes:
  - /var/log/openvpn:/var/log/openvpn:rw
```

This allows the container to access:

- `status.log`
- `session_history.log`
- `active_sessions.json`
- `server_status.json`

### 2. Traefik domain setup

Edit your Traefik labels in `docker-compose.yml`:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.openvpn.rule=Host(`openvpn.example.com`)"
  - "traefik.http.routers.openvpn-secure.tls=true"
  ...
```

Replace `openvpn.example.com` with your real domain name.

### 3. DNS & SSL

Make sure:

- Your domain DNS points to the host
- Traefik is configured with TLS/SSL (e.g., Let's Encrypt)

### 4. Environment variables

You can override default log locations and timezone with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVPN_MONITOR_TZ` | `Europe/Bucharest` | Timezone used to compute session durations. |
| `OPENVPN_STATUS_LOG` | `/var/log/openvpn/status.log` | Path to the OpenVPN status log parsed for active clients. |
| `OPENVPN_HISTORY_LOG` | `/var/log/openvpn/session_history.log` | File used to persist session history entries. |
| `OPENVPN_ACTIVE_SESSIONS` | `/var/log/openvpn/active_sessions.json` | JSON file storing in-progress sessions. |
| `OPENVPN_SERVER_STATUS` | `/var/log/openvpn/server_status.json` | Optional JSON file with aggregated server status information. |

Example `docker-compose.yml` override:

```yaml
environment:
  OPENVPN_MONITOR_TZ: "Europe/Prague"
  OPENVPN_STATUS_LOG: "/data/openvpn/status.log"
```

---

## 🌐 Access the Interface

After deployment, access the web UI at:

```
https://openvpn.example.com
```

---

## 📡 API Endpoints

| Method | Endpoint            | Description                    |
|--------|---------------------|--------------------------------|
| GET    | `/api/clients`      | Current active clients         |
| GET    | `/api/history`      | Session history log            |
| GET    | `/api/server-status`| Current OpenVPN server status  |

---

## 🧪 What You Should See

- Real-time traffic graph
- Connected client list with traffic and uptime
- Geolocation map view of client IPs
- Modal session history with date & user filters

---

## 📦 Requirements

Installed automatically via Docker:

- Python 3
- Flask
- pytz
- psutil

Uses CDN libraries:

- Bootstrap 5
- Leaflet.js
- Chart.js
- jQuery

---

## ✅ Local verification

For local development outside Docker install both runtime and development dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Then run the quality checks and tests:

```bash
black --check .
flake8
pytest
```

These are the same commands executed in CI.

---

## 👤 Author

Developed by **Farggus**  
Project: **OpenVPN Monitor**  
License: **Private/Internal Use Only**

