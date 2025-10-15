---
name: Upgrade to OpenVPN status-version 3
about: Enhancement to support modern OpenVPN status log format
title: 'Migrate to OpenVPN status-version 3 format'
labels: enhancement, parser
assignees: ''
---

## Description
Upgrade OpenVPN status log format from **version 1** (default) to **version 3** (modern, tab-separated format).

## Current Status

**OpenVPN Configuration:**
```conf
status /var/log/openvpn/status.log
# No status-version directive = defaults to version 1
```

**Current Format (Version 1):**
- Delimiter: Comma (`,`)
- Structure: Separate CLIENT LIST and ROUTING TABLE sections
- VPN IPs: Located in separate ROUTING TABLE section
- Parsing: Requires merging two sections by Common Name

## Motivation

### Version 3 Benefits:
1. **Reliable Parsing** - Tab-separated fields (no ambiguity with commas in data)
2. **Unified Format** - All client data in single CLIENT LIST section (includes VPN IPs)
3. **Additional Fields** - Client ID, Peer ID, Username fields available
4. **Modern Standard** - Recommended format for OpenVPN 2.4+ (we use 2.6.14)
5. **Simpler Code** - No need to merge separate sections

## Proposed Solution

### 1. OpenVPN Server Configuration
Add to `server.conf`:
```conf
status /var/log/openvpn/status.log
status-version 3  # ← Add this line
```

### 2. Update Parser (`app/parser.py`)
Modify status log parser to handle version 3 format:

**Version 3 Format:**
```
Common Name[TAB]Real Address[TAB]Virtual Address[TAB]Virtual IPv6[TAB]Bytes Received[TAB]Bytes Sent[TAB]Connected Since
```

**Changes needed:**
- Switch from comma to tab delimiter (`split('\t')`)
- Parse CLIENT LIST as single unified section
- Update ROUTING TABLE parsing (also tab-separated in v3)
- Maintain backward compatibility with v1 (optional)

### 3. Testing
- Test parser with both version 1 and version 3 formats
- Verify VPN IP extraction works correctly
- Ensure geolocation still functions
- Check API responses remain consistent

## Implementation Steps

- [ ] Document current version 1 parsing logic
- [ ] Create sample version 3 status.log for testing
- [ ] Update parser to detect format version
- [ ] Implement version 3 parsing logic
- [ ] Add unit tests for version 3 format
- [ ] Update documentation (README.md, CLAUDE.md)
- [ ] Test in development environment
- [ ] Update OpenVPN server configuration
- [ ] Deploy and verify in production

## Backward Compatibility

**Option A: Support both formats**
- Auto-detect format version by checking delimiter
- Maintain dual parsing logic

**Option B: Version 3 only**
- Simpler implementation
- Requires server configuration update
- Document migration in README

## Additional Context

### References:
- [OpenVPN Status Format Docs](https://openvpn.net/community-docs/management-interface.html)
- Current implementation: `app/parser.py:60-120`
- Related modules: `app/traffic_collector.py`, `app/routes.py`

### Version Comparison:
| Feature | Version 1 (current) | Version 3 (proposed) |
|---------|---------------------|----------------------|
| Delimiter | Comma | Tab |
| VPN IPs in CLIENT LIST | ❌ No | ✅ Yes |
| Client/Peer ID | ❌ No | ✅ Yes |
| Parsing complexity | High (2 sections) | Low (1 section) |
| Reliability | Medium | High |

## Priority
**Medium** - Enhancement that improves code maintainability and adopts modern standards. Current implementation works correctly but could be simplified.
