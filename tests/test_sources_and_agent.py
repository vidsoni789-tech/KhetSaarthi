"""Unit tests for Phase 2: sources adapter hardening and agent orchestrator telemetry."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.agent import run_advisory
from core.sources import (
    COMMODITY_MAP,
    geocode_location,
    get_mandi_prices,
    normalize_commodity_name,
    resolve_data_gov_api_key,
)


def test_resolve_api_key_empty_string_bypasses_env(monkeypatch):
    """Passing api_key='' must explicitly bypass DATA_GOV_API_KEY in .env."""
    monkeypatch.setenv("DATA_GOV_API_KEY", "real_key_in_environment_12345")

    # Explicit empty string: MUST NOT fall back to env
    resolved = resolve_data_gov_api_key(api_key="")
    assert resolved == ""

    # None passed: MUST fall back to env
    resolved_env = resolve_data_gov_api_key(api_key=None)
    assert resolved_env == "real_key_in_environment_12345"


def test_mandi_prices_empty_key_returns_unconfigured(monkeypatch):
    """get_mandi_prices(..., api_key='') strictly returns unconfigured without network call."""
    monkeypatch.setenv("DATA_GOV_API_KEY", "super_secret_env_key")

    result = get_mandi_prices("Maharashtra", "Soybean", api_key="")
    assert result["connected"] is False
    assert result["status"] == "unconfigured"
    assert result["records"] == []
    assert "DATA_GOV_API_KEY is not configured" in result["message"]


def test_mandi_resource_lists_message_degrades_gracefully():
    """When data.gov.in returns {'message': 'Resource lists'}, return degraded dict without raising RuntimeError."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": "Resource lists"}

    with patch("requests.Session.get", return_value=mock_resp):
        result = get_mandi_prices("Maharashtra", "Soyabean", api_key="test_key_abc")
        assert result["connected"] is False
        assert result["status"] == "degraded"
        assert result["records"] == []
        assert "Resource lists" in result["reason"]
        assert "Resource lists" in result["message"]


def test_mandi_timeout_degrades_gracefully():
    """When data.gov.in times out after 4.5s, catch ReadTimeout and return degraded dict."""
    with patch("requests.Session.get", side_effect=requests.exceptions.ReadTimeout("Read timed out")):
        result = get_mandi_prices("Maharashtra", "Soyabean", api_key="test_key_abc")
        assert result["connected"] is False
        assert result["status"] == "degraded"
        assert result["records"] == []
        assert "timeout" in result["reason"].lower()


def test_mandi_district_fallback_to_state():
    """When district query has 0 records, automatically fallback to state level query."""
    mock_empty_district = MagicMock()
    mock_empty_district.ok = True
    mock_empty_district.json.return_value = {"records": []}

    mock_state_results = MagicMock()
    mock_state_results.ok = True
    mock_state_results.json.return_value = {
        "records": [
            {
                "market": "Lasalgaon",
                "district": "Nashik",
                "commodity": "Soyabean",
                "variety": "Yellow",
                "arrival_date": "31/10/2026",
                "min_price": "4200",
                "max_price": "4600",
                "modal_price": "4450",
            }
        ]
    }

    # First call (district) returns empty; second call (state fallback) returns records
    with patch("requests.Session.get", side_effect=[mock_empty_district, mock_state_results]):
        result = get_mandi_prices("Maharashtra", "Soybean", api_key="test_key", district="Nashik")
        assert result["connected"] is True
        assert result["status"] == "success"
        assert result["query_level"] == "state"
        assert len(result["records"]) == 1
        assert result["records"][0]["Market"] == "Lasalgaon"
        assert result["records"][0]["Modal price (₹/quintal)"] == "4450"


def test_commodity_normalization():
    """Ensure standard crops map cleanly to AGMARKNET official commodity names."""
    assert normalize_commodity_name("Soybean") == "Soyabean"
    assert normalize_commodity_name("Tur / Pigeon Pea") == "Arhar (Tur/Red Gram)(Whole)"
    assert normalize_commodity_name("Rice") == "Paddy(Dhan)(Common)"
    assert normalize_commodity_name("Cotton") == "Cotton"
    assert normalize_commodity_name("UnknownCrop") == "UnknownCrop"


def test_geocoding_nashik_maharashtra():
    """Test geocoding for 'Nashik, Maharashtra' resolves with proper coordinates and metadata."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "results": [
            {
                "name": "Nashik",
                "latitude": 19.9973,
                "longitude": 73.7910,
                "country": "India",
                "admin1": "Maharashtra",
                "admin2": "Nashik",
                "population": 1486053,
                "timezone": "Asia/Kolkata",
            }
        ]
    }

    with patch("requests.Session.get", return_value=mock_resp):
        place = geocode_location("Nashik, Maharashtra")
        assert place["name"] == "Nashik"
        assert place["admin1"] == "Maharashtra"
        assert place["admin2"] == "Nashik"
        assert 19.0 <= place["latitude"] <= 21.0
        assert 73.0 <= place["longitude"] <= 74.5


def test_geocoding_smart_fallback_for_compound_location():
    """When compound query like 'Lasalgaon, Nashik' returns 0 results, retry with primary token."""
    mock_empty = MagicMock()
    mock_empty.ok = True
    mock_empty.json.return_value = {"results": []}

    mock_lasalgaon = MagicMock()
    mock_lasalgaon.ok = True
    mock_lasalgaon.json.return_value = {
        "results": [
            {
                "name": "Lāsalgaon",
                "latitude": 20.1427,
                "longitude": 74.2395,
                "country": "India",
                "admin1": "Maharashtra",
                "admin2": "Nashik",
                "population": 17360,
                "timezone": "Asia/Kolkata",
            }
        ]
    }

    with patch("requests.Session.get", side_effect=[mock_empty, mock_lasalgaon]):
        place = geocode_location("Lasalgaon, Nashik")
        assert place["name"] == "Lāsalgaon"
        assert place["admin1"] == "Maharashtra"
        assert place["admin2"] == "Nashik"


def test_agent_execution_trace_telemetry():
    """Agent orchestrator produces rich telemetry with latency_ms and evidence for all steps."""
    mock_geo = {
        "name": "Nashik",
        "admin1": "Maharashtra",
        "admin2": "Nashik",
        "country": "India",
        "latitude": 19.9973,
        "longitude": 73.7910,
        "timezone": "Asia/Kolkata",
        "candidates": [],
    }
    mock_weather = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"],
            "precipitation_sum": [0.0, 1.2, 0.0, 0.0, 0.0, 0.0, 0.0],
            "precipitation_probability_max": [10, 45, 10, 5, 5, 0, 0],
            "temperature_2m_max": [30.0, 29.5, 30.5, 31.0, 31.5, 30.0, 30.0],
            "temperature_2m_min": [19.0, 18.5, 18.0, 18.0, 19.0, 19.5, 19.0],
            "wind_speed_10m_max": [11.0, 12.5, 10.0, 9.0, 8.5, 10.0, 11.0],
            "et0_fao_evapotranspiration": [4.0, 3.8, 4.2, 4.1, 4.3, 4.0, 4.0],
        }
    }

    with patch("core.agent.geocode_location", return_value=mock_geo), \
         patch("core.agent.get_weather_forecast", return_value=mock_weather):
        report = run_advisory(
            location_text="Nashik, Maharashtra",
            crop="Soybean",
            stage="Flowering",
            language="mr",
            mandi_api_key="",  # Test explicit unconfigured fallback
        )

        assert "total_latency_ms" in report
        assert report["total_latency_ms"] >= 1

        steps = {event["step"]: event for event in report["agent_log"]}
        assert "plan" in steps
        assert "geocode" in steps
        assert "weather" in steps
        assert "mandi" in steps
        assert "risk_engine" in steps
        assert "validation" in steps

        # Check mandi partial_fallback
        assert steps["mandi"]["status"] == "partial_fallback"
        assert "partial fallback" in steps["mandi"]["detail"].lower()

        # Check telemetry fields on every step
        for s_name, s_event in steps.items():
            assert "latency_ms" in s_event, f"Missing latency_ms in {s_name}"
            assert isinstance(s_event["latency_ms"], int)
            assert "evidence" in s_event, f"Missing evidence in {s_name}"
            assert s_event["evidence"], f"Empty evidence in {s_name}"

