import os
import tempfile
from typing import Dict, Any

from fastapi.testclient import TestClient

# Ensure the app uses an isolated temporary SQLite database during tests
# This avoids clashing with any developer machine DB and keeps tests hermetic.
tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db.name}"

from src.api.main import app  # noqa: E402  (import after setting env)
from src.db.seed import seed  # noqa: E402

client = TestClient(app)


def _create_requirement(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = client.post("/api/v1/requirements", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_estimate(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = client.post("/api/v1/estimates", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_item(estimate_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = client.post(f"/api/v1/estimates/{estimate_id}/items", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health_check():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert data.get("message") == "Healthy"


def test_requirement_crud_flow():
    # Create
    created = _create_requirement(
        {
            "title": "Login feature",
            "description": "User should be able to login",
            "priority": "High",
            "status": "draft",
        }
    )
    req_id = created["id"]
    assert created["title"] == "Login feature"
    assert created["status"] == "draft"

    # Read (get by id)
    r = client.get(f"/api/v1/requirements/{req_id}")
    assert r.status_code == 200
    fetched = r.json()
    assert fetched["id"] == req_id

    # List
    r = client.get("/api/v1/requirements")
    assert r.status_code == 200
    items = r.json()
    assert any(i["id"] == req_id for i in items)

    # Update
    r = client.patch(f"/api/v1/requirements/{req_id}", json={"status": "approved"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["status"] == "approved"

    # Delete
    r = client.delete(f"/api/v1/requirements/{req_id}")
    assert r.status_code == 204

    # Not found after delete
    r = client.get(f"/api/v1/requirements/{req_id}")
    assert r.status_code == 404


def test_reference_endpoints_rate_cards_and_complexity_defaults():
    # Seed baseline reference data
    seed()

    # Rate cards list non-empty after seed
    r = client.get("/api/v1/reference/rates")
    assert r.status_code == 200
    rates = r.json()
    assert isinstance(rates, list)
    assert len(rates) >= 1
    rate_id = rates[0]["id"]

    # Get one
    r = client.get(f"/api/v1/reference/rates/{rate_id}")
    assert r.status_code == 200

    # Update rate card
    r = client.patch(f"/api/v1/reference/rates/{rate_id}", json={"currency": "USD"})
    assert r.status_code == 200
    assert r.json()["currency"] == "USD"

    # Create new rate card
    r = client.post(
        "/api/v1/reference/rates",
        json={"role": "architect", "hourly_rate": 150.0, "currency": "USD"},
    )
    assert r.status_code == 201
    new_rate = r.json()
    assert new_rate["role"] == "architect"

    # Delete newly created rate card
    r = client.delete(f"/api/v1/reference/rates/{new_rate['id']}")
    assert r.status_code == 204

    # Complexity defaults list non-empty after seed
    r = client.get("/api/v1/reference/complexity-defaults")
    assert r.status_code == 200
    cds = r.json()
    assert isinstance(cds, list)
    assert len(cds) >= 1
    cd_id = cds[0]["id"]

    # Get one
    r = client.get(f"/api/v1/reference/complexity-defaults/{cd_id}")
    assert r.status_code == 200

    # Update one
    r = client.patch(f"/api/v1/reference/complexity-defaults/{cd_id}", json={"default_hours": 7.5})
    assert r.status_code == 200
    assert float(r.json()["default_hours"]) == 7.5

    # Create new defaults
    r = client.post(
        "/api/v1/reference/complexity-defaults",
        json={"item_type": "ops", "complexity": "medium", "default_hours": 9.0},
    )
    assert r.status_code == 201
    created = r.json()
    assert created["item_type"] == "ops"

    # Delete newly created defaults
    r = client.delete(f"/api/v1/reference/complexity-defaults/{created['id']}")
    assert r.status_code == 204


def test_estimates_items_and_recalc():
    # Ensure reference data exists for cost calculation
    seed()

    # Create a requirement to associate (optional)
    req = _create_requirement(
        {"title": "Checkout flow", "description": "Implement checkout", "priority": "High", "status": "draft"}
    )

    # Create an estimate
    est = _create_estimate({"name": "Checkout Estimate", "requirement_id": req["id"], "notes": "Initial pass"})
    estimate_id = est["id"]

    # No items initially
    r = client.get(f"/api/v1/estimates/{estimate_id}/items")
    assert r.status_code == 200
    assert r.json() == []

    # Create a few items (some with 0 hours to use defaults)
    item1 = _create_item(
        estimate_id,
        {"estimate_id": estimate_id, "name": "Frontend Cart UI", "item_type": "frontend", "complexity": "medium", "hours": 0.0},
    )
    item2 = _create_item(
        estimate_id,
        {"estimate_id": estimate_id, "name": "Backend Order API", "item_type": "backend", "complexity": "high", "hours": 12.5},
    )

    # List items
    r = client.get(f"/api/v1/estimates/{estimate_id}/items")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    ids = {i["id"] for i in items}
    assert item1["id"] in ids and item2["id"] in ids

    # Recalc totals
    r = client.post(f"/api/v1/estimates/{estimate_id}/recalc")
    assert r.status_code == 200, r.text
    totals = r.json()
    assert totals["estimate_id"] == estimate_id
    assert "currency" in totals
    assert totals["total_hours"] >= 0.0
    assert totals["total_cost"] >= 0.0
    assert isinstance(totals["by_role"], dict)
    assert isinstance(totals["items"], list)
    assert len(totals["items"]) == 2

    # Update one item
    item1_id = item1["id"]
    r = client.patch(f"/api/v1/estimates/items/{item1_id}", json={"hours": 5.0})
    assert r.status_code == 200
    assert float(r.json()["hours"]) == 5.0

    # Get one item
    r = client.get(f"/api/v1/estimates/items/{item1_id}")
    assert r.status_code == 200

    # Delete one item
    r = client.delete(f"/api/v1/estimates/items/{item1_id}")
    assert r.status_code == 204

    # Delete estimate
    r = client.delete(f"/api/v1/estimates/{estimate_id}")
    assert r.status_code == 204
