---
name: Multi-Server Federation Support
about: Add federated monitoring for multiple OpenVPN servers
title: '[ENHANCEMENT] Multi-Server Federation Support'
labels: enhancement, feature
assignees: ''
---

## Description

Add **federated multi-server monitoring** capability to OpenVPN Monitor, allowing a central dashboard instance to aggregate and display data from multiple remote OpenVPN servers.

## Motivation

### Problem
Currently, each OpenVPN Monitor instance can only monitor a single local OpenVPN server. Organizations running multiple OpenVPN servers (e.g., different geographic locations, separate VPN instances) need to:
- Open multiple browser tabs/windows to monitor each server
- Manually aggregate client counts and traffic statistics
- Switch between dashboards to get a complete picture

### Use Cases
1. **Multi-Region VPN Infrastructure**: Monitor EU, US, and ASIA servers from one dashboard
2. **High Availability Setup**: Track all VPN servers in an HA cluster
3. **Client Distribution Analysis**: See which servers are most utilized
4. **Unified Reporting**: Generate reports across all VPN infrastructure

## Proposed Solution

### Architecture: Federated Monitoring

```
┌─────────────────────────────────────────────┐
│      Central Dashboard Instance             │
│      (Master Mode)                          │
│                                             │
│  Configuration:                             │
│  REMOTE_SERVERS=                            │
│    EU-1:https://vpn-eu1.example.com,       │
│    EU-2:https://vpn-eu2.example.com,       │
│    US-1:https://vpn-us1.example.com        │
└──────────────┬──────────────────────────────┘
               │
               │ HTTPS API Calls
               │ (reuse existing /api/clients)
               │
    ┌──────────┴────────┬────────────┐
    ▼                   ▼            ▼
┌─────────┐       ┌─────────┐   ┌─────────┐
│ Server 1│       │ Server 2│   │ Server 3│
│ (EU-1)  │       │ (EU-2)  │   │ (US-1)  │
│         │       │         │   │         │
│ Local   │       │ Local   │   │ Local   │
│ OpenVPN │       │ OpenVPN │   │ OpenVPN │
│ Monitor │       │ Monitor │   │ Monitor │
└─────────┘       └─────────┘   └─────────┘
```

### Key Features

#### 1. Configuration
- **Environment Variable**: `REMOTE_SERVERS` (comma-separated list)
- **Format**: `Name:URL` or just `URL`
- **Example**:
  ```bash
  REMOTE_SERVERS=EU-1:https://vpn-eu1.example.com,EU-2:https://vpn-eu2.example.com,US-1:https://vpn-us1.example.com
  FEDERATION_AUTH=openvpn:password  # Basic auth for remote servers
  ```

#### 2. Backend Components

**New Module: `app/federation.py`**
- `fetch_remote_clients(server)` - Fetch clients from remote /api/clients
- `fetch_remote_server_status(server)` - Fetch status from /api/server-status
- `aggregate_all_clients()` - Combine local + remote clients
- `get_all_servers_status()` - Get status of all servers

**New API Endpoints in `app/routes.py`**
- `GET /api/federation/enabled` - Check if federation is configured
- `GET /api/servers` - List all servers (local + remote) with status
- `GET /api/servers/<server_id>/clients` - Get clients for specific server
- `GET /api/clients/all-servers` - Aggregated clients from all servers

#### 3. Frontend Components

**New JavaScript Module: `app/static/js/federation.js`**
- Server selector dropdown
- Server overview cards (show status, client count, traffic)
- Filter clients by server
- "All Servers" aggregated view

**UI Features**
- ✅ Server overview with status cards (Online/Offline)
- ✅ Dropdown to filter clients by specific server
- ✅ "All Servers" view showing aggregated client list
- ✅ Server badge column in clients table
- ✅ Graceful handling of offline servers

#### 4. Security
- HTTPS required for all remote servers
- Basic Authentication support via `FEDERATION_AUTH`
- Configurable timeout: `FEDERATION_TIMEOUT=5` (seconds)
- Optional: Future enhancement for API token-based auth

### Implementation Details

#### Configuration Loading (`app/config.py`)
```python
def _load_remote_servers():
    """
    Load remote server URLs from environment variable.
    Format: Name:URL,Name:URL or URL,URL
    """
    servers_str = os.getenv("REMOTE_SERVERS", "").strip()
    if not servers_str:
        return []

    servers = []
    for entry in servers_str.split(","):
        # Parse "Name:URL" or just "URL"
        if ":" in entry and not entry.startswith("http"):
            name, url = entry.split(":", 1)
        else:
            url = entry
            name = urlparse(url).hostname

        servers.append({
            "id": name.lower().replace(" ", "-"),
            "name": name.strip(),
            "url": url.strip().rstrip("/")
        })

    return servers
```

#### Data Fetching (`app/federation.py`)
```python
def fetch_remote_clients(server):
    """Fetch clients from remote server's API"""
    try:
        url = urljoin(server["url"], "/api/clients")
        response = requests.get(
            url,
            timeout=FEDERATION_TIMEOUT,
            auth=_get_auth(),
            verify=True
        )

        if response.status_code == 200:
            data = response.json()
            # Add server metadata to each client
            for client in data.get("clients", []):
                client["server_id"] = server["id"]
                client["server_name"] = server["name"]
            return data
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from {server['name']}: {e}")

    return None
```

#### Frontend UI
```javascript
// Load all servers and display status cards
async function loadServersList() {
    const response = await fetch('/api/servers');
    const data = await response.json();

    // Render server cards with status
    data.servers.forEach(server => {
        renderServerCard(server);
    });
}

// Filter clients by server
async function filterByServer(serverId) {
    const endpoint = serverId === 'all'
        ? '/api/clients/all-servers'
        : `/api/servers/${serverId}/clients`;

    const response = await fetch(endpoint);
    const data = await response.json();
    updateClientsTable(data.clients);
}
```

## Alternatives Considered

### Alternative 1: Centralized Agent Approach
**Architecture**: Lightweight agents on each server send data to central collector

**Pros**:
- Lower resource usage (no full Flask app on each server)
- Push-based updates (real-time)

**Cons**:
- Requires new agent software
- More complex deployment
- Need to manage agent authentication

**Decision**: Rejected in favor of federated approach to reuse existing infrastructure

### Alternative 2: Database Replication
**Architecture**: All servers write to central database

**Pros**:
- Single source of truth
- Complex queries possible

**Cons**:
- Requires database infrastructure
- More complex deployment
- Not aligned with current file-based architecture

**Decision**: Rejected - too much architectural change

### Alternative 3: Log Aggregation
**Architecture**: Collect all `status.log` files to central location

**Pros**:
- Simple file copying
- No API dependencies

**Cons**:
- File locking issues
- Requires file sharing infrastructure
- Parsing complexity

**Decision**: Rejected - federation is cleaner

## Implementation Plan

Detailed implementation plan available in: **`MULTI_SERVER_IMPLEMENTATION_PLAN.md`**

### Phases

| Phase | Duration | Scope |
|-------|----------|-------|
| 1. Configuration Layer | 1-2 hours | Load REMOTE_SERVERS from env |
| 2. Federation Backend | 3-4 hours | Create federation.py module |
| 3. API Endpoints | 2-3 hours | Add /api/servers endpoints |
| 4. Frontend UI | 4-5 hours | Server selector and filtering |
| 5. Documentation | 1-2 hours | Update README and CLAUDE.md |
| 6. Testing | 2-3 hours | Unit and integration tests |
| 7. Deployment | 1-2 hours | Docker updates and validation |
| **Total** | **14-21 hours** | - |

### Success Criteria

- ✅ Central dashboard fetches data from multiple remote servers
- ✅ UI displays server overview with status indicators
- ✅ Users can filter clients by server or view all servers
- ✅ Offline servers marked clearly without breaking UI
- ✅ All API endpoints return correct aggregated data
- ✅ Tests achieve >80% coverage
- ✅ Documentation complete with setup instructions

## Additional Context

### Benefits

1. **User Experience**
   - Single dashboard for all VPN infrastructure
   - Quick overview of all servers at a glance
   - Easy switching between server-specific and aggregated views

2. **Operations**
   - Simplified monitoring for multi-server deployments
   - Early detection of server issues (offline status)
   - Better capacity planning (see which servers are busiest)

3. **Scalability**
   - No limit on number of remote servers
   - Each server remains independent and functional
   - Graceful degradation if remote servers are unreachable

### Compatibility

- ✅ Backward compatible - works in standalone mode if `REMOTE_SERVERS` not set
- ✅ No database changes required
- ✅ Reuses existing API endpoints
- ✅ Minimal code changes to core application

### Future Enhancements (Phase 8+)

1. **API Token Authentication** - Replace Basic Auth with Bearer tokens
2. **Redis Caching** - Cache remote server data for better performance
3. **Health Alerts** - Email/Slack notifications when servers go offline
4. **Historical Aggregation** - Unified session history across all servers
5. **WebSocket Support** - Real-time updates instead of polling
6. **Server Groups** - Organize servers by region/purpose

### Screenshots/Mockups

#### Server Overview
```
┌─────────────────────────────────────────────────────┐
│  Servers Overview                                   │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ EU-1     │  │ EU-2     │  │ US-1     │         │
│  │ ● Online │  │ ● Online │  │ ⚫ Offline│         │
│  │          │  │          │  │          │         │
│  │ 5 clients│  │ 3 clients│  │ 0 clients│         │
│  │ RX: 123MB│  │ RX: 45MB │  │ RX: 0 MB │         │
│  │ TX: 67MB │  │ TX: 23MB │  │ TX: 0 MB │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
```

#### Clients Table with Server Filter
```
┌─────────────────────────────────────────────────────┐
│  Filter by Server: [All Servers ▼]                 │
├─────────────────────────────────────────────────────┤
│  Client Name  │ IP          │ Server  │ Traffic   │
│  client1      │ 1.2.3.4     │ EU-1    │ 123 MB    │
│  client2      │ 5.6.7.8     │ EU-2    │ 45 MB     │
│  client3      │ 9.10.11.12  │ EU-1    │ 67 MB     │
└─────────────────────────────────────────────────────┘
```

### Related Issues

- None currently

### References

- Implementation Plan: `MULTI_SERVER_IMPLEMENTATION_PLAN.md`
- Project Documentation: `CLAUDE.md`
- Similar Feature in Other Projects:
  - Zabbix Proxy/Server architecture
  - Prometheus Federation
  - Grafana datasource aggregation

---

**Priority**: Medium-High
**Complexity**: Medium
**Estimated Effort**: 14-21 hours
**Breaking Changes**: None (fully backward compatible)
