If you find this project useful and want to support further development, you can do so via:

[![Buy Me a Coffee](https://img.shields.io/badge/☕-Buy%20Me%20a%20Coffee-yellow)](https://buymeacoffee.com/scuruci)
[![Revolut](https://img.shields.io/badge/💸-Revolut-blue)](https://revolut.me/s_curuci)

Your support helps keep the open-source projects alive and evolving

# OpenVPN Monitor

A Flask-based web dashboard for real-time monitoring of OpenVPN server activity with advanced features including session tracking, traffic analytics, geolocation mapping, and historical data visualization.

## Features

- **Real-time Client Monitoring** - Live view of connected VPN clients with connection details
- **Session History** - Complete history of all VPN sessions with detailed statistics
- **Traffic Analytics** - Real-time traffic charts with historical data (up to 24 hours)
- **Geolocation Mapping** - Automatic IP geolocation with interactive maps
- **Multiple Display Modes** - Aggregated and individual traffic views with dynamic Y-axis scaling
- **Multi-language Support** - English and Russian interface with easy language switching
- **RESTful API** - Full API access for integration with external systems
- **Docker Support** - Easy deployment with Docker Compose and Traefik integration
- **Timezone Support** - Configurable timezone for accurate session duration calculations

## Architecture

### Core Components

| Component | Purpose | Files |
|-----------|---------|-------|
| **Flask Application** | Serves web UI and REST API endpoints (`/api/clients`, `/api/history`, `/api/server-status`, `/api/clients/summary`, `/api/traffic-metrics`) | `app/routes.py`, `app/templates/index.html` |
| **Configuration Layer** | Loads timezone, log paths, and JSON file paths from environment variables; creates directories and initializes empty JSON files on first run | `app/config.py` |
| **Status Parser** | Parses OpenVPN's `status.log` (version 3 format), maintains session data, normalizes IPv4/IPv6 addresses, uses file locking (`fcntl`) to prevent race conditions, and atomically updates files | `app/parser.py` |
| **Traffic Collector** | Collects and stores traffic metrics every 10 seconds, maintains 24-hour history, calculates speeds (MB/s) | `app/traffic_collector.py` |
| **Background Logger** | Runs parser, traffic collector, and server status collector in a loop to keep data fresh | `logger.py` |
| **Internationalization** | Flask-Babel for Python/Jinja2 templates, custom API endpoint for JavaScript translations | `app/routes.py` (`/api/translations`), `translations/`, `app/static/js/i18n.js` |
| **Server Status Collector** | Collects OpenVPN server operational status (status, uptime, local/public IP, ping check) directly from within the Docker container - no cron required | `app/server_status_collector.py` |
| **Containerization** | Python 3.12 Docker image with supervisord managing both Flask web server and background logger | `Dockerfile`, `docker-compose.yml`, `supervisord.conf` |

### Data Flow

1. OpenVPN server writes to `/var/log/openvpn/status.log`
2. Background logger calls `parse_status_log()` every 10 seconds
3. Parser reads active clients and routing table, calculates session durations
4. For new clients, automatically fetches geolocation from ip-api.com (45 req/min limit)
5. Traffic collector captures current traffic metrics and calculates speeds
6. Server status collector checks `status.log` freshness and fetches public IP (runs every 60 seconds)
7. Updates `active_sessions.json`, `session_history.json`, `traffic_metrics.json`, and `server_status.json` under file lock
8. API endpoints read cached/persisted data and serve to UI

## Prerequisites

- Running OpenVPN server with status logging enabled (recommend `status-version 3`)
- Linux host with Docker 24+ and Docker Compose v2, OR Python ≥3.11 for manual setup
- Directory on host for state files (`active_sessions.json`, `session_history.json`, `server_status.json`, `traffic_metrics.json`)
- (Optional) Traefik v2 reverse proxy with external network `proxy` for publishing the dashboard
- (Optional) Internet access for server status collector and parser to determine public IP and client geolocation

## Installation

### Pre-installation Steps

1. **Configure OpenVPN**

   Ensure `/etc/openvpn/server.conf` contains:
   ```
   status /var/log/openvpn/status.log
   status-version 3
   ```

   **Set read permissions on status.log** (required for non-root container):
   ```bash
   sudo chmod 644 /var/log/openvpn/status.log
   ```

   This allows the container (running as UID 1000) to read the OpenVPN status file. The file contains only monitoring data (IP addresses, traffic stats, connection times) - no sensitive credentials.

2. **Directory Structure**

   Default installation path is `/var/www`. Navigate there and clone the repository:
   ```bash
   cd /var/www
   git clone https://github.com/farggus/openvpn-monitor.git
   cd openvpn-monitor
   ```

   For custom path (e.g., `/home/app_data/openvpn-monitor`):
   ```bash
   sudo mkdir -p /home/app_data/openvpn-monitor/data
   sudo chown -R 1000:1000 /home/app_data/openvpn-monitor
   ```

3. **Traefik (Optional)**

   If publishing via Traefik, create external network:
   ```bash
   docker network create proxy
   ```

   Prepare TLS certificates/authorization (Basic Auth) and adjust labels in `docker-compose.yml`

### Docker Compose Installation

1. **Clone Repository**
   ```bash
   cd /var/www
   git clone https://github.com/farggus/openvpn-monitor.git
   cd openvpn-monitor
   ```

2. **Prepare Data Directory and Set Permissions**

   The container runs as non-root user (UID 1000) for security:
   ```bash
   sudo mkdir -p /var/www/openvpn-monitor/data
   sudo chown -R 1000:1000 /var/www/openvpn-monitor
   ```

3. **Configure Environment Variables**

   Create `.env` file from template:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure your domain:
   ```bash
   # Required: Set your domain for Traefik routing
   OPENVPN_DOMAIN=your-domain.com

   # Optional: Server geolocation (disabled by default for security)
   # OPENVPN_SERVER_GEOLOCATION=false

   # Optional: Set local IP address manually (auto-detected from container if not set)
   # OPENVPN_LOCAL_IP=10.8.0.1
   ```

4. **Configure Additional Environment Variables (Optional)**

   Edit `docker-compose.yml` environment block if needed. Available variables:

   | Variable | Purpose | Default |
   |----------|---------|---------|
   | `OPENVPN_DOMAIN` | Domain name for Traefik routing (set in .env file) | `localhost` |
   | `OPENVPN_MONITOR_TZ` | Timezone for session duration calculations | `Europe/Bucharest` |
   | `OPENVPN_STATUS_LOG` | Path to OpenVPN status file (inside container) | `/var/log/openvpn/status.log` |
   | `OPENVPN_HISTORY_LOG` | Session history JSON | `/app/data/session_history.json` |
   | `OPENVPN_ACTIVE_SESSIONS` | Active sessions JSON | `/app/data/active_sessions.json` |
   | `OPENVPN_SERVER_STATUS` | Server status JSON | `/app/data/server_status.json` |
   | `OPENVPN_TRAFFIC_METRICS` | Traffic metrics JSON | `/app/data/traffic_metrics.json` |
   | `OPENVPN_SERVER_GEOLOCATION` | Enable server geolocation (security risk) | `false` |
   | `OPENVPN_LOCAL_IP` | Server local IP (auto-detected if not set) | (auto) |

5. **Verify Volume Mounts**

   Ensure `volumes` section includes:
   ```yaml
   - /var/log/openvpn:/var/log/openvpn:rw
   - ./data:/app/data:rw
   ```

6. **Build and Start Container**
   ```bash
   docker compose up --build -d
   ```

7. **Check Container Status**
   ```bash
   docker compose logs -f
   ```

   Look for `OpenVPN background logger started...` message and no `status.log` read errors

8. **Access UI**
   - With Traefik: `https://<your-domain>`
   - Direct port mapping: Uncomment `ports: - "5000:5000"` in docker-compose.yml and access `http://<host>:5000`

9. **Rebuild from Scratch**
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

### Manual Installation (Development)

1. **Setup Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
   export OPENVPN_HISTORY_LOG=$(pwd)/data/session_history.json
   export OPENVPN_ACTIVE_SESSIONS=$(pwd)/data/active_sessions.json
   export OPENVPN_SERVER_STATUS=$(pwd)/data/server_status.json
   export OPENVPN_TRAFFIC_METRICS=$(pwd)/data/traffic_metrics.json
   export OPENVPN_MONITOR_TZ=Europe/Bucharest
   mkdir -p data
   ```

3. **Run Services**

   Option 1 - Two terminals:
   ```bash
   # Terminal 1
   flask --app app run --host 0.0.0.0 --port 5000

   # Terminal 2
   python logger.py
   ```

   Option 2 - Supervisord:
   ```bash
   pip install supervisor
   supervisord -c supervisord.conf
   ```

4. **Verify**
   - Open browser at `http://localhost:5000`
   - Check `data/` directory for JSON files being updated

## Post-Installation Steps

1. **Verify Data Files**

   Check that data directory contains:
   - `session_history.json`
   - `active_sessions.json`
   - `server_status.json`
   - `traffic_metrics.json`

2. **Configure Authentication/HTTPS**

   When using Traefik:
   - Add middleware with Basic Auth or other authentication
   - Configure TLS certificate (Let's Encrypt or custom) for secure access

3. **Monitoring and Alerts**

   - Add `/api/server-status` health check to monitoring system
   - Configure container log collection (stdout/stderr) to centralized storage

4. **Backup**

   Include `data/` directory in regular backups to preserve session history with geolocation data

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/clients` | Current active clients including traffic and IP addresses |
| GET | `/api/history` | History of completed sessions, suitable for reporting |
| GET | `/api/server-status` | Server metadata: mode, uptime, client count, traffic |
| GET | `/api/clients/summary` | Client summary (session count, traffic, last login) |
| GET | `/api/traffic-metrics` | Traffic metrics with period filter (30m, 1h, 3h, 6h, 12h) |
| GET | `/api/translations` | UI translations for current locale (used by JavaScript frontend) |

### API Examples

```bash
# Get all active clients
curl http://localhost:5000/api/clients

# Get session history
curl http://localhost:5000/api/history

# Get server status
curl http://localhost:5000/api/server-status

# Get traffic metrics for last hour
curl http://localhost:5000/api/traffic-metrics?period=60

# Get traffic metrics for specific client
curl http://localhost:5000/api/traffic-metrics?period=30&client=user1
```

## Feature Details

### Geolocation Integration

The system automatically fetches and stores geolocation data for client IP addresses directly in session files, eliminating the need for separate geolocation databases.

**How It Works:**

1. **New Session Creation**
   - Client connects to VPN
   - Parser detects physical IP address
   - Fetches geolocation from ip-api.com (free API, 45 requests/min limit)
   - Stores data in `active_sessions.json` with `location` field

2. **Data Structure**
   ```json
   {
     "client-name": {
       "ip": "109.185.9.154",
       "vpn_ip": "10.8.0.10",
       "connected_at": "2025-10-07 07:16:06",
       "bytes_received": 12345678,
       "bytes_sent": 87654321,
       "port": "60877",
       "session_id": "uuid",
       "location": {
         "city": "Bucharest",
         "country": "Romania",
         "latitude": 44.4268,
         "longitude": 26.1025
       }
     }
   }
   ```

3. **Session History**
   - When client disconnects, session data (including location) is appended to `session_history.json`
   - No external API calls needed for historical data
   - Maps display location markers for both active and historical sessions

**API Service:**
- Provider: ip-api.com
- Rate limit: 45 requests/minute
- No API key required
- Returns: city, country, latitude, longitude

If API is unavailable or rate limit exceeded, sessions are created with null location values.

### Traffic Metrics & Historical Data

Real-time traffic monitoring with historical data storage and visualization.

**Features:**

- **Background Collection** - Metrics collected every 10 seconds (even when dashboard is closed)
- **24-Hour Storage** - Maintains data for the last 24 hours
- **Period Filters** - View data for: 30 minutes, 1 hour, 3 hours, 6 hours, 12 hours
- **Instant Loading** - Historical data loads immediately when opening charts
- **Smooth Updates** - Real-time updates without page refresh
- **Multiple Display Modes:**
  - **Aggregated View** - All clients on one chart with individual colors
  - **Individual View** - Select specific client with detailed statistics

**Data Structure:**

`traffic_metrics.json` stores:
```json
{
  "client_name": [
    {
      "timestamp": "2025-10-09T12:00:00+03:00",
      "bytes_received": 1234567,
      "bytes_sent": 234567,
      "speed_rx": 1.5,
      "speed_tx": 0.5
    }
  ]
}
```

**Statistics Displayed:**
- Current Rx/Tx speed
- Peak Rx/Tx speed for selected period
- Average speed (calculated from all data points)

**Performance:**
- File size: ~50-100 KB for 5 clients over 24 hours
- Points per client: ~8,640 (24h × 360 points/hour)
- Automatic cleanup of data older than 24 hours

## Key Implementation Details

### File Locking Pattern

The parser uses `fcntl.flock()` to prevent concurrent modifications:
- `active_sessions_lock()` prevents race conditions when reading/writing active sessions
- `history_log()` context manager locks history file during append operations
- Atomic file updates using temp files and `os.replace()`

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

### Traffic Speed Calculation

```python
speed_mb_per_sec = (current_bytes - previous_bytes) / (1024 * 1024) / time_delta_seconds
```

- Always positive (uses `max(0, ...)`)
- Precision: 6 decimal places
- Unit: MB/s

## Internationalization (i18n)

The application supports multiple languages with seamless switching between them.

### Supported Languages

- **English (en)** - Default language
- **Russian (ru)** - Full translation

### Language Selection

Users can switch languages using the dropdown selector in the top-right corner of the interface. The language preference is saved in a browser cookie and persists across sessions.

**Language Detection Priority:**
1. URL parameter: `?lang=en` or `?lang=ru`
2. Browser cookie: `lang`
3. HTTP Accept-Language header
4. Default: English

**Example:**
```
http://localhost:5000/?lang=ru  # Force Russian
http://localhost:5000/?lang=en  # Force English
```

### Architecture

**Backend (Python/Jinja2):**
- Uses **Flask-Babel** for server-side translations
- All user-facing strings wrapped in `gettext()` or `_()`
- Templates use `{{ _('text') }}` syntax
- Compiled `.mo` files loaded on application start

**Frontend (JavaScript):**
- Custom i18n module (`app/static/js/i18n.js`)
- Translations fetched from `/api/translations` endpoint
- Function `t('key')` for translating strings in JavaScript

**Translation Files:**
```
translations/
├── en/LC_MESSAGES/messages.po  # English translations (source)
├── ru/LC_MESSAGES/messages.po  # Russian translations
└── messages.pot                # Template file
```

### Adding New Translations

For developers who want to add new languages or update existing ones:

1. **For new language (e.g., German):**
   ```bash
   mkdir -p translations/de/LC_MESSAGES
   cp translations/en/LC_MESSAGES/messages.po translations/de/LC_MESSAGES/
   # Edit messages.po and translate msgstr values
   ```

2. **Update code to include new language:**
   - Add to `get_locale()` in `app/routes.py`
   - Add option to language selector in `app/templates/index.html`

3. **Compile and rebuild:**
   ```bash
   docker compose build
   docker compose up -d
   ```

For detailed localization documentation, see [I18N.md](I18N.md).

## Development

### Docker Commands

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

### Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests are located in `tests/` directory:
- `test_parser.py` - Unit tests for status log parsing logic
- `test_routes.py` - Integration tests for API endpoints

Mock `status.log` files can be created for testing different scenarios.

### Code Formatting

```bash
black .
flake8
```

Static analyzers configured via `pyproject.toml`.

### Working with Translations

When developing new features that include user-facing text:

1. **Wrap strings in Python:**
   ```python
   from flask_babel import gettext as _
   message = _("Your translatable text")
   ```

2. **Wrap strings in Jinja2 templates:**
   ```html
   <h1>{{ _('Page Title') }}</h1>
   ```

3. **Add JavaScript translations:**
   - Add key-value pair to `/api/translations` endpoint in `app/routes.py`
   - Use `t('your_key')` in JavaScript code

4. **Update translation files:**
   - Edit `translations/en/LC_MESSAGES/messages.po`
   - Edit `translations/ru/LC_MESSAGES/messages.po`

5. **Compile and test:**
   ```bash
   python compile_translations.py
   docker compose build
   docker compose up -d
   ```

See [I18N.md](I18N.md) for complete localization documentation.

## Configuration

### Adjusting Traffic Metrics Retention

Edit `app/traffic_collector.py`:
```python
# Change from 24 hours to another value
MAX_METRIC_AGE_SECONDS = 48 * 60 * 60  # 48 hours
```

### Adjusting Collection Interval

Edit `logger.py`:
```python
# Change from 10 seconds to another interval
time.sleep(5)  # 5 seconds
```

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| **Empty client table** | Run `sudo chmod 644 /var/log/openvpn/status.log` to allow container (UID 1000) read access. Also verify `docker logs openvpn-admin` shows no permission errors |
| **Permission denied errors** | Ensure data directory is owned by UID 1000: `sudo chown -R 1000:1000 ./data` and verify OpenVPN log permissions: `sudo chmod 644 /var/log/openvpn/status.log` |
| **"Unknown" server status** | Server status is collected automatically from `status.log`. Wait 60 seconds for first update. Check container logs: `docker compose logs -f` for errors. Verify status.log is accessible and being updated by OpenVPN server |
| **No client map** | Check ip-api.com availability and rate limit (45/min). Geolocation is added automatically on first client connection |
| **Timezone errors** | Verify `OPENVPN_MONITOR_TZ` is a valid IANA timezone (e.g., `Europe/Bucharest`, not `EET`) |
| **File lock timeouts** | Check for stale `.lock` files in data directory |
| **Empty charts on open** | Wait 10-20 seconds for first data points to be collected. Verify background logger is running: `docker compose logs -f` |
| **No historical traffic data** | Check `data/traffic_metrics.json` exists and has correct permissions. Restart container if needed |
| **Translations not working** | Ensure `flask-babel` is installed, check browser console for `/api/translations` errors, verify `.mo` files exist in `translations/` |
| **Language not changing** | Clear browser cookies, check `lang` cookie value, verify language selector in HTML |

## Operations and Updates

### Updating the Application

```bash
git pull
docker compose build
docker compose up -d
```

### Data Migration

When updating from older versions:
- Stop container
- Backup `data/` directory
- Remove outdated JSON files (they will be recreated automatically)
- Start container

### Important Paths

- OpenVPN status log (host): `/var/log/openvpn/status.log`
- Data directory (container): `/app/data`
- Data directory (host, default): `./data`
- Templates: `app/templates/`
- Configuration: `app/config.py`

## Security

This application implements several security best practices:

### Non-Root Container Execution

The Docker container runs as a non-root user (UID 1000) to minimize security risks:

- **User:** `appuser` (UID 1000, GID 1000)
- **Benefit:** Limits potential damage if the container is compromised
- **Implementation:** Configured in `Dockerfile` and `supervisord.conf`

**Important:** Ensure the host data directory has correct permissions:
```bash
sudo chown -R 1000:1000 /path/to/data
```

### Optional Server Geolocation

Server geolocation is **disabled by default** to prevent information disclosure:

- **Default:** Server location is NOT collected or displayed
- **Risk:** Revealing server's physical location can aid attackers
- **Enable only if necessary:** Set `OPENVPN_SERVER_GEOLOCATION=true` in environment

Client geolocation (for connected VPN users) remains enabled and is a core feature of the monitoring dashboard.

### Domain Configuration

Use environment variables instead of hardcoded values:

- **Variable:** `OPENVPN_DOMAIN` in `.env` file
- **Benefit:** Prevents accidental exposure of production domains in public repositories
- **Example:** See `.env.example` for configuration template

### Basic Authentication

The application includes built-in Traefik Basic Auth support for password protection:

**Setup:**

1. **Generate password hash:**
   ```bash
   htpasswd -nbB openvpn YourSecurePassword
   ```

2. **Add to `.env` file** (escape `$` with `$$`):
   ```bash
   # Example output: openvpn:$2y$05$abc123...
   # In .env file:
   OPENVPN_BASIC_AUTH=openvpn:$$2y$$05$$abc123...
   ```

3. **For multiple users:**
   ```bash
   OPENVPN_BASIC_AUTH=user1:$$2y$$05$$...,user2:$$2y$$05$$...
   ```

**IMPORTANT:** The `.env.example` file contains a default password (`openvpn123`) for testing purposes. **You MUST change this** before deploying to production:

```bash
cp .env.example .env
# Edit .env and replace OPENVPN_BASIC_AUTH with your own hash
```

**Security Note:** Basic Auth credentials are configured via environment variables to prevent hardcoding in `docker-compose.yml`. Never commit your `.env` file to version control.

### Container Restart Policy

Docker Compose includes `restart: unless-stopped` policy:

- Automatically restarts container on failure
- Survives host reboots
- Can be manually stopped when needed

### Recommended Additional Security Measures

1. **Enable Authentication:**
   - Use Traefik Basic Auth or OAuth middleware
   - Never expose dashboard without authentication

2. **Use HTTPS:**
   - Configure TLS certificates via Traefik
   - Redirect HTTP to HTTPS automatically

3. **Limit Network Access:**
   - Run container in isolated Docker network
   - Use firewall rules to restrict access

4. **Regular Updates:**
   - Keep base images and dependencies updated
   - Monitor security advisories for Python packages

5. **Audit Logs:**
   - Monitor container logs for suspicious activity
   - Integrate with centralized logging system

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! We appreciate bug reports, feature requests, code contributions, and documentation improvements.

Please read our [Contributing Guidelines](CONTRIBUTING.md) to get started. The guide covers:

- Setting up your development environment
- Coding standards and best practices
- Testing guidelines
- Pull request process
- How to report bugs and suggest features

For quick questions, feel free to open a GitHub issue or discussion.


## Support the project
For issues and feature requests, please use the GitHub issue tracker.

If you find this project useful and want to support further development, you can do so via:

[![Buy Me a Coffee](https://img.shields.io/badge/☕-Buy%20Me%20a%20Coffee-yellow)](https://buymeacoffee.com/scuruci)
[![Revolut](https://img.shields.io/badge/💸-Revolut-blue)](https://revolut.me/s_curuci)

Your support helps keep the open-source projects alive and evolving

