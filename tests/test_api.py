"""HTTP 接口层：单工况、批量、预置算例与错误返回。"""

import pytest

from app.presets import SOFTENING_BED_CONDITION as BASE
from app.server import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_single_run_endpoint(client):
    resp = client.post("/api/v1/breakthrough/run", json=BASE)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["saturated"] is True
    assert len(data["time"]) == data["n_points"]
    assert data["breakthrough_time"] is not None
    assert data["total_adsorbed"] == pytest.approx(
        data["theoretical_capacity"], rel=0.01
    )


def test_single_run_validation_error_carries_reasons(client):
    resp = client.post("/api/v1/breakthrough/run", json={**BASE, "C0": 0})
    assert resp.status_code == 400
    error = resp.get_json()["error"]
    assert any("C0" in reason for reason in error["reasons"])


def test_single_run_rejects_non_json_body(client):
    resp = client.post(
        "/api/v1/breakthrough/run", data="not json", content_type="text/plain"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["reasons"]


def test_batch_endpoint(client):
    payload = {
        "runs": [
            BASE,
            {**BASE, "Q": BASE["Q"] * 2.0},
            {**BASE, "m": -1.0},
        ]
    }
    resp = client.post("/api/v1/breakthrough/batch", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 3
    first, second, third = data["results"]
    assert first["ok"] is True and second["ok"] is True
    assert third["ok"] is False
    assert any("m" in r for r in third["error"]["reasons"])
    # 各工况互不影响：流量加倍者穿透更早
    assert (
        second["result"]["breakthrough_time"]
        < first["result"]["breakthrough_time"]
    )


def test_batch_endpoint_rejects_empty_dataset(client):
    resp = client.post("/api/v1/breakthrough/batch", json={"runs": []})
    assert resp.status_code == 400


def test_softening_preset_endpoint(client):
    resp = client.get("/api/v1/presets/softening")
    assert resp.status_code == 200
    payload = resp.get_json()
    result = payload["result"]
    assert result["saturated"] is True
    bt = result["breakthrough_time"]
    pre = [
        c
        for t, c in zip(result["time"], result["relative_concentration"])
        if t < bt
    ]
    assert max(pre) <= result["threshold"]
