# GitHub Issue: Multi-Server Federation Support

**Copy this content to create a new issue on GitHub**

---

**Title**: [ENHANCEMENT] Multi-Server Federation Support

**Labels**: `enhancement`, `feature`

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

Each OpenVPN server runs its own instance of OpenVPN Monitor. A central "master" instance aggregates data from remote instances via existing REST API endpoints.

```
Central Dashboard
       │
       ├─── HTTPS GET /api/clients ──→ Server 1 (EU-1)
       ├─── HTTPS GET /api/clients ──→ Server 2 (EU-2)
       └─── HTTPS GET /api/clients ──→ Server 3 (US-1)
```

### Key Features

#### 1. Simple Configuration
```bash
# .env on central dashboard
REMOTE_SERVERS=EU-1:https://vpn-eu1.example.com,EU-2:https://vpn-eu2.example.com,US-1:https://vpn-us1.example.com
FEDERATION_AUTH=openvpn:password
```

#### 2. New API Endpoints
- `GET /api/federation/enabled` - Check if federation is configured
- `GET /api/servers` - List all servers (local + remote) with status
- `GET /api/servers/<server_id>/clients` - Get clients for specific server
- `GET /api/clients/all-servers` - Aggregated clients from all servers

#### 3. Frontend Features
- ✅ Server overview cards showing status (Online/Offline)
- ✅ Client count, RX/TX traffic per server
- ✅ Dropdown to filter clients by specific server
- ✅ "All Servers" view with aggregated client list
- ✅ Server badge column in clients table
- ✅ Graceful handling of offline servers (no errors)

#### 4. Security
- HTTPS required for all remote servers
- Basic Authentication support
- Configurable timeout: `FEDERATION_TIMEOUT=5` seconds
- Future: API token-based authentication

### UI Mockup

#### Servers Overview
```
┌────────────────────────────────────────────────┐
│  Servers Overview                              │
├────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ EU-1     │  │ EU-2     │  │ US-1     │    │
│  │ ● Online │  │ ● Online │  │ ⚫ Offline│    │
│  │ 5 clients│  │ 3 clients│  │ 0 clients│    │
│  │ RX: 123MB│  │ RX: 45MB │  │ RX: 0 MB │    │
│  │ TX: 67MB │  │ TX: 23MB │  │ TX: 0 MB │    │
│  └──────────┘  └──────────┘  └──────────┘    │
└────────────────────────────────────────────────┘

Filter by Server: [All Servers ▼]

┌────────────────────────────────────────────────┐
│ Client     │ IP        │ Server │ Traffic     │
├────────────────────────────────────────────────┤
│ client1    │ 1.2.3.4   │ EU-1   │ 123 MB      │
│ client2    │ 5.6.7.8   │ EU-2   │ 45 MB       │
│ client3    │ 9.10.11.12│ EU-1   │ 67 MB       │
└────────────────────────────────────────────────┘
```

## Implementation Plan

**Detailed plan**: See `MULTI_SERVER_IMPLEMENTATION_PLAN.md` in project root

### Timeline

| Phase | Duration | Scope |
|-------|----------|-------|
| Configuration Layer | 1-2 hours | Load REMOTE_SERVERS from env |
| Federation Backend | 3-4 hours | Create `app/federation.py` |
| API Endpoints | 2-3 hours | Add `/api/servers/*` endpoints |
| Frontend UI | 4-5 hours | Server selector & filtering |
| Documentation | 1-2 hours | Update README, CLAUDE.md |
| Testing | 2-3 hours | Unit & integration tests |
| Deployment | 1-2 hours | Docker updates |
| **Total** | **14-21 hours** | |

### Success Criteria
- ✅ Central dashboard fetches data from multiple remote servers
- ✅ UI displays server overview with status
- ✅ Filter by server or view all servers
- ✅ Offline servers don't break UI
- ✅ Test coverage >80%
- ✅ Complete documentation

## Alternatives Considered

### 1. Centralized Agent Approach
Lightweight agents on each server push data to central collector.

**Rejected**: Requires new software deployment, more complex than reusing existing API.

### 2. Database Replication
All servers write to central database.

**Rejected**: Too much architectural change, requires database infrastructure.

### 3. Log Aggregation
Collect all `status.log` files centrally.

**Rejected**: File locking issues, complex parsing, federation is cleaner.

## Benefits

### User Experience
- Single dashboard for all VPN infrastructure
- Quick overview of server health
- Easy switching between views

### Operations
- Simplified monitoring for multi-server deployments
- Early detection of server issues
- Better capacity planning

### Technical
- ✅ **Backward compatible** - works without `REMOTE_SERVERS` (standalone mode)
- ✅ **No database changes** required
- ✅ **Reuses existing API** endpoints
- ✅ **Minimal code changes** to core app
- ✅ **Graceful degradation** if remote servers unreachable

## Future Enhancements (Post-MVP)

1. **API Token Auth** - Replace Basic Auth with tokens
2. **Redis Caching** - Cache remote data for performance
3. **Health Alerts** - Notifications when servers go offline
4. **Historical Aggregation** - Unified session history
5. **WebSocket Updates** - Real-time data instead of polling
6. **Server Groups** - Organize servers by region/purpose

## Additional Context

### Files to be Created/Modified

**New Files:**
- `app/federation.py` - Remote data fetching logic
- `app/static/js/federation.js` - Frontend multi-server UI
- `tests/test_federation.py` - Unit tests
- `MULTI_SERVER_IMPLEMENTATION_PLAN.md` - Detailed implementation guide

**Modified Files:**
- `app/config.py` - Add `REMOTE_SERVERS` loading
- `app/routes.py` - Add federation API endpoints
- `app/templates/index.html` - Add server selector UI
- `.env.example` - Document new variables
- `README.md` - Multi-server setup section
- `CLAUDE.md` - Federation architecture docs
- `docker-compose.yml` - Environment variables

### References
- Prometheus Federation: https://prometheus.io/docs/prometheus/latest/federation/
- Grafana Datasources: https://grafana.com/docs/grafana/latest/datasources/
- Similar pattern used in Zabbix Proxy/Server architecture

---

**Priority**: Medium-High
**Complexity**: Medium
**Estimated Effort**: 14-21 hours
**Breaking Changes**: None
**Backward Compatibility**: ✅ Yes

---

## How to Create This Issue on GitHub

1. Go to: https://github.com/farggus/openvpn-monitor/issues/new/choose
2. Select "Enhancement" template
3. Copy this content
4. Add labels: `enhancement`, `feature`
5. Submit issue
