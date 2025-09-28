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

Ensure OpenVPN logs are accessible at `/var/log/openvpn/status.log`. The application stores its
state files (history, active sessions, geolocation cache, server status) under the repository
`data/` directory, which is created automatically on first launch if it does not exist.

```bash
docker-compose up --build -d
```

---

## 🔧 Post-install Configuration

### 1. Log directory mount

Verify these volumes are properly set in `docker-compose.yml`:

```yaml
volumes:
  - /var/log/openvpn:/var/log/openvpn:rw
  - ./data:/app/data:rw
```

This allows the container to access:

- `status.log`
- `data/active_sessions.json`
- `data/client_geolocation.json`
- `data/server_status.json`
- `data/session_history.log`

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
| `OPENVPN_HISTORY_LOG` | `<project_root>/data/session_history.log` | File used to persist session history entries. |
| `OPENVPN_ACTIVE_SESSIONS` | `<project_root>/data/active_sessions.json` | JSON file storing in-progress sessions. |
| `OPENVPN_SERVER_STATUS` | `<project_root>/data/server_status.json` | Optional JSON file with aggregated server status information. |
| `OPENVPN_CLIENT_GEO_DB` | `<project_root>/data/client_geolocation.json` | Local cache of IP geolocation metadata. |

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

### Automating provisioning with `openvpn-install.sh`

If you plan to issue or revoke VPN profiles programmatically, avoid invoking the bundled
`openvpn-install.sh` directly from the Flask process. Instead, run it from a privileged backend
helper that exposes a hardened API to the web app. See [Docs/openvpn-install-integration.md](Docs/openvpn-install-integration.md)
for a step-by-step outline, including an `expect` example and security considerations.

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

