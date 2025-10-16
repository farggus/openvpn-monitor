# OpenVPN Monitor v1.0.0 - Release Notes

**Release Date:** October 16, 2025
**First Stable Release**

---

## Overview

We're excited to announce the first stable release of **OpenVPN Monitor** - a modern, Docker-ready web dashboard for real-time monitoring of OpenVPN server activity. Written from scratch and inspired by [furlongm/openvpn-monitor](https://github.com/furlongm/openvpn-monitor), this release represents months of development focused on creating a production-ready monitoring solution.

---

## Highlights

### Core Monitoring Features

**Real-time Client Dashboard**
- Live view of all connected VPN clients with automatic 10-second updates
- Comprehensive connection details: IP addresses, session duration, traffic statistics
- Automatic geolocation for all connected clients (city, country, coordinates)
- Interactive maps powered by Leaflet showing client locations

**Traffic Analytics**
- Real-time traffic charts with 24-hour historical data retention
- Multiple time period views: 30m, 1h, 3h, 6h, 12h, 24h
- Dual display modes: aggregated (all clients) and per-client views
- Traffic speed calculations (MB/s) with peak and average statistics
- Chart.js visualization with zoom and pan support

**Session History & Archival**
- Complete tracking of all VPN sessions with UUID-based session IDs
- Smart data management: keeps last 90 days in fast-access storage
- Automatic monthly archival with gzip compression (~10x compression ratio)
- Archive statistics API for monitoring historical data
- Persistent geolocation data in session archives

**Server Status Monitoring**
- Real-time server health monitoring (CONNECTED/DISCONNECTED status)
- Server uptime tracking and active client count
- Total traffic statistics across all connections
- Public and local IP address detection
- Fully containerized - no cron or host access required

### User Experience

**Multi-language Support**
- Full internationalization (i18n) with English and Russian languages
- Seamless language switching with browser cookie persistence
- Server-side (Flask-Babel) and client-side (custom i18n.js) translation support
- API endpoint for dynamic translation loading

**Responsive Design**
- Bootstrap-based UI optimized for desktop and mobile devices
- Real-time updates without page refresh
- Loading indicators and user feedback
- Clean, modern interface

**RESTful API**
- Full API access for external integrations
- 7 comprehensive endpoints covering all monitoring data
- Two-level caching strategy for optimal performance
- JSON responses with proper error handling

### Technical Excellence

**Docker-First Architecture**
- Single-command deployment with Docker Compose
- Two deployment modes: with Traefik (reverse proxy) and standalone
- Non-root container execution (UID 1000) for enhanced security
- Automatic restart policy for high availability

**Performance Optimization**
- Request-level caching (Flask `g` object) for efficient data reuse
- Response-level caching (Flask-Caching) with 10-second TTL
- Sub-100ms API response times under load
- Efficient file locking with atomic updates

**Data Integrity**
- File locking (`fcntl.flock()`) prevents race conditions
- Atomic file updates using temp files and `os.replace()`
- Session validation and cleanup mechanisms
- Graceful handling of corrupted data

**Security Features**
- Non-root container (runs as `appuser`, UID 1000)
- Optional Basic Authentication via Traefik
- HTTPS support with Let's Encrypt integration
- Server geolocation disabled by default to prevent location disclosure
- Environment-based configuration (no hardcoded secrets)
- `.env` file excluded from Git to prevent credential leaks

---

## What's Included

### Core Components

**Flask Application** (`app/routes.py`)
- 7 API endpoints for comprehensive monitoring
- Jinja2 templates for web UI
- Request-scoped caching for performance
- Multi-language support (Flask-Babel)

**Status Parser** (`app/parser.py`)
- Parses OpenVPN status.log (version 3 format)
- Maintains active sessions and session history
- Automatic geolocation via ip-api.com (with caching)
- IPv4 and IPv6 address normalization
- 609 lines of clean, well-structured code

**Traffic Collector** (`app/traffic_collector.py`)
- Collects metrics every 10 seconds
- 24-hour data retention with automatic cleanup
- Traffic speed calculations based on byte deltas
- File locking for concurrent access safety

**Server Status Collector** (`app/server_status_collector.py`)
- Determines server status by checking status.log freshness
- Fetches public IP via external APIs (ipify.org, icanhazip.com)
- Runs entirely within container - no host access needed
- Replaces legacy cron-based scripts

**History Manager** (`app/history_manager.py`)
- Automatic rotation of sessions older than 90 days
- Monthly compressed archives (`.json.gz` format)
- Archive statistics endpoint for monitoring
- Prevents unlimited growth of session history

**Background Logger** (`logger.py`)
- Orchestrates periodic tasks (parse, collect, rotate)
- Runs alongside Flask via supervisord
- Error handling with emergency exit after 10 consecutive failures
- Detailed logging for troubleshooting

**Configuration Layer** (`app/config.py`)
- Environment variable management
- Automatic directory and file initialization
- Timezone configuration support
- Sensible defaults for all settings

### Deployment Files

**Docker Configuration**
- `Dockerfile` - Python 3.12 Alpine-based image with non-root user
- `docker-compose.yml` - Traefik integration with HTTPS and auth
- `docker-compose.standalone.yml` - Standalone deployment on port 5000
- `supervisord.conf` - Process manager for Flask and background logger
- `.env.example` - Environment variable template

**Documentation**
- `README.md` - Comprehensive installation and usage guide (1570 lines)
- `CLAUDE.md` - Development guide for Claude Code integration
- `CONTRIBUTING.md` - Contribution guidelines and best practices
- `translations/I18N.md` - Localization guide
- `LICENSE` - MIT License

### Testing & Quality

**Test Suite**
- `tests/test_parser.py` - Status log parsing logic tests
- `tests/test_routes.py` - API endpoint integration tests
- `tests/test_traffic_collector.py` - Traffic collection tests
- `tests/test_new_features.py` - Feature validation tests

**Code Quality**
- Black code formatter configuration
- Flake8 linting setup
- Type hints for better code clarity
- Comprehensive docstrings

---

## Requirements

### Minimum System Requirements
- **RAM:** 256 MB
- **Disk:** 500 MB (including Docker image)
- **CPU:** 1 core

### Software Requirements
- **Docker:** 20+ with Docker Compose v1.29+ or v2
- **OpenVPN Server:** Running instance with status logging enabled
- **Docker Permissions:** User must be in `docker` group
- **Status Log Permissions:** Readable by UID 1000

### Optional Requirements
- **Traefik v2:** For reverse proxy and HTTPS (only for `docker-compose.yml`)
- **Internet Access:** For geolocation and public IP detection
- **Domain Name:** For production deployment with HTTPS

---

## Installation

### Quick Start (5 minutes)

```bash
# 1. Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# 2. Clone repository
git clone https://github.com/farggus/openvpn-monitor.git /var/www/openvpn-monitor
cd /var/www/openvpn-monitor

# 3. Set permissions
sudo mkdir -p data
sudo chown -R 1000:1000 .

# 4. Configure environment
cp .env.example .env
nano .env  # Set OPENVPN_MONITOR_TZ and change default password

# 5. Start container
docker compose up --build -d  # With Traefik
# OR
docker compose -f docker-compose.standalone.yml up --build -d  # Standalone

# 6. Access dashboard
# Traefik: https://your-domain.com
# Standalone: http://your-server-ip:5000
```

See `README.md` for detailed installation instructions including OpenVPN configuration, permissions setup, and troubleshooting.

---

## Configuration

### Essential Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVPN_DOMAIN` | `localhost` | Domain name for Traefik routing |
| `OPENVPN_MONITOR_TZ` | `Europe/Bucharest` | IANA timezone for session calculations |
| `OPENVPN_STATUS_LOG` | `/var/log/openvpn/status.log` | Path to OpenVPN status file |

### Security Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVPN_BASIC_AUTH` | `openvpn:openvpn123` | Traefik Basic Auth credentials (change in production!) |
| `OPENVPN_SERVER_GEOLOCATION` | `false` | Enable server geolocation (disabled for security) |

### Data File Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVPN_HISTORY_LOG` | `/app/data/session_history.json` | Session history storage |
| `OPENVPN_ACTIVE_SESSIONS` | `/app/data/active_sessions.json` | Active sessions storage |
| `OPENVPN_SERVER_STATUS` | `/app/data/server_status.json` | Server status storage |
| `OPENVPN_TRAFFIC_METRICS` | `/app/data/traffic_metrics.json` | Traffic metrics storage |

See `README.md` Configuration Reference section for complete variable list.

---

## API Reference

### Available Endpoints

| Endpoint | Method | Cache | Description |
|----------|--------|-------|-------------|
| `/api/clients` | GET | 10s | Active clients with traffic and geolocation |
| `/api/history` | GET | None | Session history (last 90 days) |
| `/api/history/archive-stats` | GET | None | Monthly archive statistics |
| `/api/server-status` | GET | 10s | Server status and total traffic |
| `/api/clients/summary` | GET | 10s | Per-client aggregated statistics |
| `/api/traffic-metrics` | GET | 10s | Historical traffic data (supports `period` and `client` params) |
| `/api/translations` | GET | None | UI translations for current locale |

### Example API Call

```bash
# Get active clients
curl http://localhost:5000/api/clients

# Get traffic metrics for last hour
curl "http://localhost:5000/api/traffic-metrics?period=60"

# Get archive statistics
curl http://localhost:5000/api/history/archive-stats
```

See `README.md` API Reference section for detailed examples and response formats.

---

## Architecture

### System Overview

```
User Browser (Web UI)
    ↓ HTTP/HTTPS
Traefik (Optional - Reverse Proxy + Auth + TLS)
    ↓
Docker Container (UID 1000)
    ├── Supervisord
    │   ├── Flask Web App (port 5000)
    │   │   └── API Endpoints + UI
    │   └── Background Logger
    │       ├── Status Parser (10s interval)
    │       ├── Traffic Collector (10s interval)
    │       ├── Server Status Collector (60s interval)
    │       └── History Rotation (24h interval)
    ├── Data Files (JSON)
    │   ├── active_sessions.json
    │   ├── session_history.json (90 days)
    │   ├── traffic_metrics.json (24 hours)
    │   ├── server_status.json
    │   └── history_archive/*.json.gz
    └── Read-only mount
        ↓
OpenVPN Server (Host)
    └── /var/log/openvpn/status.log
```

### Data Flow

1. OpenVPN writes to `status.log` every ~10 seconds
2. Background logger triggers parser, collector, and status checks
3. Parser reads client list, calculates durations, fetches geolocation
4. Traffic collector captures metrics and calculates speeds
5. Server status collector checks log freshness and fetches IPs
6. History manager archives sessions older than 90 days
7. All data written atomically with file locking
8. API endpoints serve cached/persisted data
9. Web UI updates via AJAX without page refresh

---

## Known Limitations

### Current Release

1. **Single-file State Storage**
   - Not suitable for horizontal scaling (multiple replicas)
   - Consider PostgreSQL migration for large installations

2. **Geolocation Rate Limit**
   - ip-api.com free tier: 45 requests/minute
   - High-traffic deployments may hit rate limits

3. **24-hour Traffic Retention**
   - Traffic metrics older than 24 hours are automatically deleted
   - Extend by modifying `MAX_METRIC_AGE_SECONDS` in `traffic_collector.py`

4. **90-day History Retention**
   - Sessions older than 90 days moved to compressed archives
   - Extend by modifying `MAX_HISTORY_DAYS` in `history_manager.py`

---

## Upgrade Path

### From Development Versions

If you've been running development versions (commits before this release):

```bash
# 1. Backup data
sudo cp -r data data.backup.$(date +%Y%m%d)

# 2. Pull latest code
git pull origin main

# 3. Update .env if needed
cp .env .env.backup
# Compare .env.example for new variables

# 4. Rebuild container
docker compose down
docker compose build --no-cache
docker compose up -d

# 5. Verify logs
docker compose logs -f
```

### Breaking Changes

None - This is the first stable release.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Empty client table | Verify container can read `/var/log/openvpn/status.log` with `chmod 644` |
| Permission denied (Docker) | Add user to docker group: `sudo usermod -aG docker $USER` |
| Wrong session times | Set correct `OPENVPN_MONITOR_TZ` in `.env` (use IANA timezone) |
| Unknown server status | Wait 60 seconds for first collection |
| No geolocation | Check internet access and ip-api.com availability |
| Container won't start | Check port 5000 availability or change port in `docker-compose.yml` |

See `README.md` Troubleshooting section for detailed debugging steps.

---

## Security Notes

### Important Security Considerations

1. **Change Default Password**
   - `.env.example` contains test password `openvpn123`
   - Generate secure password: `htpasswd -nbB openvpn YourSecurePassword`
   - Escape `$` as `$$` in `.env` file

2. **Server Geolocation Disabled**
   - `OPENVPN_SERVER_GEOLOCATION=false` by default
   - Prevents exposing server's physical location
   - Only enable if absolutely necessary

3. **Non-Root Container**
   - Container runs as `appuser` (UID 1000)
   - Limits damage if container is compromised
   - Data directory must be owned by UID 1000

4. **HTTPS Recommended**
   - Use Traefik mode for automatic Let's Encrypt certificates
   - Standalone mode has no HTTPS - add nginx reverse proxy

5. **Environment Security**
   - `.env` file excluded from Git
   - Never commit secrets to repository
   - Use environment variables for sensitive data

---

## Contributing

We welcome contributions! Please read `CONTRIBUTING.md` for:
- Setting up development environment
- Coding standards (Black, Flake8)
- Testing requirements
- Pull request process
- Reporting bugs and suggesting features

Quick development setup:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest

# Format code
black .
flake8
```

---

## Credits

### Inspiration

This project was inspired by [furlongm/openvpn-monitor](https://github.com/furlongm/openvpn-monitor) but written from scratch with a modern tech stack and Docker-first architecture.

### Technologies Used

- **Backend:** Python 3.12, Flask, Flask-Babel
- **Frontend:** Bootstrap 5, Chart.js, Leaflet
- **Containerization:** Docker, Docker Compose, supervisord
- **Reverse Proxy:** Traefik v2 (optional)
- **Data Storage:** JSON files with file locking
- **Geolocation:** ip-api.com

---

## Support

### Getting Help

- **Issues:** [GitHub Issue Tracker](https://github.com/farggus/openvpn-monitor/issues)
- **Documentation:** See `README.md`, `CLAUDE.md`, and `I18N.md`
- **Discussions:** GitHub Discussions for questions and ideas

### Supporting Development

If you find this project useful, consider supporting continued development:

[![Buy Me a Coffee](https://img.shields.io/badge/☕-Buy%20Me%20a%20Coffee-yellow)](https://buymeacoffee.com/scuruci)
[![Revolut](https://img.shields.io/badge/💸-Revolut-blue)](https://revolut.me/s_curuci)

---

## License

MIT License - see `LICENSE` file for details.

---

## What's Next?

### Planned for v1.1.0

- GitHub Actions CI/CD for automated testing
- Healthcheck endpoint for Docker
- Rate limiting for API endpoints
- Enhanced input validation with marshmallow
- PostgreSQL backend option for large deployments

### Future Roadmap

- Prometheus metrics exporter
- Email/Slack notifications for server status changes
- User authentication and role-based access control
- Historical session search and filtering
- WebSocket support for real-time updates
- Additional languages (German, French, Spanish)

---

**Thank you for using OpenVPN Monitor v1.0.0!**

For the latest updates, visit: https://github.com/farggus/openvpn-monitor

---

## Changelog

### v1.0.0 (October 16, 2025)

**Core Features**
- Real-time client monitoring with 10-second updates
- Traffic analytics with 24-hour historical data
- Session history with automatic monthly archival
- Server status monitoring (containerized solution)
- Multi-language support (English, Russian)
- Interactive geolocation maps (Leaflet)
- RESTful API with 7 comprehensive endpoints

**Architecture**
- Docker-first deployment with two modes (Traefik/Standalone)
- Non-root container execution (UID 1000)
- Two-level caching strategy for performance
- File locking with atomic updates for data integrity
- Supervisord process management

**Security**
- Optional Basic Authentication via Traefik
- HTTPS support with Let's Encrypt
- Server geolocation disabled by default
- Environment-based configuration
- No hardcoded secrets

**Documentation**
- 1570-line comprehensive README
- Development guide (CLAUDE.md)
- Contribution guidelines (CONTRIBUTING.md)
- Internationalization guide (I18N.md)
- MIT License

**Testing**
- Unit tests for parser, routes, and traffic collector
- Integration tests for API endpoints
- Code formatting with Black
- Linting with Flake8

**Total Lines of Code:** ~2073 lines (excluding tests and documentation)
**API Endpoints:** 7
**Supported Languages:** 2
**Production Dependencies:** 5 packages
