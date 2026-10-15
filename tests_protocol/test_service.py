from fastapi.testclient import TestClient

from evolving_soul.keyring_store import MemoryKeyStore
from evolving_soul.service import create_app
from evolving_soul.vault import SoulVault


def test_local_control_plane_bootstrap_and_route_boundaries(tmp_path):
    vault = SoulVault.create(tmp_path / "vault", key_store=MemoryKeyStore())
    app = create_app(vault)
    client = TestClient(app)
    assert client.get("/v1/health").json()["vault"] == "unlocked"
    assert (
        client.post(
            "/v1/bootstrap/register/options", json={"code": "wrong", "owner_name": "Owner"}
        ).status_code
        == 401
    )
    paths = {route.path for route in app.routes}
    assert "/v1/proposals/{proposal_id}/approve" in paths
    assert "/v1/recovery" not in paths
    assert "/v1/plugin/approve" not in paths
    vault.lock()
