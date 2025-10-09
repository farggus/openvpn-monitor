# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For comprehensive documentation including installation, features, and usage, see [README.md](README.md).

## Quick Reference

**Project**: OpenVPN Monitor - Flask-based web dashboard for real-time monitoring of OpenVPN server activity

**Tech Stack**: Python 3.12, Flask, Bootstrap UI, Chart.js, Leaflet maps, Docker, supervisord

**Key Files**:
- `app/routes.py` - Flask application and API endpoints
- `app/parser.py` - OpenVPN status.log parser with session tracking
- `app/traffic_collector.py` - Traffic metrics collection and storage
- `logger.py` - Background daemon that runs parser and collector every 10 seconds
- `app/config.py` - Configuration and environment variables
- `scripts/server_status.sh` - Server status collection (run via cron)

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
export OPENVPN_TRAFFIC_METRICS=$(pwd)/data/traffic_metrics.json
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

## Architecture Overview

### Core Components

**Flask Application** (`app/routes.py`)
- Serves web UI and REST API endpoints
- Main endpoints: `/api/clients`, `/api/history`, `/api/server-status`, `/api/clients/summary`, `/api/traffic-metrics`
- Uses request-scoped caching via Flask's `g` object to avoid re-parsing status.log multiple times per request

**Configuration Layer** (`app/config.py`)
- Loads timezone, log paths, and JSON file paths from environment variables
- Creates directories and initializes empty JSON files on first run
- Environment variables: `OPENVPN_MONITOR_TZ`, `OPENVPN_STATUS_LOG`, `OPENVPN_HISTORY_LOG`, `OPENVPN_ACTIVE_SESSIONS`, `OPENVPN_SERVER_STATUS`, `OPENVPN_TRAFFIC_METRICS`

**Status Parser** (`app/parser.py`)
- Parses OpenVPN's `status.log` (expects version 3 format)
- Maintains `active_sessions.json` and appends to `session_history.json`
- Normalizes IPv4/IPv6 addresses, calculates session durations
- Fetches geolocation for new clients from ip-api.com (45 req/min limit)
- Uses file locking (`fcntl`) to prevent race conditions during concurrent reads/writes
- Atomically updates files using temp files and `os.replace()`

**Traffic Collector** (`app/traffic_collector.py`)
- Collects traffic metrics every 10 seconds
- Maintains `traffic_metrics.json` with 24-hour historical data
- Calculates traffic speeds (MB/s) based on byte deltas
- Uses file locking and atomic updates like the parser
- Automatically cleans up data older than 24 hours

**Background Logger** (`logger.py`)
- Simple loop that calls `parse_status_log()` and `collect_traffic_metrics()` every 10 seconds
- Runs alongside Flask via `supervisord`

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
4. For new clients, fetches geolocation from ip-api.com and stores in session data
5. Traffic collector captures metrics and calculates speeds
6. Updates `active_sessions.json`, `session_history.json`, and `traffic_metrics.json` under file lock
7. API endpoints read cached/persisted data and serve to UI
8. Cron script updates `server_status.json` with server metadata

## Key Implementation Details

### File Locking Pattern
The parser and traffic collector use `fcntl.flock()` to prevent concurrent modifications:
- `active_sessions_lock()` prevents race conditions when reading/writing active sessions
- `history_log()` context manager locks history file during append operations
- `traffic_metrics_lock()` protects traffic metrics file
- All use atomic updates via temp files and `os.replace()`

### Session Tracking
- New clients get a UUID `session_id` when first detected in `status.log`
- Sessions are tracked in `active_sessions.json` with bytes received/sent and geolocation
- When client disconnects, session is appended to `session_history.json` with final traffic stats
- Session duration is calculated using timezone-aware datetime objects

### Geolocation Integration
- Automatically fetched when new client connects via ip-api.com
- Stored directly in `active_sessions.json` and `session_history.json` (no separate DB)
- Includes: city, country, latitude, longitude
- Gracefully handles API failures (stores null values)

### Traffic Metrics
- Collected every 10 seconds in background
- Stores: timestamp, bytes_received, bytes_sent, speed_rx, speed_tx
- 24-hour retention with automatic cleanup
- Supports period filtering: 30m, 1h, 3h, 6h, 12h

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
- Static files: `app/static/`
- Configuration: `app/config.py`

## Common Development Tasks

### Adding a New API Endpoint
1. Add route function in `app/routes.py`
2. Use `_get_cached_clients()` if you need parsed client data
3. Return JSON response
4. Add tests in `tests/test_routes.py`

### Modifying Status Parser
1. Edit `app/parser.py`
2. Maintain backwards compatibility with existing JSON structure
3. Use file locking for any file operations
4. Add unit tests in `tests/test_parser.py`

### Adding New Configuration
1. Add to `app/config.py`
2. Add environment variable to `docker-compose.yml`
3. Document in README.md
4. Provide sensible default value

### Debugging
- Check logs: `docker compose logs -f`
- Verify data files: `ls -lh data/`
- Test parser directly: `python -c "from app.parser import parse_status_log; print(parse_status_log())"`
- Check file locks: `lsof data/*.lock`

## Common Gotchas

- **Empty client table**: Verify container can read `/var/log/openvpn/status.log` with correct permissions
- **Unknown server status**: Ensure `scripts/server_status.sh` is running via cron and writing to correct path
- **Timezone errors**: `OPENVPN_MONITOR_TZ` must be valid IANA timezone (e.g., `Europe/Moscow`, not `MSK`)
- **Geolocation not working**: Parser fetches geolocation from ip-api.com when clients connect (45 req/min limit). Check network access and API availability
- **File lock timeouts**: If parser hangs, check for stale `.lock` files in data directory
- **Empty charts**: Wait 10-20 seconds for metrics to be collected. Check `traffic_metrics.json` exists

## Configuration Variables

All optional with sensible defaults (uncomment in `docker-compose.yml` to customize):

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENVPN_MONITOR_TZ` | Timezone for session duration calculations | `Europe/Bucharest` |
| `OPENVPN_STATUS_LOG` | Path to OpenVPN status file (inside container) | `/var/log/openvpn/status.log` |
| `OPENVPN_HISTORY_LOG` | Session history JSON | `/app/data/session_history.json` |
| `OPENVPN_ACTIVE_SESSIONS` | Active sessions JSON | `/app/data/active_sessions.json` |
| `OPENVPN_SERVER_STATUS` | Server status JSON | `/app/data/server_status.json` |
| `OPENVPN_TRAFFIC_METRICS` | Traffic metrics JSON | `/app/data/traffic_metrics.json` |
