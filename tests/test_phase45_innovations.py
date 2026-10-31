"""Unit tests for Phase 4.5 Innovations:
- Spatial Mandi Arbitrage & Spoilage Value-at-Risk (VaR in ₹)
- FAO-56 Crop Water Balance & Precision Drip Irrigation (hours/acre)
- Counterfactual Weather Stress-Test Modifier
- 6-Step Autonomous Orchestrator Pipeline
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from core.economics import (
    compute_crop_water_balance,
    evaluate_mandi_arbitrage_and_hold_risk,
    estimate_road_distance_km,
    haversine_distance_km,
    apply_weather_stress_deltas,
    MAHARASHTRA_DISTRICT_COORDS,
)
from core.agent import run_advisory, run_khetsaarthi_agent


def test_haversine_and_road_distance():
    """Verify Haversine distance and road tortuosity factor between Nashik and Pune."""
    nashik_pt = MAHARASHTRA_DISTRICT_COORDS["nashik"]
    pune_pt = MAHARASHTRA_DISTRICT_COORDS["pune"]

    crow_km = haversine_distance_km(nashik_pt, pune_pt)
    assert 150.0 <= crow_km <= 180.0

    road_km = estimate_road_distance_km("Nashik", nashik_pt, "Pune")
    assert road_km > crow_km
    assert road_km == pytest.approx(crow_km * 1.25, abs=0.5)

    # Intra-district defaults to 25 km
    intra_km = estimate_road_distance_km("Nashik", nashik_pt, "Nashik")
    assert intra_km == 25.0


def test_mandi_spatial_arbitrage_and_net_ranking():
    """Markets must be ranked by Net Take-Home Revenue after road transport deduction."""
    mandi_data = {
        "connected": True,
        "status": "success",
        "records": [
            {
                "Market": "Lasalgaon",
                "District": "Nashik",
                "Modal price (₹/quintal)": "4400",
                "Date": "29/10/2026",
            },
            {
                "Market": "Baramati",
                "District": "Pune",
                "Modal price (₹/quintal)": "4750",  # Higher raw price, but ~200km transport away
                "Date": "29/10/2026",
            },
            {
                "Market": "Local Taluka",
                "District": "Nashik",
                "Modal price (₹/quintal)": "4450",
                "Date": "29/10/2026",
            },
        ],
    }

    result = evaluate_mandi_arbitrage_and_hold_risk(
        mandi_data=mandi_data,
        origin_district="Nashik",
        origin_coords=(19.9975, 73.7898),
        crop="Soybean",
        stage="Vegetative",
        weather_risk_score=10,
        forecast_rain_mm=0.0,
        forecast_max_rain_prob=10.0,
        lot_quintals=20.0,
        language="en",
    )

    assert result["has_market_data"] is True
    assert result["lot_quintals"] == 20.0
    rankings = result["market_rankings"]
    assert len(rankings) == 3

    # Confirm net take-home ranking: Local Taluka (4450 - 37.5 = 4412.5) vs Lasalgaon (4400 - 37.5 = 4362.5)
    # vs Baramati (4750 - ~310 = ~4440)
    for i in range(len(rankings) - 1):
        assert rankings[i]["net_take_home_inr"] >= rankings[i + 1]["net_take_home_inr"]

    assert result["best_market_net_revenue"] > 0
    assert result["recommendation_code"] == "SAFE_TO_HOLD"
    assert result["spoilage_var_inr"] == 0.0


def test_harvest_unseasonal_rain_spoilage_var():
    """Unseasonal rain during Maturity/Harvest triggers SELL_NOW with positive ₹ at Risk."""
    mandi_data = {
        "connected": True,
        "status": "cached_snapshot",
        "records": [
            {
                "Market": "Nashik",
                "District": "Nashik",
                "Modal price (₹/quintal)": "4500",
                "Date": "28/10/2026",
            }
        ],
    }

    result = evaluate_mandi_arbitrage_and_hold_risk(
        mandi_data=mandi_data,
        origin_district="Nashik",
        origin_coords=(19.9975, 73.7898),
        crop="Soybean",
        stage="Maturity / Harvest",
        weather_risk_score=65,
        forecast_rain_mm=18.5,  # Heavy unseasonal rain
        forecast_max_rain_prob=85.0,
        lot_quintals=30.0,
        language="mr",
    )

    assert result["recommendation_code"] == "SELL_NOW"
    assert result["spoilage_risk_pct"] >= 10.0
    expected_var = round((4500 * 30.0) * (result["spoilage_risk_pct"] / 100.0), 2)
    assert result["spoilage_var_inr"] == expected_var
    assert "पावसापूर्वी तात्काळ विक्री करा" in result["localized_recommendation"]


def test_fao56_crop_water_balance_deficit():
    """Test FAO-56 ETc, effective rainfall, and precision drip irrigation calculation."""
    daily_dates = ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"]
    daily_et0 = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]  # 35.0 mm total ET0
    daily_rain = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # 0 rain

    # Flowering Soybean: Kc = 1.15
    result = compute_crop_water_balance(
        daily_dates=daily_dates,
        daily_et0=daily_et0,
        daily_rain=daily_rain,
        crop="Soybean",
        stage="Flowering",
        language="hi",
    )

    assert result["kc"] == 1.15
    # Total ETc = 35.0 * 1.15 = 40.25 mm
    assert result["total_etc_mm"] == pytest.approx(40.25, abs=0.1)
    assert result["effective_rain_mm"] == 0.0
    assert result["net_irrigation_deficit_mm"] == pytest.approx(40.25, abs=0.1)

    # 40.25 mm * 4046.86 L/acre = 162,886 Liters
    assert result["liters_per_acre_needed"] > 160000
    # 162,886 / 16,000 = ~10.2 hours drip per acre
    assert result["drip_hours_per_acre"] == pytest.approx(10.2, abs=0.2)
    assert "मिमी नमी की कमी" in result["localized_verdict"]


def test_fao56_crop_water_balance_zero_deficit_wet_spell():
    """When effective rain exceeds ETc, deficit is 0 and verdict advises zero irrigation."""
    daily_dates = ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"]
    daily_et0 = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0]  # 21.0 mm total ET0
    daily_rain = [10.0, 15.0, 20.0, 5.0, 0.0, 0.0, 0.0]  # 50 mm rain -> 40 mm eff rain

    result = compute_crop_water_balance(
        daily_dates=daily_dates,
        daily_et0=daily_et0,
        daily_rain=daily_rain,
        crop="Soybean",
        stage="Sowing",  # Kc = 0.40 -> ETc = 8.4 mm
        language="mr",
    )

    assert result["kc"] == 0.40
    assert result["effective_rain_mm"] == pytest.approx(40.0, abs=0.1)
    assert result["net_irrigation_deficit_mm"] == 0.0
    assert result["drip_hours_per_acre"] == 0.0
    assert "पाणी देण्याची गरज नाही" in result["localized_verdict"]


def test_apply_weather_stress_deltas_preserves_baseline():
    """Counterfactual modifier creates an isolated copy and adjusts deltas correctly."""
    base_weather = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "precipitation_sum": [2.0, 3.0, 1.0],
            "temperature_2m_max": [30.0, 31.0, 29.0],
            "wind_speed_10m_max": [10.0, 12.0, 8.0],
            "precipitation_probability_max": [40, 50, 30],
        }
    }

    modified = apply_weather_stress_deltas(
        weather=base_weather,
        rain_delta_mm=30.0,
        temp_delta_c=5.0,
        wind_delta_kmh=15.0,
    )

    # Baseline untouched
    assert base_weather["daily"]["precipitation_sum"] == [2.0, 3.0, 1.0]
    assert base_weather["daily"]["temperature_2m_max"] == [30.0, 31.0, 29.0]
    assert base_weather["daily"]["wind_speed_10m_max"] == [10.0, 12.0, 8.0]

    # Modified values shifted
    mod_daily = modified["daily"]
    assert mod_daily["temperature_2m_max"] == [35.0, 36.0, 34.0]
    assert mod_daily["wind_speed_10m_max"] == [25.0, 27.0, 23.0]
    assert mod_daily["precipitation_sum"][1] > 3.0
    assert mod_daily["precipitation_probability_max"][1] > 50


def test_agent_orchestrator_includes_economics_and_water():
    """Agent execution graph includes 6-step plan with economics_and_water step."""
    mock_geo = MagicMock()
    mock_geo.ok = True
    mock_geo.json.return_value = {
        "results": [
            {
                "name": "Nashik",
                "latitude": 19.9973,
                "longitude": 73.7910,
                "country": "India",
                "admin1": "Maharashtra",
                "admin2": "Nashik",
            }
        ]
    }

    mock_weather = MagicMock()
    mock_weather.ok = True
    mock_weather.json.return_value = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"],
            "precipitation_sum": [1.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0],
            "temperature_2m_max": [31.0, 32.0, 30.0, 31.0, 30.0, 31.0, 32.0],
            "temperature_2m_min": [18.0, 19.0, 18.0, 17.0, 18.0, 19.0, 18.0],
            "wind_speed_10m_max": [12.0, 14.0, 11.0, 15.0, 10.0, 11.0, 12.0],
            "precipitation_probability_max": [30, 10, 10, 45, 10, 10, 10],
            "et0_fao_evapotranspiration": [4.5, 4.8, 4.6, 4.2, 4.5, 4.7, 4.8],
        }
    }

    with patch("requests.Session.get", side_effect=[mock_geo, mock_weather]):
        report = run_advisory(
            location_text="Nashik, Maharashtra",
            crop="Soybean",
            stage="Flowering",
            language="mr",
            mandi_api_key="",
            lot_quintals=25.0,
        )

        assert "economics_and_water" in report
        econ_step = next((s for s in report["agent_log"] if s["step"] == "economics_and_water"), None)
        assert econ_step is not None
        assert econ_step["status"] == "completed"

        econ_water = report["economics_and_water"]
        assert econ_water["lot_quintals"] == 25.0
        assert "water_balance" in econ_water
        assert "mandi_arbitrage" in econ_water
        assert econ_water["water_balance"]["net_irrigation_deficit_mm"] > 0
        assert econ_water["water_balance"]["drip_hours_per_acre"] > 0

        # Verify alias works identically
        assert run_khetsaarthi_agent == run_advisory

