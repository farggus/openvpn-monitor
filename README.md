# OpenVPN Monitor

A modern web dashboard for real-time monitoring of OpenVPN server activity. Track active connections, analyze traffic patterns, view session history with geolocation, and visualize traffic metrics — all through an intuitive web interface.

[![Buy Me a Coffee](https://img.shields.io/badge/☕-Buy%20Me%20a%20Coffee-yellow)](https://buymeacoffee.com/scuruci)
[![Revolut](https://img.shields.io/badge/💸-Revolut-blue)](https://revolut.me/s_curuci)

---

## Features

### Core Monitoring
- **Real-time Client Dashboard** - Live view of connected VPN clients with connection details
- **Traffic Analytics** - Real-time traffic charts with 24-hour historical data and multiple time periods (30m, 1h, 3h, 6h, 12h)
- **Session History** - Complete history of all VPN sessions with automatic archival (keeps last 90 days, archives older data monthly)
- **Server Status** - Server health monitoring with uptime, connection status, and public IP detection

### Geolocation & Mapping
- **Automatic Geolocation** - IP geolocation for all connected clients via ip-api.com
- **Interactive Maps** - Leaflet-based maps showing client locations in real-time
- **Historical Location Data** - Preserved geolocation in session archives

### Data Management
- **Smart History Archival** - Automatic rotation of old sessions to compressed monthly archives (`.json.gz`)
- **24-Hour Traffic Retention** - Traffic metrics collected every 10 seconds with automatic cleanup
- **Persistent Storage** - All data stored in JSON files with atomic updates and file locking

### User Experience
- **Multi-language Support** - English and Russian interface with easy language switching
- **Multiple Display Modes** - Aggregated and per-client traffic views with dynamic scaling
- **Responsive Design** - Bootstrap-based UI optimized for desktop and mobile
- **RESTful API** - Full API access for integration with external systems

### Technical Features
- **Docker Ready** - Single-command deployment with Docker Compose
- **Non-root Container** - Runs as unprivileged user (UID 1000) for security
- **API Caching** - Two-level caching strategy (request-level + response-level) for optimal performance
- **Timezone Support** - Configurable timezone for accurate session duration calculations
- **Traefik Integration** - Built-in labels for reverse proxy and HTTPS setup

---

## Quick Start

Get OpenVPN Monitor running in under 5 minutes:

```bash
# 1. Clone repository
cd /var/www
git clone https://github.com/farggus/openvpn-monitor.git
cd openvpn-monitor

# 2. Set permissions
sudo mkdir -p data
sudo chown -R 1000:1000 .

# 3. Configure environment
cp .env.example .env
nano .env  # Set OPENVPN_DOMAIN and change default password

# 4. Start container
docker compose up --build -d

# 5. Check logs
docker compose logs -f
```

Access dashboard at `https://your-domain.com` (with Traefik) or `http://localhost:5000` (direct port).

---

## Prerequisites

Before installing, ensure you have:

### Required
- **OpenVPN Server** - Running instance with status logging enabled
- **Docker & Docker Compose** - Docker 24+ and Compose v2
- **Status Log Permissions** - Readable by UID 1000 (see Pre-installation Steps)

### Optional
- **Traefik v2** - For reverse proxy and HTTPS (recommended)
- **Internet Access** - For geolocation (ip-api.com) and public IP detection
- **Domain Name** - For production deployment with HTTPS

### Minimum System Requirements
- **RAM:** 256 MB
- **Disk:** 500 MB (including Docker image)
- **CPU:** 1 core

---

## Installation

### Pre-installation Steps

#### 1. Configure OpenVPN Status Logging

Edit your OpenVPN server configuration (`/etc/openvpn/server.conf`):

```conf
status /var/log/openvpn/status.log
status-version 3
```

Restart OpenVPN server:
```bash
sudo systemctl restart openvpn@server
```

#### 2. Set Status Log Permissions

The container runs as non-root user (UID 1000) and needs read access to `status.log`:

```bash
sudo chmod 644 /var/log/openvpn/status.log
```

**Security Note:** The status log contains only monitoring data (IP addresses, traffic stats, connection times) — no credentials or sensitive keys.

#### 3. Create Traefik Network (Optional)

If using Traefik for reverse proxy:

```bash
docker network create proxy
```

---

### Docker Compose Installation (Recommended)

#### Step 1: Clone Repository

Choose your installation directory:

```bash
# Default location: /var/www
cd /var/www
git clone https://github.com/farggus/openvpn-monitor.git
cd openvpn-monitor

# Alternative location (adjust paths accordingly)
# cd /home/app_data && git clone ...
```

#### Step 2: Set Directory Permissions

Container runs as UID 1000 for security:

```bash
sudo mkdir -p data
sudo chown -R 1000:1000 /var/www/openvpn-monitor
```

For custom paths:
```bash
sudo chown -R 1000:1000 /path/to/your/openvpn-monitor
```

#### Step 3: Configure Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

**Edit `.env` file** (minimum required configuration):

```bash
# Required: Your domain name
OPENVPN_DOMAIN=vpn-monitor.example.com

# Required: Change default Basic Auth password
# Generate with: htpasswd -nbB openvpn YourSecurePassword
# Remember to escape $ as $$ in .env file
OPENVPN_BASIC_AUTH=openvpn:$$2y$$05$$your_hashed_password_here
```

**Important:** The `.env.example` contains a default password (`openvpn123`) for testing. **You MUST change this before production deployment.**

<details>
<summary><b>Optional Environment Variables (click to expand)</b></summary>

Most settings have sensible defaults. Override only if needed:

```bash
# Timezone (default: Europe/Bucharest)
OPENVPN_MONITOR_TZ=America/New_York

# Server local IP (auto-detected if not set)
OPENVPN_LOCAL_IP=10.8.0.1

# Server geolocation (disabled by default for security)
OPENVPN_SERVER_GEOLOCATION=false

# File paths (usually don't need to change)
OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
OPENVPN_HISTORY_LOG=/app/data/session_history.json
OPENVPN_ACTIVE_SESSIONS=/app/data/active_sessions.json
OPENVPN_SERVER_STATUS=/app/data/server_status.json
OPENVPN_TRAFFIC_METRICS=/app/data/traffic_metrics.json
```

See [Configuration Reference](#configuration-reference) for full details.
</details>

#### Step 4: Verify Docker Compose Configuration

Check `docker-compose.yml` volume mounts:

```yaml
volumes:
  - /var/log/openvpn:/var/log/openvpn:rw  # OpenVPN status.log location
  - ./data:/app/data:rw                    # Data directory
```

**Adjust `/var/log/openvpn` path** if your OpenVPN logs are in a different location.

#### Step 5: Choose Deployment Mode

##### Option A: With Traefik (Recommended for Production)

Default `docker-compose.yml` includes Traefik labels. Ensure:
- Traefik is running
- Network `proxy` exists
- DNS points to your server

Start container:
```bash
docker compose up --build -d
```

Access at: `https://vpn-monitor.example.com`

##### Option B: Direct Port Access (Development/Testing)

Uncomment `ports` section in `docker-compose.yml`:

```yaml
ports:
  - "5000:5000"
```

Start container:
```bash
docker compose up --build -d
```

Access at: `http://your-server-ip:5000`

#### Step 6: Verify Installation

Check container status:
```bash
docker compose logs -f
```

Look for:
- ✅ `OpenVPN background logger started...`
- ✅ `Traffic collector initialized...`
- ✅ No permission errors on `status.log`

Check data files:
```bash
ls -lh data/
```

Should contain:
- `active_sessions.json`
- `session_history.json`
- `server_status.json`
- `traffic_metrics.json`

#### Step 7: First Login

1. Open dashboard URL
2. Enter Basic Auth credentials (username: `openvpn`, password from `.env`)
3. Wait 10-20 seconds for initial data collection
4. Client table should populate with active VPN connections

---

### Manual Installation (Development)

For development without Docker:

#### Step 1: Setup Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 2: Set Environment Variables

```bash
export OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
export OPENVPN_HISTORY_LOG=$(pwd)/data/session_history.json
export OPENVPN_ACTIVE_SESSIONS=$(pwd)/data/active_sessions.json
export OPENVPN_SERVER_STATUS=$(pwd)/data/server_status.json
export OPENVPN_TRAFFIC_METRICS=$(pwd)/data/traffic_metrics.json
export OPENVPN_MONITOR_TZ=Europe/Bucharest
mkdir -p data
```

#### Step 3: Run Services

**Option 1 - Two Terminals:**
```bash
# Terminal 1: Flask web server
flask --app app run --host 0.0.0.0 --port 5000

# Terminal 2: Background logger
python logger.py
```

**Option 2 - Supervisord:**
```bash
pip install supervisor
supervisord -c supervisord.conf
```

#### Step 4: Access Dashboard

Open browser at `http://localhost:5000`

---

## Configuration Reference

### Environment Variables

All variables are optional with sensible defaults:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| **`OPENVPN_DOMAIN`** | Domain name for Traefik routing | `localhost` | `vpn.example.com` |
| **`OPENVPN_BASIC_AUTH`** | Traefik Basic Auth credentials | `openvpn:openvpn123` | `user:$$2y$$05$$...` |
| **`OPENVPN_MONITOR_TZ`** | Timezone for session calculations | `Europe/Bucharest` | `America/New_York` |
| `OPENVPN_STATUS_LOG` | OpenVPN status file path | `/var/log/openvpn/status.log` | Custom path |
| `OPENVPN_HISTORY_LOG` | Session history JSON file | `/app/data/session_history.json` | Custom path |
| `OPENVPN_ACTIVE_SESSIONS` | Active sessions JSON file | `/app/data/active_sessions.json` | Custom path |
| `OPENVPN_SERVER_STATUS` | Server status JSON file | `/app/data/server_status.json` | Custom path |
| `OPENVPN_TRAFFIC_METRICS` | Traffic metrics JSON file | `/app/data/traffic_metrics.json` | Custom path |
| `OPENVPN_SERVER_GEOLOCATION` | Enable server location tracking | `false` | `true` (not recommended) |
| `OPENVPN_LOCAL_IP` | Server local IP address | Auto-detected | `10.8.0.1` |

### Setting Basic Authentication

Generate secure password hash:

```bash
htpasswd -nbB openvpn YourSecurePassword
```

Output example: `openvpn:$2y$05$abc123...`

**Add to `.env` file** (escape `$` as `$$`):
```bash
OPENVPN_BASIC_AUTH=openvpn:$$2y$$05$$abc123...
```

For multiple users:
```bash
OPENVPN_BASIC_AUTH=user1:$$2y$$05$$...,user2:$$2y$$05$$...
```

### Timezone Configuration

Use IANA timezone names:

```bash
# Valid examples
OPENVPN_MONITOR_TZ=Europe/Bucharest
OPENVPN_MONITOR_TZ=America/New_York
OPENVPN_MONITOR_TZ=Asia/Tokyo

# Invalid (will cause errors)
OPENVPN_MONITOR_TZ=EET  # Use Europe/Bucharest instead
OPENVPN_MONITOR_TZ=UTC-5  # Use America/New_York instead
```

[Full list of IANA timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

---

## Features Deep Dive

### Real-time Client Monitoring

Dashboard displays all active VPN connections with:

- **Client Information:** Common name, real IP address, VPN IP address
- **Connection Details:** Connected since, session duration, port number
- **Traffic Statistics:** Bytes received/sent, current speed (MB/s)
- **Geolocation:** City, country, coordinates (fetched automatically on first connection)
- **Session ID:** UUID for tracking across disconnections

**Update Frequency:** Every 10 seconds (background logger)

**Data Source:** OpenVPN `status.log` (version 3 format)

### Session History & Archival

Complete tracking of all VPN sessions with smart data management:

#### Active Session Tracking
- New clients get UUID `session_id` when first detected
- Sessions tracked in `active_sessions.json` with real-time traffic updates
- Geolocation fetched automatically from ip-api.com (45 requests/min limit)

#### Disconnection Handling
- When client disconnects, session appended to `session_history.json`
- Final traffic statistics and total session duration calculated
- Geolocation data preserved for historical analysis

#### Automatic Archival
- **Retention Policy:** Last 90 days in main file for fast API access
- **Monthly Archives:** Older sessions compressed to `data/history_archive/session_history_YYYY-MM.json.gz`
- **Compression Ratio:** ~10x (e.g., 5 MB → 500 KB)
- **Automatic Cleanup:** Runs once every 24 hours via background logger
- **No Duplicates:** Idempotent process safe to run multiple times

#### Archive API
```bash
# Get archive statistics
curl http://localhost:5000/api/history/archive-stats

# Response example
{
  "total_archives": 3,
  "archives": [
    {"month": "2025-09", "count": 1523, "size_mb": 0.42},
    {"month": "2025-08", "count": 2156, "size_mb": 0.58},
    {"month": "2025-07", "count": 1891, "size_mb": 0.51}
  ]
}
```

**Configuration:**
- Archive age: `MAX_HISTORY_DAYS = 90` in `app/history_manager.py`
- Archive location: `data/history_archive/`

### Traffic Analytics

Real-time traffic monitoring with historical data visualization:

#### Collection
- **Frequency:** Every 10 seconds (background collection)
- **Retention:** 24 hours of historical data
- **Storage:** `traffic_metrics.json` (~50-100 KB for 5 clients)
- **Automatic Cleanup:** Data older than 24 hours removed automatically

#### Metrics Collected
- Timestamp (ISO 8601 with timezone)
- Bytes received (cumulative)
- Bytes sent (cumulative)
- RX speed (MB/s)
- TX speed (MB/s)

#### Display Modes
1. **Aggregated View** - All clients on one chart with individual colors
2. **Individual View** - Single client with detailed statistics

#### Time Periods
- 30 minutes
- 1 hour
- 3 hours
- 6 hours
- 12 hours
- 24 hours (full retention)

#### Statistics Shown
- Current RX/TX speed
- Peak RX/TX speed (for selected period)
- Average speed (calculated from all data points in period)

#### Speed Calculation
```python
speed_mb_per_sec = (current_bytes - previous_bytes) / (1024 * 1024) / time_delta_seconds
```

**Features:**
- Instant loading (no delay when opening charts)
- Smooth real-time updates without page refresh
- Dynamic Y-axis scaling based on traffic patterns
- Chart.js visualization with zoom and pan support

### Geolocation & Mapping

Automatic IP geolocation for connected clients:

#### How It Works
1. New client connects to VPN
2. Parser detects physical IP address
3. API request to ip-api.com for geolocation
4. Data stored in session JSON with coordinates

#### Data Collected
- City
- Country
- Latitude
- Longitude
- Country code

#### API Service
- **Provider:** ip-api.com (free tier)
- **Rate Limit:** 45 requests per minute
- **No API Key Required**
- **Fallback:** Sessions created with null location if API unavailable

#### Map Display
- **Library:** Leaflet with OpenStreetMap tiles
- **Markers:** Show all active client locations
- **Popups:** Display client name and connection details
- **Clustering:** Groups nearby markers automatically

#### Data Structure Example
```json
{
  "client-name": {
    "ip": "109.185.9.154",
    "vpn_ip": "10.8.0.10",
    "location": {
      "city": "Bucharest",
      "country": "Romania",
      "latitude": 44.4268,
      "longitude": 26.1025
    }
  }
}
```

**Server Geolocation:** Disabled by default for security (prevents exposing server location to attackers). Enable with `OPENVPN_SERVER_GEOLOCATION=true` only if necessary.

### Multi-language Support (i18n)

Seamless language switching with persistent preference:

#### Supported Languages
- **English (en)** - Default
- **Russian (ru)** - Full translation

#### Language Selection
- Dropdown selector in top-right corner
- Preference saved in browser cookie
- Persists across sessions

#### Detection Priority
1. URL parameter: `?lang=en` or `?lang=ru`
2. Browser cookie: `lang`
3. HTTP Accept-Language header
4. Default: English

#### Force Language
```
https://vpn-monitor.example.com/?lang=ru  # Force Russian
https://vpn-monitor.example.com/?lang=en  # Force English
```

#### Technical Implementation
- **Backend:** Flask-Babel for server-side translations
- **Frontend:** Custom i18n module (`app/static/js/i18n.js`)
- **API Endpoint:** `/api/translations` provides translations to JavaScript
- **Translation Files:** `translations/{lang}/LC_MESSAGES/messages.po`

For adding new languages, see [I18N.md](I18N.md).

### Server Status Monitoring

Automatic collection of OpenVPN server operational status:

#### Metrics Collected
- **Status:** CONNECTED / DISCONNECTED (based on `status.log` freshness)
- **Uptime:** Server running time
- **Client Count:** Number of active connections
- **Traffic Totals:** Total bytes received/sent across all clients
- **Public IP:** Fetched from ipify.org or icanhazip.com
- **Local IP:** Auto-detected from container's eth0 interface (or manual via `OPENVPN_LOCAL_IP`)
- **Ping Check:** Connectivity test

#### Collection Method
- **Frequency:** Every 60 seconds (via `logger.py`)
- **Status Determination:** `status.log` modified in last 30 seconds = CONNECTED
- **Fully Containerized:** No host access or cron required
- **File:** `app/server_status_collector.py`

#### API Response
```json
{
  "status": "CONNECTED",
  "uptime": "5 days, 3 hours",
  "clients_connected": 12,
  "total_bytes_received": 5368709120,
  "total_bytes_sent": 1073741824,
  "public_ip": "203.0.113.42",
  "local_ip": "10.8.0.1"
}
```

---

## API Reference

### Endpoints

| Method | URL | Description | Cache TTL |
|--------|-----|-------------|-----------|
| GET | `/api/clients` | Active clients with traffic and geolocation | 10s |
| GET | `/api/history` | Completed sessions (last 90 days) | None |
| GET | `/api/history/archive-stats` | Archive statistics (monthly summaries) | None |
| GET | `/api/server-status` | Server status and total traffic | 10s |
| GET | `/api/clients/summary` | Per-client aggregated statistics | 10s |
| GET | `/api/traffic-metrics` | Historical traffic data with period filter | 10s |
| GET | `/api/translations` | UI translations for current locale | None |

### Examples

#### Get Active Clients
```bash
curl http://localhost:5000/api/clients
```

Response:
```json
{
  "client1": {
    "ip": "109.185.9.154",
    "vpn_ip": "10.8.0.10",
    "connected_at": "2025-10-15 12:30:45",
    "bytes_received": 12345678,
    "bytes_sent": 87654321,
    "location": {
      "city": "Bucharest",
      "country": "Romania",
      "latitude": 44.4268,
      "longitude": 26.1025
    }
  }
}
```

#### Get Session History
```bash
curl http://localhost:5000/api/history
```

Returns array of completed sessions (last 90 days).

#### Get Archive Statistics
```bash
curl http://localhost:5000/api/history/archive-stats
```

#### Get Server Status
```bash
curl http://localhost:5000/api/server-status
```

#### Get Traffic Metrics
```bash
# Last hour
curl http://localhost:5000/api/traffic-metrics?period=60

# Last 30 minutes for specific client
curl "http://localhost:5000/api/traffic-metrics?period=30&client=client1"

# Period values: 30 (30m), 60 (1h), 180 (3h), 360 (6h), 720 (12h)
```

#### Get Translations
```bash
curl http://localhost:5000/api/translations?lang=ru
```

### API Caching Strategy

Two-level caching for optimal performance:

#### 1. Request-Level Caching (Flask `g` object)
- Single parse per HTTP request
- Shared across multiple endpoint calls within same request
- Fresh data on each HTTP request (cleared after response)
- Function: `_get_cached_clients()` in `app/routes.py`

#### 2. Response-Level Caching (Flask-Caching)
- In-memory SimpleCache with 10-second TTL
- Matches data update frequency (logger runs every 10 seconds)
- Cached endpoints: `/api/clients`, `/api/server-status`, `/api/clients/summary`, `/api/traffic-metrics`
- Benefits: Reduced disk I/O, lower CPU usage, faster response times

**Result:** Sub-100ms API response times even under heavy load.

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                         │
│                  (React-like SPA interface)                 │
└────────────┬────────────────────────────────────────────────┘
             │ HTTP/HTTPS
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Traefik (Optional)                       │
│              Reverse Proxy + Basic Auth + TLS               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                         │
│                  (runs as UID 1000)                         │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Supervisord Process Manager              │ │
│  │                                                       │ │
│  │  ┌─────────────────┐      ┌─────────────────────┐   │ │
│  │  │  Flask Web App  │      │  Background Logger  │   │ │
│  │  │   (port 5000)   │      │   (logger.py)       │   │ │
│  │  │                 │      │                     │   │ │
│  │  │ - Routes        │      │ - Parser (10s)      │   │ │
│  │  │ - API Endpoints │      │ - Traffic (10s)     │   │ │
│  │  │ - Templates     │      │ - Server Status(60s)│   │ │
│  │  │ - Caching       │      │ - History Rotate(24h)│  │ │
│  │  └─────────────────┘      └─────────────────────┘   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    Data Files                         │ │
│  │  - active_sessions.json                               │ │
│  │  - session_history.json (last 90 days)                │ │
│  │  - traffic_metrics.json (24 hours)                    │ │
│  │  - server_status.json                                 │ │
│  │  - history_archive/*.json.gz (monthly archives)       │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────────┘
             │ Read-only mount
             ▼
┌─────────────────────────────────────────────────────────────┐
│               OpenVPN Server (Host System)                  │
│                /var/log/openvpn/status.log                  │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **Flask Application** | `app/routes.py`, `app/templates/` | Serves web UI and REST API endpoints |
| **Configuration Layer** | `app/config.py` | Loads environment variables, initializes directories |
| **Status Parser** | `app/parser.py` | Parses `status.log`, maintains sessions, fetches geolocation |
| **Traffic Collector** | `app/traffic_collector.py` | Collects traffic metrics every 10 seconds |
| **History Manager** | `app/history_manager.py` | Rotates old sessions to monthly compressed archives |
| **Server Status Collector** | `app/server_status_collector.py` | Monitors server health and connectivity |
| **Background Logger** | `logger.py` | Orchestrates periodic tasks (parse, collect, rotate) |
| **i18n System** | `app/routes.py`, `translations/`, `app/static/js/i18n.js` | Multi-language support (Flask-Babel + custom JS) |

### Data Flow

```
1. OpenVPN writes to status.log (every ~10s)
2. Background logger triggers parse_status_log() (every 10s)
3. Parser reads client list and routing table
4. New clients: fetch geolocation from ip-api.com
5. Traffic collector captures current metrics and calculates speeds
6. Server status collector checks status.log freshness (every 60s)
7. History manager archives old sessions (every 24h)
8. All data written atomically with file locking:
   - active_sessions.json
   - session_history.json
   - traffic_metrics.json
   - server_status.json
9. API endpoints read cached/persisted data
10. Web UI fetches data via AJAX and updates charts/tables
```

### File Locking & Atomic Updates

All JSON files use safe concurrent access:

- **File Locking:** `fcntl.flock()` prevents race conditions
- **Context Managers:** `active_sessions_lock()`, `history_log()`, `traffic_metrics_lock()`
- **Atomic Updates:** Write to temp file → `os.replace()` → original file
- **Lock Files:** `.lock` files in data directory

This ensures data integrity even with concurrent reads/writes.

### Session Tracking

- **New Connection:** Assign UUID `session_id`, store in `active_sessions.json`
- **Active Session:** Update bytes_received/sent every 10 seconds
- **Disconnection:** Append final session data to `session_history.json`
- **Duration Calculation:** Timezone-aware datetime objects
- **Geolocation:** Fetched once on connection, stored permanently

### IP Address Handling

Parser supports both IPv4 and IPv6:

- **Function:** `_split_real_address()` extracts IP and port
- **Formats:** `192.168.1.1:1234`, `[::1]:1234`, `[2001:db8::1]:1234`
- **Routing Table:** Parsed separately to map common names to VPN IPs
- **Storage:** `vpn_ipv4`, `vpn_ipv6`, and combined `vpn_ip` fields

---

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/farggus/openvpn-monitor.git
cd openvpn-monitor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
export OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
export OPENVPN_HISTORY_LOG=$(pwd)/data/session_history.json
export OPENVPN_ACTIVE_SESSIONS=$(pwd)/data/active_sessions.json
export OPENVPN_SERVER_STATUS=$(pwd)/data/server_status.json
export OPENVPN_TRAFFIC_METRICS=$(pwd)/data/traffic_metrics.json
export OPENVPN_MONITOR_TZ=Europe/Bucharest
mkdir -p data
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_parser.py

# Run with verbose output
pytest -v
```

Test files:
- `tests/test_parser.py` - Status log parsing logic
- `tests/test_routes.py` - API endpoint integration tests

### Code Formatting

```bash
# Format code
black .

# Check linting
flake8

# Type checking (if using mypy)
mypy app/
```

Configuration in `pyproject.toml`.

### Working with Translations

#### Add New Translatable String

**Python:**
```python
from flask_babel import gettext as _
message = _("Your translatable text")
```

**Jinja2 Templates:**
```html
<h1>{{ _('Page Title') }}</h1>
```

**JavaScript:**
```javascript
// 1. Add to /api/translations endpoint in app/routes.py
@app.route("/api/translations")
def translations():
    return jsonify({
        "your_key": _("Your translatable text")
    })

// 2. Use in JavaScript
t('your_key')  // Returns translated string
```

#### Update Translation Files

```bash
# 1. Extract new strings to messages.pot
pybabel extract -F babel.cfg -o translations/messages.pot .

# 2. Update existing .po files
pybabel update -i translations/messages.pot -d translations

# 3. Edit translations/en/LC_MESSAGES/messages.po
# 4. Edit translations/ru/LC_MESSAGES/messages.po

# 5. Compile translations
python compile_translations.py

# 6. Rebuild container
docker compose build
docker compose up -d
```

See [I18N.md](I18N.md) for detailed localization guide.

### Docker Development Workflow

```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f

# Rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up -d

# Access container shell
docker compose exec openvpn-monitor bash

# Restart single service (after code change)
docker compose restart openvpn-monitor
```

### Common Development Tasks

#### Adding New API Endpoint

1. Add route function in `app/routes.py`:
```python
@app.route("/api/your-endpoint")
def your_endpoint():
    data = _get_cached_clients()  # Use cached data
    # Process data
    return jsonify(result)
```

2. Add tests in `tests/test_routes.py`
3. Update API documentation in README.md

#### Modifying Status Parser

1. Edit `app/parser.py`
2. Maintain backwards compatibility with JSON structure
3. Use file locking for any file operations
4. Add unit tests in `tests/test_parser.py`
5. Test with sample `status.log` files

#### Changing Data Retention

**Traffic Metrics (default: 24 hours):**
```python
# app/traffic_collector.py
MAX_METRIC_AGE_SECONDS = 48 * 60 * 60  # 48 hours
```

**Session History (default: 90 days):**
```python
# app/history_manager.py
MAX_HISTORY_DAYS = 180  # 180 days
```

#### Adjusting Collection Intervals

```python
# logger.py
while True:
    parse_status_log()
    collect_traffic_metrics()
    time.sleep(5)  # Change from 10s to 5s
```

---

## Troubleshooting

### Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| **Empty client table** | Container can't read `status.log` | `sudo chmod 644 /var/log/openvpn/status.log` |
| **Permission denied on data files** | Data directory not owned by UID 1000 | `sudo chown -R 1000:1000 ./data` |
| **"Unknown" server status** | Status collector not yet run | Wait 60 seconds for first collection |
| **No geolocation on map** | ip-api.com unavailable or rate limited | Check internet access, wait for rate limit reset |
| **Timezone errors** | Invalid timezone format | Use IANA names: `Europe/Bucharest`, not `EET` |
| **File lock timeouts** | Stale lock files | Remove `.lock` files in data directory |
| **Empty traffic charts** | Not enough data collected yet | Wait 10-20 seconds for initial data points |
| **No historical traffic** | `traffic_metrics.json` missing | Check file permissions and container logs |
| **Language not switching** | Browser cookie issue | Clear cookies, check browser console for errors |
| **Can't login (Basic Auth)** | Wrong password or escaped incorrectly | Regenerate hash, ensure `$$` in `.env` file |
| **Container won't start** | Port 5000 already in use | Change port in `docker-compose.yml` or stop conflicting service |

### Debugging Steps

#### Check Container Logs
```bash
docker compose logs -f openvpn-monitor
```

Look for:
- ✅ `OpenVPN background logger started...`
- ✅ `Traffic collector initialized...`
- ❌ `Permission denied: /var/log/openvpn/status.log`
- ❌ `Failed to write active_sessions.json`

#### Verify Data Files
```bash
ls -lh data/
```

Expected output:
```
-rw-r--r-- 1 1000 1000  15K Oct 15 12:30 active_sessions.json
-rw-r--r-- 1 1000 1000 500K Oct 15 12:30 session_history.json
-rw-r--r-- 1 1000 1000  80K Oct 15 12:30 traffic_metrics.json
-rw-r--r-- 1 1000 1000 2.5K Oct 15 12:30 server_status.json
```

All files should be owned by UID 1000.

#### Test Parser Directly
```bash
docker compose exec openvpn-monitor python -c "from app.parser import parse_status_log; print(parse_status_log())"
```

Should output current client data without errors.

#### Check Status Log
```bash
sudo ls -lh /var/log/openvpn/status.log
sudo tail /var/log/openvpn/status.log
```

Verify:
- File exists and is readable by UID 1000 (permissions: `644`)
- File is being updated (check timestamp)
- Contains `status-version 3` format

#### Verify Network Connectivity
```bash
# Test geolocation API
curl http://ip-api.com/json/8.8.8.8

# Test public IP detection
curl https://api.ipify.org
```

#### Check File Locks
```bash
# Inside container
docker compose exec openvpn-monitor ls -lh data/*.lock

# If stale locks exist
docker compose exec openvpn-monitor rm data/*.lock
docker compose restart openvpn-monitor
```

### Getting Help

If you're still stuck:

1. **Check existing issues:** [GitHub Issues](https://github.com/farggus/openvpn-monitor/issues)
2. **Create new issue:** Include:
   - Container logs (`docker compose logs`)
   - Environment configuration (redact sensitive values)
   - OpenVPN status.log sample (first 20 lines)
   - Steps to reproduce

---

## Operations & Updates

### Updating Application

```bash
# Stop container
docker compose down

# Backup data directory
sudo cp -r data data.backup.$(date +%Y%m%d)

# Pull latest code
git pull

# Rebuild and start
docker compose build --no-cache
docker compose up -d

# Check logs
docker compose logs -f
```

### Backing Up Data

Include these files/directories in regular backups:

```bash
# Essential data files
data/active_sessions.json
data/session_history.json
data/traffic_metrics.json
data/server_status.json

# Archived sessions (if keeping long-term history)
data/history_archive/*.json.gz

# Configuration
.env
docker-compose.yml
```

Backup script example:
```bash
#!/bin/bash
BACKUP_DIR="/backup/openvpn-monitor/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cp -r data/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"
```

### Monitoring Health

Add to monitoring system (Prometheus, Nagios, etc.):

```bash
# Check server status endpoint
curl -s http://localhost:5000/api/server-status | jq .status

# Expected: "CONNECTED"
```

Health check script:
```bash
#!/bin/bash
STATUS=$(curl -s http://localhost:5000/api/server-status | jq -r .status)
if [ "$STATUS" != "CONNECTED" ]; then
    echo "OpenVPN Monitor: Server status is $STATUS"
    exit 1
fi
```

### Log Rotation

Container logs to stdout/stderr. Configure Docker log rotation:

```yaml
# docker-compose.yml
services:
  openvpn-monitor:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Scaling Considerations

For high-traffic deployments:

- **Multiple Replicas:** Not supported (single-file state storage)
- **High Availability:** Use Docker Swarm or Kubernetes with shared volume
- **Database Backend:** Consider migrating from JSON to PostgreSQL for large installations
- **Cache Layer:** Redis for distributed caching (requires code modification)

---

## Security

### Non-Root Container

Container runs as unprivileged user for security:

- **User:** `appuser` (UID 1000, GID 1000)
- **Benefit:** Limits damage if container is compromised
- **Implementation:** `Dockerfile` and `supervisord.conf`

**Requirement:** Host data directory must be owned by UID 1000:
```bash
sudo chown -R 1000:1000 /path/to/data
```

### Basic Authentication

Built-in Traefik Basic Auth support:

**Generate password:**
```bash
htpasswd -nbB openvpn YourSecurePassword
```

**Add to `.env` (escape `$` as `$$`):**
```bash
OPENVPN_BASIC_AUTH=openvpn:$$2y$$05$$abc123...
```

**⚠️ IMPORTANT:** Change default password (`openvpn123` in `.env.example`) before production deployment.

### HTTPS Setup

Use Traefik for automatic HTTPS:

```yaml
# docker-compose.yml labels
- "traefik.http.routers.openvpn-monitor.tls=true"
- "traefik.http.routers.openvpn-monitor.tls.certresolver=letsencrypt"
```

Traefik handles Let's Encrypt certificates automatically.

### Server Geolocation

**Disabled by default** to prevent exposing server location:

- **Default:** Server location NOT collected
- **Risk:** Revealing physical location aids attackers
- **Enable:** Only if necessary with `OPENVPN_SERVER_GEOLOCATION=true`

Client geolocation (VPN users) remains enabled.

### Environment Security

- **`.env` file:** Added to `.gitignore`, never commit to Git
- **Secrets:** Use Docker secrets or environment variables
- **Traefik labels:** Domain and auth configured via environment

### Container Restart Policy

```yaml
restart: unless-stopped
```

- Auto-restarts on failure
- Survives host reboots
- Manual stop possible

### Recommended Practices

1. **Enable Authentication:** Never expose without auth
2. **Use HTTPS:** Always use TLS in production
3. **Limit Network Access:** Docker network isolation + firewall rules
4. **Regular Updates:** Keep base images and dependencies updated
5. **Audit Logs:** Monitor container logs for suspicious activity
6. **Read-Only Mounts:** OpenVPN log mounted read-only where possible

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up development environment
- Coding standards and best practices
- Testing requirements
- Pull request process
- Reporting bugs and suggesting features

For quick questions, open a GitHub issue or discussion.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Support

### Getting Help

- **Issues:** [GitHub Issue Tracker](https://github.com/farggus/openvpn-monitor/issues)
- **Documentation:** [I18N.md](I18N.md), [CONTRIBUTING.md](CONTRIBUTING.md)
- **Discussions:** GitHub Discussions for questions and ideas

### Supporting Development

If you find this project useful, consider supporting continued development:

[![Buy Me a Coffee](https://img.shields.io/badge/☕-Buy%20Me%20a%20Coffee-yellow)](https://buymeacoffee.com/scuruci)
[![Revolut](https://img.shields.io/badge/💸-Revolut-blue)](https://revolut.me/s_curuci)

Your support helps keep open-source projects alive and evolving!

---

**OpenVPN Monitor** - Modern web dashboard for OpenVPN server monitoring
