import importlib
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    history_path = tmp_path / "history.log"

    monkeypatch.setenv("OPENVPN_HISTORY_LOG", str(history_path))

    from app import config

    importlib.reload(config)

    from app import routes

    importlib.reload(routes)

    routes.app.config.update(TESTING=True)
    client = routes.app.test_client()

    return client, history_path


def test_api_history_includes_vpn_ip_versions(app_client):
    client, history_path = app_client

    history_path.write_text(
        "\n".join(
            [
                "2024-01-01 09:00:00,alice,198.51.100.10,s1,1.0,2.0,10.8.0.5,443,2024-01-01 10:00:00",
                "2024-01-02 09:00:00,bob,203.0.113.5,s2,3.0,4.0,10.9.0.2,1194,2024-01-02 11:00:00,10.9.0.2,2001:db8::abcd",
                "2024-01-03 09:00:00,carol,2001:db8::10,s3,5.0,6.0,2001:db8::ffff,1194,2024-01-03 10:00:00",
            ]
        )
    )

    response = client.get("/api/history")
    assert response.status_code == 200

    entries = json.loads(response.data)
    assert len(entries) == 3

    alice, bob, carol = entries

    assert alice["vpn_ip"] == "10.8.0.5"
    assert alice["vpn_ipv4"] == "10.8.0.5"
    assert alice["vpn_ipv6"] == ""

    assert bob["vpn_ip"] == "10.9.0.2"
    assert bob["vpn_ipv4"] == "10.9.0.2"
    assert bob["vpn_ipv6"] == "2001:db8::abcd"

    assert carol["vpn_ip"] == "2001:db8::ffff"
    assert carol["vpn_ipv4"] == ""
    assert carol["vpn_ipv6"] == "2001:db8::ffff"
