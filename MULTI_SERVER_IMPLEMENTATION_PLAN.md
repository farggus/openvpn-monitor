# Multi-Server Federated Monitoring - Implementation Plan

## 📋 Overview

This document outlines the implementation plan for **Federated Multi-Server Monitoring** in OpenVPN Monitor.

**Architecture:** Each OpenVPN server runs its own instance of openvpn-monitor. A central dashboard instance aggregates data from remote instances via their existing REST APIs.

**Key Feature:** Configure remote server URLs via environment variable (comma-separated list).

---

## 🎯 Goals

1. ✅ Minimal code changes - reuse existing API endpoints
2. ✅ Each server remains independent and functional
3. ✅ Central dashboard aggregates data from all servers
4. ✅ UI supports:
   - View all servers in one table
   - Filter clients by specific server
   - Switch between aggregated and per-server views
5. ✅ Graceful failure handling (offline servers don't break dashboard)

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│         Central Dashboard Instance                       │
│         (Master Mode)                                    │
│                                                          │
│  Environment Variable:                                   │
│  REMOTE_SERVERS=                                         │
│    https://vpn-eu-1.example.com,                        │
│    https://vpn-eu-2.example.com,                        │
│    https://vpn-us-1.example.com                         │
│                                                          │
│  Features:                                               │
│  - Aggregates data from all remote servers              │
│  - Shows unified client list                            │
│  - Displays server status overview                      │
│  - Maintains its own local OpenVPN monitoring           │
└──────────────┬──────────────────────────────────────────┘
               │
               │ HTTPS API Calls
               │ GET /api/clients
               │ GET /api/server-status
               │
    ┌──────────┴────────────┬──────────────────┐
    │                       │                  │
    ▼                       ▼                  ▼
┌──────────┐          ┌──────────┐       ┌──────────┐
│ Server 1 │          │ Server 2 │       │ Server 3 │
│ (EU-1)   │          │ (EU-2)   │       │ (US-1)   │
│          │          │          │       │          │
│ Local    │          │ Local    │       │ Local    │
│ OpenVPN  │          │ OpenVPN  │       │ OpenVPN  │
│ Monitor  │          │ Monitor  │       │ Monitor  │
└──────────┘          └──────────┘       └──────────┘
```

---

## 📁 File Structure Changes

```
openvpn-monitor/
├── app/
│   ├── federation.py          # NEW: Remote server data fetcher
│   ├── config.py              # MODIFIED: Add REMOTE_SERVERS config
│   └── routes.py              # MODIFIED: Add /api/servers endpoint
├── app/templates/
│   └── index.html             # MODIFIED: Add server selector UI
├── app/static/
│   └── js/
│       └── federation.js      # NEW: Frontend logic for multi-server
├── .env.example               # MODIFIED: Add REMOTE_SERVERS example
├── docker-compose.yml         # MODIFIED: Add environment variable
├── README.md                  # MODIFIED: Document multi-server setup
└── MULTI_SERVER_IMPLEMENTATION_PLAN.md  # THIS FILE
```

---

## 🔧 Implementation Steps

### **Phase 1: Configuration Layer** (1-2 hours)

#### Step 1.1: Update `app/config.py`

Add configuration loading for remote servers:

```python
# app/config.py

def _load_remote_servers():
    """
    Load remote server URLs from environment variable.

    Format: Comma-separated URLs with optional display names
    Examples:
      REMOTE_SERVERS=https://vpn1.example.com,https://vpn2.example.com
      REMOTE_SERVERS=EU-1:https://vpn1.example.com,US-1:https://vpn2.example.com

    Returns:
        list of dicts: [{"id": "...", "name": "...", "url": "..."}]
    """
    servers_str = os.getenv("REMOTE_SERVERS", "").strip()

    if not servers_str:
        return []

    servers = []
    for idx, entry in enumerate(servers_str.split(",")):
        entry = entry.strip()
        if not entry:
            continue

        # Parse format: "name:url" or just "url"
        if ":" in entry and not entry.startswith("http"):
            # Format: "EU-1:https://..."
            name, url = entry.split(":", 1)
            name = name.strip()
            url = url.strip()
        else:
            # Format: "https://..."
            url = entry
            # Extract hostname for default name
            from urllib.parse import urlparse
            parsed = urlparse(url)
            name = parsed.hostname or f"Server-{idx+1}"

        # Generate server ID from URL
        server_id = name.lower().replace(" ", "-")

        servers.append({
            "id": server_id,
            "name": name,
            "url": url.rstrip("/")  # Remove trailing slash
        })

    return servers

# Load remote servers on module import
REMOTE_SERVERS = _load_remote_servers()

if REMOTE_SERVERS:
    logger.info(f"Loaded {len(REMOTE_SERVERS)} remote servers for federation")
    for server in REMOTE_SERVERS:
        logger.info(f"  - {server['name']} ({server['id']}): {server['url']}")
else:
    logger.info("No remote servers configured (running in standalone mode)")
```

**Testing:**
```bash
# Test configuration loading
export REMOTE_SERVERS="EU-1:https://vpn-eu1.example.com,US-1:https://vpn-us1.example.com"
python3 -c "from app.config import REMOTE_SERVERS; print(REMOTE_SERVERS)"
```

---

### **Phase 2: Federation Backend** (3-4 hours)

#### Step 2.1: Create `app/federation.py`

New module to handle remote server data fetching:

```python
# app/federation.py
"""
Federation module for aggregating data from remote OpenVPN Monitor instances.
"""
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .config import REMOTE_SERVERS

logger = logging.getLogger(__name__)

# HTTP timeout for remote API calls
API_TIMEOUT = int(os.getenv("FEDERATION_TIMEOUT", "5"))

# Optional: Basic auth credentials for remote servers
# Format: username:password (same for all servers)
FEDERATION_AUTH = os.getenv("FEDERATION_AUTH")


def _get_auth():
    """Get authentication tuple for requests."""
    if FEDERATION_AUTH and ":" in FEDERATION_AUTH:
        username, password = FEDERATION_AUTH.split(":", 1)
        return (username, password)
    return None


def fetch_remote_clients(server: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Fetch clients from a remote server's /api/clients endpoint.

    Args:
        server: Dict with keys 'id', 'name', 'url'

    Returns:
        Dict with 'clients' list or None on error
    """
    try:
        url = urljoin(server["url"], "/api/clients")
        response = requests.get(
            url,
            timeout=API_TIMEOUT,
            auth=_get_auth(),
            verify=True  # Set to False if using self-signed certs (not recommended)
        )

        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Fetched {len(data.get('clients', []))} clients from {server['name']}")
            return data
        else:
            logger.warning(
                f"Failed to fetch clients from {server['name']}: "
                f"HTTP {response.status_code}"
            )
            return None

    except requests.RequestException as e:
        logger.error(f"Error fetching clients from {server['name']}: {e}")
        return None


def fetch_remote_server_status(server: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Fetch server status from a remote server's /api/server-status endpoint.

    Args:
        server: Dict with keys 'id', 'name', 'url'

    Returns:
        Server status dict or None on error
    """
    try:
        url = urljoin(server["url"], "/api/server-status")
        response = requests.get(
            url,
            timeout=API_TIMEOUT,
            auth=_get_auth(),
            verify=True
        )

        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Fetched server status from {server['name']}")
            return data
        else:
            logger.warning(
                f"Failed to fetch server status from {server['name']}: "
                f"HTTP {response.status_code}"
            )
            return None

    except requests.RequestException as e:
        logger.error(f"Error fetching server status from {server['name']}: {e}")
        return None


def aggregate_all_clients() -> List[Dict[str, Any]]:
    """
    Aggregate clients from all remote servers.

    Returns:
        List of all clients with added 'server_id' and 'server_name' fields
    """
    all_clients = []

    for server in REMOTE_SERVERS:
        data = fetch_remote_clients(server)

        if data and "clients" in data:
            for client in data["clients"]:
                # Add server metadata to each client
                client["server_id"] = server["id"]
                client["server_name"] = server["name"]
                all_clients.append(client)

    return all_clients


def get_all_servers_status() -> List[Dict[str, Any]]:
    """
    Get status information for all remote servers.

    Returns:
        List of server status dicts with metadata
    """
    servers_status = []

    for server in REMOTE_SERVERS:
        status_data = fetch_remote_server_status(server)

        if status_data:
            # Merge server metadata with status data
            server_info = {
                "server_id": server["id"],
                "server_name": server["name"],
                "server_url": server["url"],
                "is_online": True,
                **status_data
            }
        else:
            # Server is unreachable
            server_info = {
                "server_id": server["id"],
                "server_name": server["name"],
                "server_url": server["url"],
                "is_online": False,
                "status": "Unreachable",
                "clients": 0
            }

        servers_status.append(server_info)

    return servers_status


def fetch_server_clients(server_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch clients for a specific server by ID.

    Args:
        server_id: Server identifier

    Returns:
        List of clients or None if server not found/unreachable
    """
    # Find server config
    server = next((s for s in REMOTE_SERVERS if s["id"] == server_id), None)

    if not server:
        logger.warning(f"Server {server_id} not found in REMOTE_SERVERS")
        return None

    data = fetch_remote_clients(server)

    if data and "clients" in data:
        clients = data["clients"]
        # Add server metadata
        for client in clients:
            client["server_id"] = server["id"]
            client["server_name"] = server["name"]
        return clients

    return None
```

**Testing:**
```bash
# Test federation module
export REMOTE_SERVERS="Test:https://httpbin.org"
python3 -c "
from app.federation import aggregate_all_clients, get_all_servers_status
print('Servers:', get_all_servers_status())
"
```

---

### **Phase 3: API Endpoints** (2-3 hours)

#### Step 3.1: Update `app/routes.py`

Add new API endpoints for federated data:

```python
# app/routes.py

# Add import at top of file
from .config import REMOTE_SERVERS
from .federation import (
    aggregate_all_clients,
    fetch_server_clients,
    get_all_servers_status,
)

# Add new endpoints after existing routes

@app.route("/api/federation/enabled")
def federation_enabled():
    """
    Check if federation mode is enabled.

    Returns:
        {
            "enabled": true/false,
            "server_count": N
        }
    """
    return jsonify({
        "enabled": len(REMOTE_SERVERS) > 0,
        "server_count": len(REMOTE_SERVERS)
    })


@app.route("/api/servers")
@cache.cached(timeout=10, query_string=False)
def get_all_servers():
    """
    Get list of all servers (local + remote) with their status.

    Returns:
        {
            "servers": [
                {
                    "server_id": "local",
                    "server_name": "Local Server",
                    "is_online": true,
                    "clients": 5,
                    "total_rx": 123.45,
                    "total_tx": 67.89,
                    "status": "CONNECTED",
                    ...
                },
                {
                    "server_id": "eu-1",
                    "server_name": "EU-1",
                    "is_online": true,
                    "clients": 3,
                    ...
                }
            ]
        }
    """
    try:
        servers = []

        # Add local server
        try:
            local_clients, _ = _get_cached_data()
            local_status = _load_server_status()

            local_server = {
                "server_id": "local",
                "server_name": os.getenv("SERVER_NAME", "Local Server"),
                "is_online": True,
                "clients": len(local_clients),
                "total_rx": round(
                    sum(c.get("bytes_received", 0) for c in local_clients) / (1024**2), 2
                ),
                "total_tx": round(
                    sum(c.get("bytes_sent", 0) for c in local_clients) / (1024**2), 2
                ),
                **local_status
            }
            servers.append(local_server)
        except Exception as e:
            logger.exception("Failed to load local server status")
            servers.append({
                "server_id": "local",
                "server_name": "Local Server",
                "is_online": False,
                "error": str(e)
            })

        # Add remote servers (if federation is enabled)
        if REMOTE_SERVERS:
            remote_servers = get_all_servers_status()
            servers.extend(remote_servers)

        return jsonify({"servers": servers})

    except Exception:
        logger.exception("[servers] Failed to aggregate servers")
        return _json_error(gettext("Failed to fetch servers list"))


@app.route("/api/servers/<server_id>/clients")
@cache.cached(timeout=10, query_string=True)
def get_server_clients_by_id(server_id: str):
    """
    Get clients for a specific server.

    Args:
        server_id: "local" for local server, or remote server ID

    Returns:
        {
            "server_id": "...",
            "server_name": "...",
            "clients": [...]
        }
    """
    try:
        if server_id == "local":
            # Return local clients
            clients, active_sessions = _get_cached_data()

            # Add location data
            for client in clients:
                common_name = client.get("common_name")
                if common_name and common_name in active_sessions:
                    client["location"] = active_sessions[common_name].get("location", {})
                client["server_id"] = "local"
                client["server_name"] = os.getenv("SERVER_NAME", "Local Server")

            return jsonify({
                "server_id": "local",
                "server_name": os.getenv("SERVER_NAME", "Local Server"),
                "clients": clients
            })

        # Fetch from remote server
        clients = fetch_server_clients(server_id)

        if clients is None:
            return _json_error(
                gettext("Server not found or unreachable"),
                404,
                code="server_not_found"
            )

        # Find server name
        server = next((s for s in REMOTE_SERVERS if s["id"] == server_id), None)
        server_name = server["name"] if server else server_id

        return jsonify({
            "server_id": server_id,
            "server_name": server_name,
            "clients": clients
        })

    except Exception:
        logger.exception(f"[server-clients] Failed to fetch clients for {server_id}")
        return _json_error(gettext("Failed to fetch server clients"))


@app.route("/api/clients/all-servers")
@cache.cached(timeout=10, query_string=False)
def get_all_servers_clients():
    """
    Get aggregated clients from all servers (local + remote).

    Returns:
        {
            "clients": [
                {
                    "common_name": "client1",
                    "server_id": "local",
                    "server_name": "Local Server",
                    ...
                },
                {
                    "common_name": "client2",
                    "server_id": "eu-1",
                    "server_name": "EU-1",
                    ...
                }
            ],
            "total_servers": 3,
            "total_clients": 10
        }
    """
    try:
        all_clients = []

        # Add local clients
        local_clients, active_sessions = _get_cached_data()
        for client in local_clients:
            common_name = client.get("common_name")
            if common_name and common_name in active_sessions:
                client["location"] = active_sessions[common_name].get("location", {})
            client["server_id"] = "local"
            client["server_name"] = os.getenv("SERVER_NAME", "Local Server")
            all_clients.append(client)

        # Add remote clients
        if REMOTE_SERVERS:
            remote_clients = aggregate_all_clients()
            all_clients.extend(remote_clients)

        return jsonify({
            "clients": all_clients,
            "total_servers": 1 + len(REMOTE_SERVERS),
            "total_clients": len(all_clients)
        })

    except Exception:
        logger.exception("[all-servers-clients] Failed to aggregate clients")
        return _json_error(gettext("Failed to fetch clients from all servers"))
```

**Testing:**
```bash
# Start Flask app
flask --app app run

# Test API endpoints
curl http://localhost:5000/api/federation/enabled
curl http://localhost:5000/api/servers
curl http://localhost:5000/api/servers/local/clients
curl http://localhost:5000/api/clients/all-servers
```

---

### **Phase 4: Frontend UI** (4-5 hours)

#### Step 4.1: Create `app/static/js/federation.js`

New JavaScript module for multi-server UI logic:

```javascript
// app/static/js/federation.js

/**
 * Federation module for multi-server monitoring UI
 */

let currentServerFilter = 'all'; // 'all' or specific server_id
let federationEnabled = false;

/**
 * Check if federation mode is enabled
 */
async function checkFederationEnabled() {
    try {
        const response = await fetch('/api/federation/enabled');
        const data = await response.json();
        federationEnabled = data.enabled;

        if (federationEnabled) {
            console.log(`Federation enabled with ${data.server_count} remote servers`);
            initFederationUI();
        } else {
            console.log('Federation disabled - running in standalone mode');
        }

        return federationEnabled;
    } catch (error) {
        console.error('Failed to check federation status:', error);
        return false;
    }
}

/**
 * Initialize federation UI components
 */
function initFederationUI() {
    // Show server selector
    const serverSelector = document.getElementById('server-selector');
    if (serverSelector) {
        serverSelector.style.display = 'block';
    }

    // Load servers list
    loadServersList();
}

/**
 * Load list of all servers and populate server selector
 */
async function loadServersList() {
    try {
        const response = await fetch('/api/servers');
        const data = await response.json();

        renderServersOverview(data.servers);
        populateServerFilter(data.servers);

    } catch (error) {
        console.error('Failed to load servers list:', error);
    }
}

/**
 * Render servers overview cards
 */
function renderServersOverview(servers) {
    const container = document.getElementById('servers-overview');
    if (!container) return;

    container.innerHTML = '';

    servers.forEach(server => {
        const statusBadge = server.is_online
            ? '<span class="badge bg-success">Online</span>'
            : '<span class="badge bg-danger">Offline</span>';

        const card = `
            <div class="col-md-4 mb-3">
                <div class="card server-card ${server.is_online ? '' : 'offline'}"
                     data-server-id="${server.server_id}"
                     style="cursor: pointer;">
                    <div class="card-body">
                        <h5 class="card-title">
                            ${escapeHtml(server.server_name)}
                            ${statusBadge}
                        </h5>
                        <div class="server-stats mt-3">
                            <div class="row text-center">
                                <div class="col-4">
                                    <div class="stat-label">Clients</div>
                                    <div class="stat-value">${server.clients || 0}</div>
                                </div>
                                <div class="col-4">
                                    <div class="stat-label">RX</div>
                                    <div class="stat-value">${(server.total_rx || 0).toFixed(1)} MB</div>
                                </div>
                                <div class="col-4">
                                    <div class="stat-label">TX</div>
                                    <div class="stat-value">${(server.total_tx || 0).toFixed(1)} MB</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', card);
    });

    // Add click handlers
    document.querySelectorAll('.server-card').forEach(card => {
        card.addEventListener('click', function() {
            const serverId = this.dataset.serverId;
            filterByServer(serverId);
        });
    });
}

/**
 * Populate server filter dropdown
 */
function populateServerFilter(servers) {
    const select = document.getElementById('server-filter-select');
    if (!select) return;

    // Clear existing options except "All Servers"
    select.innerHTML = '<option value="all">All Servers</option>';

    // Add server options
    servers.forEach(server => {
        const option = document.createElement('option');
        option.value = server.server_id;
        option.textContent = server.server_name;
        select.appendChild(option);
    });

    // Add change handler
    select.addEventListener('change', function() {
        filterByServer(this.value);
    });
}

/**
 * Filter clients by server
 */
async function filterByServer(serverId) {
    currentServerFilter = serverId;

    // Update UI to show loading state
    const clientsTable = document.getElementById('clients-table-body');
    if (clientsTable) {
        clientsTable.innerHTML = '<tr><td colspan="8" class="text-center">Loading...</td></tr>';
    }

    try {
        let clients;

        if (serverId === 'all') {
            // Fetch all clients
            const response = await fetch('/api/clients/all-servers');
            const data = await response.json();
            clients = data.clients;
        } else {
            // Fetch clients for specific server
            const response = await fetch(`/api/servers/${serverId}/clients`);
            const data = await response.json();
            clients = data.clients;
        }

        // Update clients table
        updateClientsTable(clients);

        // Update active filter display
        updateFilterDisplay(serverId);

    } catch (error) {
        console.error(`Failed to load clients for server ${serverId}:`, error);
        if (clientsTable) {
            clientsTable.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-danger">
                        Failed to load clients
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * Update active filter display
 */
function updateFilterDisplay(serverId) {
    const filterDisplay = document.getElementById('active-filter');
    if (!filterDisplay) return;

    if (serverId === 'all') {
        filterDisplay.innerHTML = '<strong>Showing:</strong> All Servers';
    } else {
        const select = document.getElementById('server-filter-select');
        const serverName = select ? select.options[select.selectedIndex].text : serverId;
        filterDisplay.innerHTML = `<strong>Showing:</strong> ${escapeHtml(serverName)}`;
    }
}

/**
 * Update clients table with server information
 */
function updateClientsTable(clients) {
    const tbody = document.getElementById('clients-table-body');
    if (!tbody) return;

    if (!clients || clients.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    No clients connected
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = '';

    clients.forEach(client => {
        const serverBadge = federationEnabled
            ? `<span class="badge bg-info">${escapeHtml(client.server_name || 'Unknown')}</span>`
            : '';

        const row = `
            <tr>
                <td>${escapeHtml(client.common_name || 'Unknown')}</td>
                <td>${escapeHtml(client.real_ip || '-')}</td>
                <td>${escapeHtml(client.vpn_ip || '-')}</td>
                <td>${formatBytes(client.bytes_received || 0)}</td>
                <td>${formatBytes(client.bytes_sent || 0)}</td>
                <td>${escapeHtml(client.connected_since || '-')}</td>
                <td>${escapeHtml(client.time_online || '-')}</td>
                <td>${serverBadge}</td>
            </tr>
        `;

        tbody.insertAdjacentHTML('beforeend', row);
    });
}

/**
 * Utility: Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Utility: Format bytes
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    checkFederationEnabled();
});
```

#### Step 4.2: Update `app/templates/index.html`

Add UI components for server selector and overview:

```html
<!-- Add in <head> section -->
<script src="{{ url_for('static', filename='js/federation.js') }}"></script>

<!-- Add server selector section after navbar -->
<div id="server-selector" class="container mt-3" style="display: none;">
    <div class="row">
        <div class="col-md-12">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Servers Overview</h5>
                    <div class="row" id="servers-overview">
                        <!-- Server cards will be inserted here by JavaScript -->
                    </div>

                    <hr class="my-4">

                    <div class="row align-items-center">
                        <div class="col-md-6">
                            <label for="server-filter-select" class="form-label">
                                Filter Clients by Server:
                            </label>
                            <select id="server-filter-select" class="form-select">
                                <option value="all">All Servers</option>
                            </select>
                        </div>
                        <div class="col-md-6 text-end">
                            <div id="active-filter" class="text-muted">
                                <strong>Showing:</strong> All Servers
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modify clients table to include Server column -->
<table class="table table-striped" id="clients-table">
    <thead>
        <tr>
            <th>Client Name</th>
            <th>Real IP</th>
            <th>VPN IP</th>
            <th>Received</th>
            <th>Sent</th>
            <th>Connected Since</th>
            <th>Time Online</th>
            <th id="server-column-header" style="display: none;">Server</th>
        </tr>
    </thead>
    <tbody id="clients-table-body">
        <!-- Client rows will be inserted here -->
    </tbody>
</table>
```

**CSS additions** (add to `app/static/css/style.css` if it exists, or inline):

```css
.server-card {
    transition: transform 0.2s, box-shadow 0.2s;
    border-left: 4px solid #28a745;
}

.server-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.server-card.offline {
    border-left-color: #dc3545;
    opacity: 0.7;
}

.stat-label {
    font-size: 0.85rem;
    color: #6c757d;
    font-weight: 500;
}

.stat-value {
    font-size: 1.25rem;
    font-weight: 600;
    color: #212529;
}

#server-selector {
    background: #f8f9fa;
    padding: 1rem 0;
}
```

---

### **Phase 5: Configuration & Documentation** (1-2 hours)

#### Step 5.1: Update `.env.example`

Add federation configuration examples:

```bash
# ============================================================================
# Multi-Server Federation (Optional)
# ============================================================================
# Enable multi-server monitoring by configuring remote OpenVPN Monitor instances
# This allows a central dashboard to aggregate data from multiple servers
#
# Format options:
#   1. Simple URLs (comma-separated):
#      REMOTE_SERVERS=https://vpn1.example.com,https://vpn2.example.com
#
#   2. Named servers (Name:URL pairs):
#      REMOTE_SERVERS=EU-Server-1:https://vpn-eu1.example.com,US-Server-1:https://vpn-us1.example.com
#
# Requirements:
#   - All remote servers must run OpenVPN Monitor with accessible API endpoints
#   - If remote servers use Basic Auth, set FEDERATION_AUTH below
#
# Example (disabled by default):
# REMOTE_SERVERS=EU-1:https://vpn-eu1.example.com,EU-2:https://vpn-eu2.example.com,US-1:https://vpn-us1.example.com

# Authentication for remote servers (if they use Basic Auth)
# Format: username:password
# FEDERATION_AUTH=openvpn:your-password-here

# API timeout for remote server requests (seconds, default: 5)
# FEDERATION_TIMEOUT=5

# Optional: Name for the local server when displayed in federation view
# SERVER_NAME=Main Server
```

#### Step 5.2: Update `README.md`

Add multi-server setup section:

```markdown
## Multi-Server Federation

OpenVPN Monitor supports **federated monitoring** - aggregate data from multiple OpenVPN servers into a single dashboard.

### Architecture

- Each OpenVPN server runs its own instance of `openvpn-monitor`
- One instance is designated as the "central dashboard"
- Central dashboard fetches data from remote instances via REST API

### Setup

#### 1. Deploy OpenVPN Monitor on each server

Follow standard installation on each OpenVPN server:

```bash
# On Server 1 (EU-1)
docker compose up -d

# On Server 2 (EU-2)
docker compose up -d

# On Server 3 (US-1)
docker compose up -d
```

#### 2. Configure central dashboard

On your central dashboard instance, add remote servers to `.env`:

```bash
# .env
REMOTE_SERVERS=EU-1:https://vpn-eu1.example.com,EU-2:https://vpn-eu2.example.com,US-1:https://vpn-us1.example.com
SERVER_NAME=Central Dashboard

# If remote servers use Basic Auth (recommended)
FEDERATION_AUTH=openvpn:your-password-here
```

#### 3. Restart central dashboard

```bash
docker compose restart
```

### Features

✅ **Unified View**: See all clients from all servers in one table
✅ **Per-Server View**: Filter clients by specific server
✅ **Server Overview**: Monitor status of all servers at a glance
✅ **Graceful Failure**: Offline servers don't break the dashboard

### Security Considerations

- Use HTTPS for all remote server URLs
- Enable Basic Authentication on all instances
- Use strong passwords (generate with `htpasswd`)
- Consider VPN or firewall rules to restrict API access
- Optionally use API tokens (future enhancement)

### Troubleshooting

**Problem**: Remote servers show as "Offline"

Solutions:
- Check network connectivity: `curl https://remote-server/api/server-status`
- Verify authentication credentials in `FEDERATION_AUTH`
- Check firewall rules allow HTTPS traffic
- Review logs: `docker compose logs -f`

**Problem**: "Failed to fetch clients"

Solutions:
- Verify remote server is running: `docker compose ps`
- Check SSL certificate validity
- Increase timeout: `FEDERATION_TIMEOUT=10`
```

#### Step 5.3: Update `CLAUDE.md`

Document federation architecture:

```markdown
## Multi-Server Federation

### Overview

Federation allows one OpenVPN Monitor instance (central dashboard) to aggregate data from multiple remote instances.

**Key files:**
- `app/federation.py` - Remote data fetching logic
- `app/static/js/federation.js` - Frontend multi-server UI
- `app/config.py` - `REMOTE_SERVERS` configuration loading

### Configuration

Environment variables:
- `REMOTE_SERVERS` - Comma-separated list of remote URLs (with optional names)
- `FEDERATION_AUTH` - Basic auth credentials for remote servers
- `FEDERATION_TIMEOUT` - HTTP timeout for remote API calls (default: 5s)
- `SERVER_NAME` - Display name for local server in federation view

### How It Works

1. **Config Loading**: `app/config.py` parses `REMOTE_SERVERS` env var on startup
2. **Data Fetching**: `app/federation.py` makes HTTP GET requests to `/api/clients` and `/api/server-status` on remote instances
3. **Aggregation**: API endpoints in `app/routes.py` combine local + remote data
4. **UI Rendering**: JavaScript in `federation.js` displays server overview and filter controls

### API Endpoints

Federation adds these endpoints:

- `GET /api/federation/enabled` - Check if federation is configured
- `GET /api/servers` - List all servers with status
- `GET /api/servers/<server_id>/clients` - Get clients for specific server
- `GET /api/clients/all-servers` - Get aggregated clients from all servers

### Testing Federation Locally

```bash
# Terminal 1: Run first instance on port 5000
export SERVER_NAME="Server 1"
flask --app app run --port 5000

# Terminal 2: Run second instance on port 5001
export SERVER_NAME="Server 2"
flask --app app run --port 5001

# Terminal 3: Run central dashboard with federation
export SERVER_NAME="Central Dashboard"
export REMOTE_SERVERS="Server-1:http://localhost:5000,Server-2:http://localhost:5001"
flask --app app run --port 5002

# Open browser: http://localhost:5002
```

### Error Handling

- Remote server unreachable → Marked as "Offline", local functionality unaffected
- Timeout errors → Logged and skipped, doesn't block UI
- Invalid responses → Logged, empty client list returned
```

---

### **Phase 6: Testing & Validation** (2-3 hours)

#### Step 6.1: Unit Tests

Create `tests/test_federation.py`:

```python
# tests/test_federation.py
import pytest
from unittest.mock import patch, Mock
from app.federation import (
    fetch_remote_clients,
    aggregate_all_clients,
    get_all_servers_status,
)


@pytest.fixture
def mock_server():
    return {
        "id": "test-server",
        "name": "Test Server",
        "url": "https://test.example.com"
    }


def test_fetch_remote_clients_success(mock_server):
    """Test successful client fetch from remote server"""
    with patch('app.federation.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "clients": [
                {"common_name": "client1", "real_ip": "1.2.3.4"}
            ]
        }
        mock_get.return_value = mock_response

        result = fetch_remote_clients(mock_server)

        assert result is not None
        assert "clients" in result
        assert len(result["clients"]) == 1


def test_fetch_remote_clients_timeout(mock_server):
    """Test timeout handling"""
    with patch('app.federation.requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = fetch_remote_clients(mock_server)

        assert result is None


def test_aggregate_clients_adds_server_metadata(mock_server):
    """Test that aggregated clients include server metadata"""
    with patch('app.federation.REMOTE_SERVERS', [mock_server]):
        with patch('app.federation.fetch_remote_clients') as mock_fetch:
            mock_fetch.return_value = {
                "clients": [{"common_name": "client1"}]
            }

            result = aggregate_all_clients()

            assert len(result) == 1
            assert result[0]["server_id"] == "test-server"
            assert result[0]["server_name"] == "Test Server"
```

#### Step 6.2: Integration Tests

Test federation endpoints:

```bash
# tests/test_routes_federation.py
def test_federation_enabled_endpoint(client):
    """Test /api/federation/enabled endpoint"""
    response = client.get('/api/federation/enabled')
    data = response.get_json()

    assert response.status_code == 200
    assert "enabled" in data
    assert "server_count" in data


def test_get_all_servers_includes_local(client):
    """Test /api/servers includes local server"""
    response = client.get('/api/servers')
    data = response.get_json()

    assert response.status_code == 200
    assert "servers" in data
    assert len(data["servers"]) >= 1

    # Check local server is present
    local_server = next(
        (s for s in data["servers"] if s["server_id"] == "local"),
        None
    )
    assert local_server is not None


def test_get_server_clients_local(client):
    """Test /api/servers/local/clients endpoint"""
    response = client.get('/api/servers/local/clients')
    data = response.get_json()

    assert response.status_code == 200
    assert "server_id" in data
    assert data["server_id"] == "local"
    assert "clients" in data
```

Run tests:

```bash
pytest tests/test_federation.py -v
pytest tests/test_routes_federation.py -v
```

---

### **Phase 7: Deployment** (1-2 hours)

#### Step 7.1: Update `docker-compose.yml`

Add environment variable support:

```yaml
services:
  openvpn-admin:
    # ... existing config ...
    environment:
      # Federation settings
      - REMOTE_SERVERS=${REMOTE_SERVERS:-}
      - FEDERATION_AUTH=${FEDERATION_AUTH:-}
      - FEDERATION_TIMEOUT=${FEDERATION_TIMEOUT:-5}
      - SERVER_NAME=${SERVER_NAME:-Local Server}
```

#### Step 7.2: Deployment checklist

Create `DEPLOYMENT_CHECKLIST.md`:

```markdown
# Multi-Server Federation Deployment Checklist

## Pre-Deployment

- [ ] All remote servers are running OpenVPN Monitor
- [ ] All remote servers are accessible via HTTPS
- [ ] Basic Auth is enabled on all servers
- [ ] Test API endpoints manually: `curl https://remote-server/api/clients -u user:pass`

## Central Dashboard Setup

- [ ] Copy `.env.example` to `.env`
- [ ] Configure `REMOTE_SERVERS` with all remote server URLs
- [ ] Set `FEDERATION_AUTH` with correct credentials
- [ ] Set `SERVER_NAME` for central dashboard
- [ ] Build and start container: `docker compose up -d --build`
- [ ] Check logs: `docker compose logs -f`

## Validation

- [ ] Open dashboard in browser
- [ ] Verify "Servers Overview" section is visible
- [ ] Check all servers show as "Online"
- [ ] Test "All Servers" view - should show clients from all servers
- [ ] Test per-server filtering - select each server individually
- [ ] Check server cards show correct client counts

## Troubleshooting

If servers show as offline:
- [ ] Check network connectivity: `docker exec openvpn-admin curl https://remote-server/api/server-status`
- [ ] Verify credentials: `curl https://remote-server/api/clients -u username:password`
- [ ] Check container logs: `docker compose logs -f`
- [ ] Increase timeout if needed: `FEDERATION_TIMEOUT=10`
```

---

## 📊 Implementation Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Configuration Layer | 1-2 hours | None |
| Phase 2: Federation Backend | 3-4 hours | Phase 1 |
| Phase 3: API Endpoints | 2-3 hours | Phase 2 |
| Phase 4: Frontend UI | 4-5 hours | Phase 3 |
| Phase 5: Documentation | 1-2 hours | All phases |
| Phase 6: Testing | 2-3 hours | Phase 1-4 |
| Phase 7: Deployment | 1-2 hours | All phases |
| **Total** | **14-21 hours** | - |

---

## 🔒 Security Considerations

### Authentication
- All remote servers **must** use HTTPS (not HTTP)
- Enable Basic Authentication on all instances
- Use strong passwords (generate with `htpasswd`)
- Store credentials in `.env` file (not in code)
- Add `.env` to `.gitignore`

### Network Security
- Consider restricting API access to specific IPs
- Use firewall rules to allow only dashboard IP
- Optionally use VPN between servers
- Enable CORS restrictions if needed

### Data Privacy
- Remote servers expose client data via API
- Ensure compliance with data protection regulations
- Consider data retention policies
- Log access to federation endpoints

---

## 🚀 Future Enhancements

### Phase 8 (Optional): Advanced Features

1. **API Token Authentication**
   - Replace Basic Auth with Bearer tokens
   - Per-server token configuration
   - Token rotation support

2. **Caching & Performance**
   - Redis cache for remote server data
   - Configurable cache TTL per server
   - Background refresh workers

3. **Health Monitoring**
   - Alert on server downtime
   - Email/Slack notifications
   - Uptime statistics

4. **Historical Data Aggregation**
   - Fetch history from remote servers
   - Unified session history view
   - Cross-server analytics

5. **Advanced Filtering**
   - Filter by client name across all servers
   - Date range filters
   - Traffic threshold filters

---

## 📝 Notes

- Federation is **optional** - if `REMOTE_SERVERS` is not set, application runs in standalone mode
- Remote servers can also be federation dashboards (recursive federation)
- No database required - all data fetched in real-time from remote APIs
- Graceful degradation - offline servers don't break the UI

---

## ✅ Success Criteria

Implementation is complete when:

1. ✅ Central dashboard can fetch data from multiple remote servers
2. ✅ UI displays server overview with status cards
3. ✅ Users can filter clients by server or view all servers
4. ✅ Offline servers are clearly marked and don't cause errors
5. ✅ All API endpoints return correct data
6. ✅ Tests pass with >80% coverage
7. ✅ Documentation is complete and accurate

---

## 🐛 Known Limitations

1. **Real-time Updates**: Currently uses polling (cache TTL). WebSocket support could be added later.
2. **Authentication**: Basic Auth only. Token-based auth is a future enhancement.
3. **SSL Verification**: Self-signed certificates require `verify=False` (security risk).
4. **Performance**: Sequential API calls to remote servers. Could be parallelized with asyncio.
5. **Error Messages**: Limited error details passed to frontend. Could be enhanced.

---

## 📚 References

- Flask Documentation: https://flask.palletsprojects.com/
- Flask-Caching: https://flask-caching.readthedocs.io/
- Requests Library: https://requests.readthedocs.io/
- Bootstrap 5: https://getbootstrap.com/docs/5.0/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-16
**Author**: Claude Code Assistant
**Status**: Ready for Implementation
