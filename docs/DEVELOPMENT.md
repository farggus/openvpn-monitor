# Development Guide

This guide provides detailed instructions for developers working on OpenVPN Monitor.

## Table of Contents

- [Setting Up Development Environment](#setting-up-development-environment)
- [Architecture Overview](#architecture-overview)
- [Working with Docker](#working-with-docker)
- [Running Tests](#running-tests)
- [Code Formatting](#code-formatting)
- [Working with Translations](#working-with-translations)
- [Common Development Tasks](#common-development-tasks)
- [Data Flow](#data-flow)
- [Key Implementation Details](#key-implementation-details)
- [Debugging](#debugging)

---

## Setting Up Development Environment

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (for containerized development)
- Git

### Local Setup (Without Docker)

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

# Create data directory
mkdir -p data
```

### Running Services

**Option 1: Two Terminals**
```bash
# Terminal 1: Flask web server
flask --app app run --host 0.0.0.0 --port 5000

# Terminal 2: Background logger
python logger.py
```

**Option 2: Supervisord**
```bash
pip install supervisor
supervisord -c supervisord.conf

# Check status
supervisorctl status

# Stop services
supervisorctl stop all
```

---

## Architecture Overview

### Core Components

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **Flask Application** | `app/routes.py` | Serves web UI and REST API endpoints |
| **Configuration Layer** | `app/config.py` | Loads environment variables, initializes directories |
| **Status Parser** | `app/parser.py` | Parses `status.log`, maintains sessions, fetches geolocation |
| **Traffic Collector** | `app/traffic_collector.py` | Collects traffic metrics every 10 seconds |
| **History Manager** | `app/history_manager.py` | Rotates old sessions to monthly compressed archives |
| **Server Status Collector** | `app/server_status_collector.py` | Monitors server health and connectivity |
| **Background Logger** | `logger.py` | Orchestrates periodic tasks (parse, collect, rotate) |
| **i18n System** | `app/routes.py`, `translations/`, `app/static/js/i18n.js` | Multi-language support |

### System Flow

```
OpenVPN Server → status.log
                     ↓
            Background Logger (logger.py)
                     ↓
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
Parser          Traffic          Server Status
(10s)          Collector         Collector (60s)
                 (10s)
    ↓                ↓                ↓
    └────────────────┼────────────────┘
                     ↓
              JSON Data Files
                     ↓
              Flask API Routes
                     ↓
               Web Browser
```

### Data Files

- **active_sessions.json** - Current active VPN connections
- **session_history.json** - Last 90 days of completed sessions
- **traffic_metrics.json** - 24 hours of traffic data
- **server_status.json** - Server operational status
- **history_archive/*.json.gz** - Compressed monthly session archives

---

## Working with Docker

### Docker Compose v1 vs v2

**Compose v2 (modern):** `docker compose` (space, no hyphen)
**Compose v1 (legacy):** `docker-compose` (with hyphen)

All examples below use v2 syntax. For v1, simply replace `docker compose` with `docker-compose`.

### Development Commands

**With Traefik (docker-compose.yml):**
```bash
# Build and start
docker compose up --build -d

# View logs (follow mode)
docker compose logs -f

# View logs for specific service
docker compose logs -f openvpn-admin

# Rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up -d

# Access container shell
docker compose exec openvpn-admin bash

# Restart single service (after code change)
docker compose restart openvpn-admin

# Stop services
docker compose down
```

**Standalone (docker-compose.standalone.yml):**
```bash
# Build and start
docker compose -f docker-compose.standalone.yml up --build -d

# View logs
docker compose -f docker-compose.standalone.yml logs -f

# Rebuild from scratch
docker compose -f docker-compose.standalone.yml down
docker compose -f docker-compose.standalone.yml build --no-cache
docker compose -f docker-compose.standalone.yml up -d

# Access container shell
docker compose -f docker-compose.standalone.yml exec openvpn-admin bash

# Restart single service
docker compose -f docker-compose.standalone.yml restart openvpn-admin
```

### Live Code Editing

To test changes without rebuilding container:

```bash
# Mount code directory as volume (add to docker-compose.yml)
volumes:
  - ./app:/app/app:ro  # Read-only mount of app code

# After code changes, restart Flask
docker compose exec openvpn-admin supervisorctl restart flask
```

---

## Running Tests

### Test Structure

- `tests/test_parser.py` - Unit tests for status log parsing logic
- `tests/test_routes.py` - Integration tests for API endpoints

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_parser.py

# Run specific test
pytest tests/test_parser.py::test_parse_active_clients

# Run with coverage report
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Writing Tests

Example test structure:

```python
# tests/test_parser.py
import pytest
from app.parser import parse_status_log

def test_parse_active_clients(tmp_path):
    """Test parsing active clients from status.log"""
    # Create mock status.log
    status_log = tmp_path / "status.log"
    status_log.write_text("""
OpenVPN CLIENT LIST
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
client1,192.168.1.100:12345,1024,2048,2025-10-15 12:00:00
ROUTING TABLE
Virtual Address,Common Name,Real Address,Last Ref
10.8.0.10,client1,192.168.1.100:12345,2025-10-15 12:00:00
""")

    # Test parser
    clients = parse_status_log(str(status_log))
    assert len(clients) == 1
    assert clients[0]['name'] == 'client1'
```

---

## Code Formatting

### Black (Code Formatter)

```bash
# Format all Python files
black .

# Check what would be reformatted (dry run)
black --check .

# Format specific file
black app/routes.py
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py312']
```

### Flake8 (Linter)

```bash
# Check all files
flake8

# Check specific file
flake8 app/routes.py

# Show statistics
flake8 --statistics
```

Configuration in `.flake8` or `setup.cfg`.

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Working with Translations

### Translation System Overview

- **Backend:** Flask-Babel (Python/Jinja2 templates)
- **Frontend:** Custom i18n module (`app/static/js/i18n.js`)
- **Supported Languages:** English (en), Russian (ru)
- **Translation Files:** `translations/{lang}/LC_MESSAGES/messages.po`

### Adding New Translatable Strings

**Python Code:**
```python
from flask_babel import gettext as _

# In route or function
message = _("Your translatable text")
```

**Jinja2 Templates:**
```html
<h1>{{ _('Page Title') }}</h1>
<p>{{ _('Welcome message') }}</p>
```

**JavaScript:**
```javascript
// 1. Add to /api/translations endpoint in app/routes.py
@app.route("/api/translations")
def translations():
    return jsonify({
        "your_key": _("Your translatable text"),
        "another_key": _("Another text")
    })

// 2. Use in JavaScript
t('your_key')  // Returns translated string based on user's language
```

### Update Translation Files

```bash
# 1. Extract new strings to messages.pot
pybabel extract -F translations/babel.cfg -o translations/messages.pot .

# 2. Update existing .po files with new strings
pybabel update -i translations/messages.pot -d translations

# 3. Edit translations manually
nano translations/en/LC_MESSAGES/messages.po
nano translations/ru/LC_MESSAGES/messages.po

# 4. Compile translations to .mo files
python translations/compile_translations.py

# 5. Rebuild container to see changes
docker compose build
docker compose up -d
```

### Translation File Format

```po
# translations/ru/LC_MESSAGES/messages.po
msgid "Active Clients"
msgstr "Активные клиенты"

msgid "Session History"
msgstr "История сессий"
```

### Adding New Language

1. Initialize new language:
```bash
pybabel init -i translations/messages.pot -d translations -l fr  # French
```

2. Translate strings in `translations/fr/LC_MESSAGES/messages.po`

3. Add language to `app/routes.py`:
```python
SUPPORTED_LANGUAGES = ['en', 'ru', 'fr']
```

4. Compile translations:
```bash
python translations/compile_translations.py
```

See [I18N.md](../translations/I18N.md) for detailed localization guide.

---

## Common Development Tasks

### Adding New API Endpoint

1. **Add route function in `app/routes.py`:**

```python
@app.route("/api/your-endpoint")
@cache.cached(timeout=10, query_string=True)
def your_endpoint():
    """Your endpoint description"""
    # Use cached data to avoid re-parsing status.log
    clients = _get_cached_clients()

    # Process data
    result = process_data(clients)

    return jsonify(result)
```

2. **Add tests in `tests/test_routes.py`:**

```python
def test_your_endpoint(client):
    """Test your new endpoint"""
    response = client.get('/api/your-endpoint')
    assert response.status_code == 200
    data = response.get_json()
    assert 'expected_key' in data
```

3. **Update API documentation in README.md**

### Modifying Status Parser

1. **Edit `app/parser.py`:**

```python
def parse_status_log(status_log_path=None):
    """Parse OpenVPN status.log and return client data"""
    # Your changes here

    # Maintain backwards compatibility with JSON structure
    # Use file locking for any file operations
    pass
```

2. **Add unit tests in `tests/test_parser.py`:**

```python
def test_new_parser_feature(tmp_path):
    """Test new parser functionality"""
    # Create mock status.log
    # Test parser behavior
    pass
```

3. **Test with sample `status.log` files**

### Changing Data Retention

**Traffic Metrics (default: 24 hours):**
```python
# app/traffic_collector.py
MAX_METRIC_AGE_SECONDS = 48 * 60 * 60  # Change to 48 hours
```

**Session History (default: 90 days):**
```python
# app/history_manager.py
MAX_HISTORY_DAYS = 180  # Change to 180 days
```

### Adjusting Collection Intervals

```python
# logger.py
def main():
    last_history_rotation = datetime.now()
    last_server_status_update = datetime.now()

    while True:
        # Parse status and collect traffic every 10 seconds
        parse_status_log()
        collect_traffic_metrics()

        # Change interval here (default: 10 seconds)
        time.sleep(10)
```

### Adding New Configuration Variable

1. **Add to `app/config.py`:**

```python
# New configuration variable
YOUR_NEW_CONFIG = os.environ.get("YOUR_NEW_CONFIG", "default_value")
```

2. **Add to `docker-compose.yml`:**

```yaml
environment:
  - YOUR_NEW_CONFIG=production_value
```

3. **Add to `.env.example`:**

```bash
# Your new configuration
YOUR_NEW_CONFIG=default_value
```

4. **Document in README.md**

---

## Data Flow

### Detailed Flow Diagram

```
1. OpenVPN writes to status.log (every ~10s)
         ↓
2. Background logger (logger.py) triggers tasks:
   - parse_status_log() every 10s
   - collect_traffic_metrics() every 10s
   - update_server_status() every 60s
   - rotate_history_if_needed() every 24h
         ↓
3. Parser (app/parser.py):
   - Reads CLIENT LIST section
   - Reads ROUTING TABLE section
   - Normalizes IPv4/IPv6 addresses
   - For new clients: fetch geolocation from ip-api.com
   - Updates active_sessions.json
   - Appends disconnected sessions to session_history.json
         ↓
4. Traffic Collector (app/traffic_collector.py):
   - Reads current bytes_received/bytes_sent
   - Calculates speed (MB/s) from byte delta
   - Appends to traffic_metrics.json
   - Removes data older than 24 hours
         ↓
5. Server Status Collector (app/server_status_collector.py):
   - Checks status.log modification time
   - Determines server status (CONNECTED if updated < 30s ago)
   - Fetches public IP from ipify.org or icanhazip.com
   - Gets local IP from container's eth0 interface
   - Writes to server_status.json
         ↓
6. History Manager (app/history_manager.py):
   - Runs once every 24 hours
   - Keeps last 90 days in session_history.json
   - Archives older sessions to compressed monthly files
   - Compresses with gzip (~10x compression)
         ↓
7. Flask API Routes (app/routes.py):
   - Read cached/persisted JSON data
   - Apply request-level caching (Flask g object)
   - Apply response-level caching (Flask-Caching)
   - Return JSON responses
         ↓
8. Web UI (templates + static/js):
   - Fetch data via AJAX
   - Update charts and tables dynamically
   - Handle language switching
```

---

## Key Implementation Details

### File Locking Pattern

All JSON files use safe concurrent access to prevent race conditions:

```python
import fcntl

@contextmanager
def active_sessions_lock():
    """Context manager for locking active sessions file"""
    lock_file = f"{ACTIVE_SESSIONS_FILE}.lock"
    with open(lock_file, "w") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
```

**Atomic Updates:**
```python
# Write to temp file first
temp_file = f"{target_file}.tmp"
with open(temp_file, "w") as f:
    json.dump(data, f, indent=2)

# Atomically replace original file
os.replace(temp_file, target_file)
```

### Session Tracking Logic

**New Connection:**
```python
session_id = str(uuid.uuid4())
session = {
    "session_id": session_id,
    "name": client_name,
    "ip": real_ip,
    "vpn_ip": vpn_ip,
    "connected_at": datetime.now(timezone).isoformat(),
    "bytes_received": 0,
    "bytes_sent": 0,
    "location": fetch_geolocation(real_ip)  # API call to ip-api.com
}
active_sessions[client_name] = session
```

**Active Session Update:**
```python
# Update traffic stats every 10 seconds
session["bytes_received"] = current_bytes_received
session["bytes_sent"] = current_bytes_sent
```

**Disconnection:**
```python
# Calculate final duration
session["session_end"] = datetime.now(timezone).isoformat()
session["duration"] = calculate_duration(session["connected_at"], session["session_end"])

# Append to history
with history_log() as history:
    history.append(session)

# Remove from active sessions
del active_sessions[client_name]
```

### IP Address Normalization

Parser handles both IPv4 and IPv6:

```python
def _split_real_address(address):
    """Split 'ip:port' or '[ipv6]:port' into (ip, port)"""
    if address.startswith('['):
        # IPv6: [2001:db8::1]:1234
        ip, port = address.rsplit(']:', 1)
        return ip[1:], int(port)
    else:
        # IPv4: 192.168.1.1:1234
        ip, port = address.rsplit(':', 1)
        return ip, int(port)
```

### API Caching Strategy

**Two-Level Caching:**

1. **Request-Level (Flask `g` object):**
```python
def _get_cached_clients():
    """Get clients from cache or parse status.log"""
    if 'clients' not in g:
        g.clients = parse_status_log()
    return g.clients
```

Benefits:
- Single parse per HTTP request
- Shared across multiple endpoint calls within same request
- Fresh data on each HTTP request

2. **Response-Level (Flask-Caching):**
```python
@app.route("/api/clients")
@cache.cached(timeout=10)
def api_clients():
    return jsonify(_get_cached_clients())
```

Benefits:
- Reduced disk I/O
- Lower CPU usage
- Faster response times
- 10-second TTL matches data update frequency

### Geolocation Integration

**API Service:** ip-api.com (free tier, 45 requests/minute)

```python
def fetch_geolocation(ip_address):
    """Fetch geolocation data from ip-api.com"""
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}",
            timeout=5
        )
        data = response.json()

        if data['status'] == 'success':
            return {
                'city': data.get('city'),
                'country': data.get('country'),
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
                'country_code': data.get('countryCode')
            }
    except Exception as e:
        logger.error(f"Geolocation fetch failed: {e}")

    return None  # Graceful degradation
```

---

## Debugging

### Common Debugging Commands

**Check Container Logs:**
```bash
docker compose logs -f openvpn-admin
```

Look for:
- ✅ `OpenVPN background logger started...`
- ✅ `Traffic collector initialized...`
- ❌ `Permission denied: /var/log/openvpn/status.log`
- ❌ `Failed to write active_sessions.json`

**Verify Data Files:**
```bash
ls -lh data/
cat data/active_sessions.json | jq .
cat data/server_status.json | jq .
```

**Test Parser Directly:**
```bash
# Inside container
docker compose exec openvpn-admin python -c "from app.parser import parse_status_log; import json; print(json.dumps(parse_status_log(), indent=2))"

# Local development
python -c "from app.parser import parse_status_log; import json; print(json.dumps(parse_status_log(), indent=2))"
```

**Check Status Log:**
```bash
sudo tail -f /var/log/openvpn/status.log
sudo ls -lh /var/log/openvpn/status.log
```

**Verify File Locks:**
```bash
# Check for stale lock files
ls -lh data/*.lock

# Remove stale locks if needed
docker compose exec openvpn-admin rm data/*.lock
docker compose restart openvpn-admin
```

**Test API Endpoints:**
```bash
# Test locally
curl http://localhost:5000/api/clients | jq .
curl http://localhost:5000/api/server-status | jq .
curl http://localhost:5000/api/traffic-metrics?period=60 | jq .

# Test in production
curl https://vpn-monitor.example.com/api/clients -u openvpn:password | jq .
```

### Python Debugging

**Using pdb (Python Debugger):**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

**Using iPython for Interactive Testing:**
```bash
# Install iPython
pip install ipython

# Start iPython shell
ipython

# Import and test functions
from app.parser import parse_status_log
clients = parse_status_log()
print(clients)
```

**Logging:**
```python
# Add debug logging
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug(f"Parsed {len(clients)} clients")
logger.info(f"Traffic collected: {metrics}")
logger.error(f"Failed to fetch geolocation: {e}")
```

### Performance Profiling

**Profile API Endpoint:**
```python
import cProfile
import pstats

@app.route("/api/slow-endpoint")
def slow_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()

    # Your code here
    result = expensive_operation()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 slowest functions

    return jsonify(result)
```

**Profile Background Logger:**
```bash
python -m cProfile -o profile.stats logger.py
```

Analyze results:
```python
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
```

---

## Important Paths

- **OpenVPN status log (host):** `/var/log/openvpn/status.log`
- **Data directory (container):** `/app/data`
- **Data directory (host, default):** `./data`
- **Templates:** `app/templates/`
- **Static files:** `app/static/`
- **Configuration:** `app/config.py`
- **Background logger:** `logger.py`
- **Tests:** `tests/`
- **Translations:** `translations/`

## Common Gotchas

- **Permission denied (Docker socket):** User must be in `docker` group
- **Empty client table:** Container can't read `/var/log/openvpn/status.log`
- **Timezone errors:** `OPENVPN_MONITOR_TZ` must be valid IANA timezone
- **Geolocation not working:** ip-api.com rate limit (45 req/min)
- **File lock timeouts:** Stale `.lock` files in data directory
- **Changes not reflected:** Need to restart Flask or rebuild container
- **Cache issues:** Clear Flask-Caching or restart container

## Getting Help

- **GitHub Issues:** https://github.com/farggus/openvpn-monitor/issues
- **Contributing Guide:** [CONTRIBUTING.md](../CONTRIBUTING.md)
- **I18N Guide:** [translations/I18N.md](../translations/I18N.md)
