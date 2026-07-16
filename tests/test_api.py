import os
import sys
from fastapi.testclient import TestClient

# Ensure scripts directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from api import (  # noqa: E402
    FALLBACK_SCAD,
    _caption_to_scad,
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


# ---------------------------------------------------------------------------
# Image caption → OpenSCAD heuristic conversion
# ---------------------------------------------------------------------------

def test_caption_house():
    code = _caption_to_scad("a house with a red roof")
    assert "cube" in code
    assert "cylinder" in code  # house has a roof

def test_caption_car():
    code = _caption_to_scad("a red car on the road")
    assert "cube" in code
    assert "cylinder" in code  # car has wheels

def test_caption_tree():
    code = _caption_to_scad("a tall tree in the forest")
    assert "cylinder" in code  # trunk
    assert "sphere" in code or "cylinder" in code  # foliage

def test_caption_person():
    code = _caption_to_scad("a person standing")
    assert "cylinder" in code
    assert "sphere" in code  # head

def test_caption_unknown_not_sphere():
    """The key bug fix: unknown objects should NOT produce the old sphere fallback."""
    code = _caption_to_scad("something completely random and unknown")
    assert "sphere(r=10)" not in code  # must NOT be the old fallback

def test_caption_variety():
    """Different captions should produce different shapes (not all the same sphere)."""
    codes = set()
    for cap in ["a house", "a car", "a tree", "a bottle", "a cat", "a phone"]:
        codes.add(_caption_to_scad(cap))
    assert len(codes) >= 4  # at least 4 unique shapes from 6 captions
