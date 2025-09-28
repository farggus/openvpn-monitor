"""Helpers for maintaining the local client geolocation database."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Dict, Iterable, MutableMapping

from .config import CLIENT_GEO_DB_PATH


_EMPTY_DB: Dict[str, Any] = {"clients": {}, "updated_at": None}


def _now_utc_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_read_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return deepcopy(_EMPTY_DB)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return deepcopy(_EMPTY_DB)

    if not isinstance(data, MutableMapping):
        return deepcopy(_EMPTY_DB)

    clients = data.get("clients")
    if not isinstance(clients, MutableMapping):
        data["clients"] = {}

    return data


def _safe_write_json(path: str, payload: Dict[str, Any]) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")

    os.replace(tmp_path, path)


def _ensure_client_record(db: Dict[str, Any], name: str) -> Dict[str, Any]:
    clients = db.setdefault("clients", {})
    client = clients.get(name)
    if client is None:
        client = {"name": name, "ips": {}, "first_seen": None, "last_seen": None}
        clients[name] = client
    return client


def _update_seen(record: Dict[str, Any], timestamp: str) -> bool:
    if not timestamp:
        return False

    changed = False
    first_seen = record.get("first_seen")
    if not first_seen or timestamp < first_seen:
        record["first_seen"] = timestamp
        changed = True

    last_seen = record.get("last_seen")
    if not last_seen or timestamp > last_seen:
        record["last_seen"] = timestamp
        changed = True

    return changed


def _ensure_ip_record(client: Dict[str, Any], ip: str) -> Dict[str, Any]:
    ips = client.setdefault("ips", {})
    ip_record = ips.get(ip)
    if ip_record is None:
        ip_record = {
            "ip": ip,
            "vpn_ipv4": [],
            "vpn_ipv6": [],
            "location": {"latitude": None, "longitude": None, "city": "", "country": ""},
            "first_seen": None,
            "last_seen": None,
        }
        ips[ip] = ip_record
    return ip_record


def _append_unique(sequence: list, value: str) -> bool:
    if not value:
        return False
    if value in sequence:
        return False
    sequence.append(value)
    return True


def ensure_geo_db_entries(history_entries: Iterable[Dict[str, Any]]) -> None:
    """Ensure that the geolocation DB knows about every client/IP in history."""

    db = _safe_read_json(CLIENT_GEO_DB_PATH)
    changed = False

    for entry in history_entries:
        name = entry.get("name")
        if not name:
            continue

        client = _ensure_client_record(db, name)

        timestamp = entry.get("timestamp") or ""
        if _update_seen(client, timestamp):
            changed = True

        ip = entry.get("ip") or ""
        if not ip:
            # Nothing to record if we don't have an external IP.
            continue

        ip_record = _ensure_ip_record(client, ip)
        if _update_seen(ip_record, timestamp):
            changed = True

        if _append_unique(ip_record["vpn_ipv4"], entry.get("vpn_ipv4")):
            changed = True

        if _append_unique(ip_record["vpn_ipv6"], entry.get("vpn_ipv6")):
            changed = True

    if changed:
        db["updated_at"] = _now_utc_iso()
        _safe_write_json(CLIENT_GEO_DB_PATH, db)

