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
- `app/server_status_collector.py` - Server status collection from within container (no cron needed)
- `logger.py` - Background daemon that runs parser, traffic collector, and server status collector
- `app/config.py` - Configuration and environment variables

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
- Environment variables: `OPENVPN_DOMAIN`, `OPENVPN_MONITOR_TZ`, `OPENVPN_STATUS_LOG`, `OPENVPN_HISTORY_LOG`, `OPENVPN_ACTIVE_SESSIONS`, `OPENVPN_SERVER_STATUS`, `OPENVPN_TRAFFIC_METRICS`, `OPENVPN_SERVER_GEOLOCATION`

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
- Simple loop that calls `parse_status_log()` every 10 seconds and `update_server_status()` every 60 seconds
- Runs alongside Flask via `supervisord`

**Server Status Collector** (`app/server_status_collector.py`)
- Python module that captures OpenVPN server operational status from within Docker container
- Determines server status by checking `status.log` freshness (updated in last 30 seconds = CONNECTED)
- Fetches public IP via external APIs (ipify.org, icanhazip.com)
- No host access or cron required - runs from `logger.py` every 60 seconds

**Containerization**
- `Dockerfile`: Python 3.12, non-root user (UID 1000), installs dependencies, copies code
- `supervisord.conf`: Runs both Flask web server and background logger as `appuser`
- `docker-compose.yml`: Mounts OpenVPN logs and data directory, includes Traefik labels, restart policy

### Data Flow

1. OpenVPN server writes to `/var/log/openvpn/status.log`
2. Background logger calls `parse_status_log()` every 10 seconds
3. Parser reads active clients and routing table, calculates session durations
4. For new clients, fetches geolocation from ip-api.com and stores in session data
5. Traffic collector captures metrics and calculates speeds
6. Server status collector checks `status.log` freshness and fetches public IP (every 60 seconds)
7. Updates `active_sessions.json`, `session_history.json`, `traffic_metrics.json`, and `server_status.json` under file lock
8. API endpoints read cached/persisted data and serve to UI

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

### Server Status Collection
- Collected every 60 seconds in background from within container
- Status determined by `status.log` freshness (< 30 seconds = CONNECTED)
- Public IP fetched via ipify.org or icanhazip.com
- Local IP from `OPENVPN_LOCAL_IP` env var or container's eth0 interface
- No cron or host access required - fully containerized solution

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
- **Unknown server status**: Wait 60 seconds for first collection. Server status determined by `status.log` freshness. Check container logs for errors and verify `status.log` is being updated by OpenVPN
- **Timezone errors**: `OPENVPN_MONITOR_TZ` must be valid IANA timezone (e.g., `Europe/Moscow`, not `MSK`)
- **Geolocation not working**: Parser fetches geolocation from ip-api.com when clients connect (45 req/min limit). Check network access and API availability
- **File lock timeouts**: If parser hangs, check for stale `.lock` files in data directory
- **Empty charts**: Wait 10-20 seconds for metrics to be collected. Check `traffic_metrics.json` exists

## Configuration Variables

All optional with sensible defaults. Set `OPENVPN_DOMAIN` in `.env` file, others can be uncommented in `docker-compose.yml`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENVPN_DOMAIN` | Domain name for Traefik routing (set in .env file) | `localhost` |
| `OPENVPN_MONITOR_TZ` | Timezone for session duration calculations | `Europe/Bucharest` |
| `OPENVPN_STATUS_LOG` | Path to OpenVPN status file (inside container) | `/var/log/openvpn/status.log` |
| `OPENVPN_HISTORY_LOG` | Session history JSON | `/app/data/session_history.json` |
| `OPENVPN_ACTIVE_SESSIONS` | Active sessions JSON | `/app/data/active_sessions.json` |
| `OPENVPN_SERVER_STATUS` | Server status JSON | `/app/data/server_status.json` |
| `OPENVPN_TRAFFIC_METRICS` | Traffic metrics JSON | `/app/data/traffic_metrics.json` |
| `OPENVPN_SERVER_GEOLOCATION` | Enable server geolocation (disabled by default for security) | `false` |
| `OPENVPN_LOCAL_IP` | Server local IP address (auto-detected from container if not set) | (auto) |

## Security Features

### Non-Root Container

The application runs as non-root user (`appuser`, UID 1000) for security:

- **Dockerfile**: Creates `appuser` group and user, sets ownership of `/app`
- **supervisord.conf**: Configures all processes to run as `appuser`
- **docker-compose.yml**: Includes `restart: unless-stopped` policy

**Important:** Host data directory must be owned by UID 1000:
```bash
sudo chown -R 1000:1000 /path/to/data
```

### Optional Server Geolocation

Server geolocation is **disabled by default** to prevent information disclosure:

- **Default behavior**: `scripts/server_status.py` does NOT fetch server location
- **Enable via**: `OPENVPN_SERVER_GEOLOCATION=true` environment variable
- **Security note**: Revealing server's physical location can aid attackers

Client geolocation (for VPN users) remains enabled as it's a core monitoring feature.

### Environment-Based Configuration

Sensitive configuration uses environment variables:

- **Domain name**: Set via `OPENVPN_DOMAIN` in `.env` file (not hardcoded)
- **.env file**: Added to `.gitignore` to prevent accidental commits
- **.env.example**: Template provided for easy setup


## Archived and Removed Files (October 2025 Cleanup)

During the project audit in October 2025, several files were archived or removed to improve maintainability.

### Archived Files (Moved to `archive/migrations/`)

The following migration scripts were successfully executed and moved to archive for historical reference:

- **`archive/migrations/migrate_close_sessions.py`**
  - **Executed:** 2025-10-13
  - **Purpose:** Closed 110 incomplete sessions in session_history.json
  - **Result:** All sessions now have `session_end` set
  - **Documentation:** See Docs/REFACTORING_SUMMARY.md

- **`archive/migrations/test_refactoring.py`**
  - **Executed:** 2025-10-13
  - **Purpose:** Validated refactoring results (no incomplete sessions, correct parser.py structure)
  - **Result:** All tests passed
  - **Documentation:** See Docs/REFACTORING_SUMMARY.md

### Removed Files (Replaced by Containerized Solution)

The following legacy files were removed as they were replaced by `app/server_status_collector.py`:

- **`scripts/server_status.sh`** (removed)
  - Legacy bash script with cron dependency
  - Contained unsafe JSON construction via shell string concatenation
  - Required host-level system utilities (dig, pgrep, curl)

- **`scripts/server_status.py`** (removed)
  - Legacy Python script with cron dependency
  - Required host-level process inspection
  - Worked only on host, not in container

- **`crontab`** (removed)
  - Cron configuration for running server_status.py every minute
  - No longer needed - replaced by `logger.py` calling `app/server_status_collector.py` every 60 seconds

### New Containerized Approach

All server status collection is now handled by **`app/server_status_collector.py`**:

- ✅ Runs inside Docker container (no host access needed)
- ✅ Called from `logger.py` every 60 seconds
- ✅ Safe JSON construction using `json.dump()`
- ✅ Determines server status by checking `status.log` freshness
- ✅ No cron required

### Removed Dependencies

- **`psutil`** removed from `requirements.txt`
  - Was not used anywhere in the codebase
  - Likely leftover from old server_status.py implementation
  - Removing it reduces Docker image size by ~500 KB

### Documentation

For complete details about the cleanup, see:
- `Docs/PROJECT_AUDIT_OCT_2025.md` - Full project audit report
- `Docs/CLEANUP_PLAN.md` - Step-by-step cleanup execution plan
- `Docs/REFACTORING_SUMMARY.md` - Session management refactoring details
