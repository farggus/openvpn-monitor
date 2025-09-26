# Code Review Notes

## Parser (`app/parser.py`)
- `LOCAL_TZ` is hard-coded to `Europe/Bucharest`; timezone/log paths should be configurable via environment or config to avoid incorrect calculations when deployed elsewhere. This also makes unit testing harder because the parser relies on the host time zone. 【F:app/parser.py†L9-L11】
- `parse_status_log` reads the entire log into memory and then iterates twice (once for the routing table, once for clients). Streaming the file once would lower overhead and reduce latency for large logs that the API polls every few seconds. 【F:app/parser.py†L26-L79】
- Every API call triggers updates to `active_sessions.json`/`session_history.log`. Without file locking this risks race conditions (corrupted JSON, duplicate history rows) once multiple workers or the background logger run concurrently. 【F:app/parser.py†L18-L25】【F:app/parser.py†L96-L123】
- Error handling falls back to `print` statements; replacing them with the standard `logging` module and returning meaningful HTTP errors would simplify debugging and play better with production log aggregation. 【F:app/parser.py†L124-L127】
- IPv6 addresses skip port extraction by setting `port = None`, yet later history writes interpolate `{port}`, yielding the literal string `None`. Consider storing explicit empty strings or retaining the socket pair to avoid confusing UI consumers. 【F:app/parser.py†L57-L106】

## Routes (`app/routes.py`)
- Flask app is instantiated with `DEBUG=True` and `PROPAGATE_EXCEPTIONS=True`, which should be development-only flags; in production they leak stack traces and disable error handling middleware. 【F:app/routes.py†L10-L12】
- `/api/server-status` calls `parse_status_log()` to compute totals even though `/api/clients` already does so, doubling file I/O every poll. Cache the client snapshot per request cycle or refactor totals into the client endpoint payload. 【F:app/routes.py†L60-L86】
- History parsing insists on non-empty RX/TX values, so "session started" lines (written with empty placeholders) are dropped. If the UI needs to show active-but-not-closed sessions or connection attempts, this should be relaxed. 【F:app/routes.py†L38-L55】
- Endpoint error reporting uses bare `print` calls; switch to `logging` and return structured error payloads so the frontend can surface specific failures. 【F:app/routes.py†L28-L33】【F:app/routes.py†L55-L58】【F:app/routes.py†L71-L78】

## General
- There is no validation around `active_sessions.json`: when the file becomes corrupted (e.g., truncated by concurrent writes) `json.load` will raise and clear all active state. Adding atomic writes (temporary files + rename) and schema validation would prevent data loss. 【F:app/parser.py†L18-L25】
- Add automated tests for parser edge cases (IPv6, reconnects, malformed rows). Currently there are no tests to guard against regressions when log formats change.
