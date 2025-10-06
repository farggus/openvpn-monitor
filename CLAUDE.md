# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

OpenVPN Monitor is a Flask-based web dashboard for real-time monitoring of OpenVPN server activity. It parses OpenVPN's `status.log`, tracks connection history, aggregates client statistics, and displays data through a Bootstrap UI with session history modals and geolocation mapping.

## Architecture

### Core Components

**Flask Application** (`app/routes.py`)
- Serves web UI and REST API endpoints
- Main endpoints: `/api/clients`, `/api/history`, `/api/server-status`, `/api/clients/summary`
- Uses request-scoped caching via Flask's `g` object to avoid re-parsing status.log multiple times per request

**Configuration Layer** (`app/config.py`)
- Loads timezone, log paths, and JSON file paths from environment variables
- Creates directories and initializes empty JSON files on first run
- Environment variables: `OPENVPN_MONITOR_TZ`, `OPENVPN_STATUS_LOG`, `OPENVPN_HISTORY_LOG`, `OPENVPN_ACTIVE_SESSIONS`, `OPENVPN_SERVER_STATUS`, `OPENVPN_CLIENT_GEO_DB`

**Status Parser** (`app/parser.py`)
- Parses OpenVPN's `status.log` (expects version 3 format)
- Maintains `active_sessions.json` and appends to `session_history.json`
- Normalizes IPv4/IPv6 addresses, calculates session durations
- Uses file locking (`fcntl`) to prevent race conditions during concurrent reads/writes
- Atomically updates files using temp files and `os.replace()`

**Background Logger** (`logger.py`)
- Simple loop that calls `parse_status_log()` every 10 seconds
- Runs alongside Flask via `supervisord`

**Geolocation Database** (`app/geo_store.py`)
- Maintains JSON registry of client IPs with first/last seen timestamps
- Provides POST `/api/geo` endpoint for external geolocation enrichment
- GET `/api/geo/<ip>` retrieves location data from local database

**Server Status Script** (`scripts/server_status.sh`)
- Shell script that captures OpenVPN server operational status (PID, local/public IP, ping check)
- Should be run via cron every minute to update `server_status.json`

**Containerization**
- `Dockerfile`: Python 3.12, installs dependencies, copies code
- `supervisord.conf`: Runs both Flask web server and background logger
- `docker-compose.yml`: Mounts OpenVPN logs and data directory, includes Traefik labels

### Data Flow

1. OpenVPN server writes to `/var/log/openvpn/status.log`
2. Background logger calls `parse_status_log()` every 10 seconds
3. Parser reads active clients and routing table, calculates session durations
4. Updates `active_sessions.json` and appends to `session_history.json` under file lock
5. API endpoints read cached/persisted data and serve to UI
6. Cron script updates `server_status.json` with server metadata

## Development Commands

### Docker (Production)
```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f

# Rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Manual Setup (Development)
```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables
export OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
export OPENVPN_HISTORY_LOG=$(pwd)/data/session_history.json
export OPENVPN_ACTIVE_SESSIONS=$(pwd)/data/active_sessions.json
export OPENVPN_SERVER_STATUS=$(pwd)/data/server_status.json
export OPENVPN_CLIENT_GEO_DB=$(pwd)/data/client_geolocation.json
export OPENVPN_MONITOR_TZ=Europe/Moscow
mkdir -p data

# Run Flask and logger (option 1: two terminals)
flask --app app run --host 0.0.0.0 --port 5000
python logger.py

# Run with supervisord (option 2: single process)
pip install supervisor
supervisord -c supervisord.conf
```

### Testing
```bash
pip install -r requirements-dev.txt
pytest
```

### Code Formatting
```bash
black .
flake8
```

## Key Implementation Details

### File Locking Pattern
The parser uses `fcntl.flock()` to prevent concurrent modifications:
- `active_sessions_lock()` prevents race conditions when reading/writing active sessions
- `history_log()` context manager locks history file during append operations

### Session Tracking
- New clients get a UUID `session_id` when first detected in `status.log`
- Sessions are tracked in `active_sessions.json` with bytes received/sent
- When client disconnects, session is appended to `session_history.json` with final traffic stats
- Session duration is calculated using timezone-aware datetime objects

### IP Address Normalization
The parser handles both IPv4 and IPv6:
- `_split_real_address()` extracts IP and port from various formats (e.g., `[::1]:1234`, `192.168.1.1:1234`)
- Routing table is parsed separately to map common names to VPN IPs
- IPv4 and IPv6 are stored separately (`vpn_ipv4`, `vpn_ipv6`) but also combined into `vpn_ip`

### API Caching Strategy
Routes use `_get_cached_clients()` which stores parsed results in Flask's `g` object. This ensures:
- Single parse per request even when multiple endpoints are called
- Fresh data on each HTTP request (g is cleared after response)

## Testing Notes

- Tests are in `tests/` directory
- `test_parser.py`: Unit tests for status log parsing logic
- `test_routes.py`: Integration tests for API endpoints
- Mock `status.log` files can be created for testing different scenarios

## Important Paths

- OpenVPN status log (host): `/var/log/openvpn/status.log`
- Data directory (container): `/app/data`
- Data directory (host, default): `./data`
- Templates: `app/templates/`
- Configuration: `app/config.py`

## Common Gotchas

- **Empty client table**: Verify container can read `/var/log/openvpn/status.log` with correct permissions
- **Unknown server status**: Ensure `scripts/server_status.sh` is running via cron and writing to correct path
- **Timezone errors**: `OPENVPN_MONITOR_TZ` must be valid IANA timezone (e.g., `Europe/Moscow`, not `MSK`)
- **Geolocation not working**: Check `client_geolocation.json` is writable; external service integration required for auto-population
- **File lock timeouts**: If parser hangs, check for stale `.lock` files in data directory

## Configuration Variables (Docker Compose)

All optional with sensible defaults (uncomment in `docker-compose.yml` to customize):

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENVPN_MONITOR_TZ` | Timezone for session duration calculations | `Europe/Bucharest` |
| `OPENVPN_STATUS_LOG` | Path to OpenVPN status file (inside container) | `/var/log/openvpn/status.log` |
| `OPENVPN_HISTORY_LOG` | Session history JSON | `/app/data/session_history.json` |
| `OPENVPN_ACTIVE_SESSIONS` | Active sessions JSON | `/app/data/active_sessions.json` |
| `OPENVPN_SERVER_STATUS` | Server status JSON | `/app/data/server_status.json` |
| `OPENVPN_CLIENT_GEO_DB` | Geolocation database JSON | `/app/data/client_geolocation.json` |
