import os
import sys
from fastapi.testclient import TestClient

# Ensure scripts directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from api import (  # noqa: E402
    FALLBACK_SCAD,
    app,
    find_shape_in_library,
    sanitize_scad,
)

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shape library
# ---------------------------------------------------------------------------

def test_library_returns_known_shape():
    code = find_shape_in_library("please make me a chair")
    assert code is not None
    assert "cube" in code or "cylinder" in code

def test_library_is_case_insensitive():
    assert find_shape_in_library("A Big ROCKET") is not None

# ---------------------------------------------------------------------------
# API endpoints that need no external services
# ---------------------------------------------------------------------------

def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()

def test_route_parametric_prompt():
    resp = client.post("/route", json={"prompt": "a simple box 20mm wide"})
    assert resp.status_code == 200
    assert resp.json()["path"] == "parametric"

def test_route_ai_prompt():
    resp = client.post("/route", json={"prompt": "a realistic organic dragon"})
    assert resp.status_code == 200
    assert resp.json()["path"] == "ai_generator"

def test_route_reports_scores():
    resp = client.post("/route", json={"prompt": "abstract futuristic spaceships"})
    body = resp.json()
    assert body["ai_score"] >= 3
    assert body["parametric_score"] == 0
