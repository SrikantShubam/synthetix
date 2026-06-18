from pathlib import Path

from fastapi.testclient import TestClient

from synthetix.web.app import create_app


def test_minimal_ui_exposes_four_workflow_views(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    assert client.get("/").status_code == 200
    assert "New run" in client.get("/").text
    assert client.get("/runs/demo/preflight").status_code == 200
    assert client.get("/runs/demo/status").status_code == 200
    assert client.get("/runs/demo/results").status_code == 200
