"""Unit and integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_status():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["launch_date"] == "March 11, 2025"
    assert data["bands_count"] == 6
    assert data["indexed_candidates_count"] >= 5


def test_list_candidates():
    response = client.get("/api/v1/candidates")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 5
    first = data["items"][0]
    # Check all 9 frontend requirements exist in the response
    assert "candidate_id" in first
    assert "ra" in first
    assert "dec" in first
    assert "observation_dates" in first
    assert "bands_observed" in first
    assert "displacement_arcsec" in first
    assert "delta_brightness_mag" in first
    assert "displacement_uncertainty_arcsec" in first
    assert "quality_indicators" in first
    assert "scientific_interpretation" in first
    assert "validation_status" in first


def test_filter_candidates_by_ice():
    response = client.get("/api/v1/candidates?ice_molecule=H2O")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["candidate_id"] == "SPX-J0439+2545" for c in data["items"])


def test_filter_candidates_by_displacement():
    response = client.get("/api/v1/candidates?min_displacement_sigma=3.0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["candidate_id"] == "SPX-J1802-2341" for c in data["items"])


def test_get_candidate_detail():
    response = client.get("/api/v1/candidates/SPX-J1802-2341")
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] == "SPX-J1802-2341"
    assert len(data["spectrum"]) == 6
    assert "epoch_1" in data["cutout_thumbnails"]


def test_update_candidate_validation():
    payload = {
        "validation_status": "Confirmed",
        "user_notes": "Triage verified by test runner."
    }
    response = client.post("/api/v1/candidates/SPX-J1802-2341/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "Confirmed"
    assert data["user_notes"] == "Triage verified by test runner."


def test_spectral_bands():
    response = client.get("/api/v1/spectral/bands")
    assert response.status_code == 200
    data = response.json()
    assert "BAND_1" in data
    assert "BAND_6" in data
    assert data["BAND_6"]["resolving_power"] == 128
    assert data["BAND_5"]["resolving_power"] == 112
    assert data["BAND_4"]["resolving_power"] == 35


def test_observations_cutout():
    # Fetch first observation ID
    obs_resp = client.get("/api/v1/observations")
    assert obs_resp.status_code == 200
    obs_list = obs_resp.json()
    assert len(obs_list) > 0
    obs_id = obs_list[0]["observation_id"]

    cutout_resp = client.get(f"/api/v1/observations/{obs_id}/cutout?ra=270.5&dec=-23.6&size_px=32")
    assert cutout_resp.status_code == 200
    cutout_data = cutout_resp.json()
    assert cutout_data["data_uri"].startswith("data:image/png;base64,")
