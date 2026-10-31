"""Test suite for Module 1 (Irrigation Advisory) and Module 2 (Pesticide Spray Advisory).

Verifies the 12 required agronomic scenarios:
1. High rainfall forecast (>= 40 mm) and soil wet -> DEFER AND RECHECK
2. No rain forecast and soil dry -> IRRIGATION MAY BE NEEDED
3. Rainfall forecast missing (None) -> INSUFFICIENT DATA (no invented rainfall)
4. Reference ET0 missing (None) -> INSUFFICIENT DATA (no invented ET0)
5. Different crops select different verified Kc parameters (Rice vs Soybean)
6. Different growth stages affect irrigation calculation (Soybean Flowering vs Sowing)
7. Same weather evaluated independently by both engines
8. Missing wind data does NOT create a SAFE spraying result
9. Missing rainfall probability does NOT produce a guaranteed suitable spraying window
10. Unverified pesticide dosage is NEVER displayed (directs to CIBRC leaflet / KVK)
11. English, Hindi, and Marathi outputs work across both engines
12. All advisory sections consume the same current forecast report payload
"""

import pytest
from core.crop_config import get_crop_config, get_kc, get_cibrc_label
from core.irrigation import plan_7day_irrigation_schedule, evaluate_daily_irrigation_need
from core.pesticide_spray import assess_pesticide_weather_suitability, evaluate_daily_spray_weather, verify_pesticide_label
from core.agent import run_advisory


def _make_mock_forecast(days=7, rain=0.0, rain_prob=10.0, temp_max=32.0, temp_min=22.0, wind=8.0, et0=4.5):
    """Helper to generate a clean 7-day forecast dataset."""
    rows = []
    base_dates = ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"]
    for i in range(days):
        rows.append({
            "Date": base_dates[i],
            "Rain (mm)": rain if isinstance(rain, (int, float)) else rain[i],
            "Rain probability (%)": rain_prob if isinstance(rain_prob, (int, float)) else rain_prob[i],
            "Max temp (°C)": temp_max if isinstance(temp_max, (int, float)) else temp_max[i],
            "Min temp (°C)": temp_min if isinstance(temp_min, (int, float)) else temp_min[i],
            "Wind (km/h)": wind if isinstance(wind, (int, float)) else wind[i],
            "Reference ET₀ (mm)": et0 if isinstance(et0, (int, float)) else et0[i],
        })
    return rows


# 1. High rain forecast (>= 40mm) and soil wet -> DEFER AND RECHECK
def test_1_high_rain_and_soil_wet_defers_irrigation():
    forecast = _make_mock_forecast(rain=45.0, rain_prob=90.0, et0=4.0)
    result = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Flowering",
        soil_texture="Black Cotton / Vertisol",
        soil_moisture="wet",
        language="en",
    )
    assert result["overall_status"] == "DEFER AND RECHECK"
    assert result["daily_schedule"][0]["status"] == "DEFER AND RECHECK"
    assert "DEFER" in result["overall_verdict"]


# 2. No rain forecast and soil dry -> IRRIGATION MAY BE NEEDED
def test_2_no_rain_and_soil_dry_needs_irrigation():
    forecast = _make_mock_forecast(rain=0.0, rain_prob=5.0, et0=5.0)
    result = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Flowering",
        soil_texture="Loamy",
        soil_moisture="dry",
        language="en",
    )
    assert result["overall_status"] == "IRRIGATION MAY BE NEEDED"
    assert result["daily_schedule"][0]["status"] == "IRRIGATION MAY BE NEEDED"
    assert "IRRIGATION" in result["overall_verdict"]


# 3. Rainfall forecast missing (None) -> INSUFFICIENT DATA (no invented rainfall)
def test_3_missing_rainfall_returns_insufficient_data():
    forecast = _make_mock_forecast()
    for row in forecast:
        row["Rain (mm)"] = None

    result = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Flowering",
        soil_texture="Loamy",
        soil_moisture="dry",
        language="en",
    )
    assert result["overall_status"] == "INSUFFICIENT DATA"
    assert "INSUFFICIENT DATA" in result["overall_verdict"]
    assert any("Rainfall forecast missing" in issue for issue in result["data_issues"])


# 4. Reference ET0 missing (None) -> INSUFFICIENT DATA (no invented ET0)
def test_4_missing_et0_returns_insufficient_data():
    forecast = _make_mock_forecast()
    for row in forecast:
        row["Reference ET₀ (mm)"] = None

    result = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Flowering",
        soil_texture="Loamy",
        soil_moisture="dry",
        language="en",
    )
    assert result["overall_status"] == "INSUFFICIENT DATA"
    assert "INSUFFICIENT DATA" in result["overall_verdict"]
    assert any("ET₀ missing" in issue for issue in result["data_issues"])


# 5. Different crops select different verified Kc parameters (Rice vs Soybean)
def test_5_different_crops_select_different_kc():
    rice_sowing_kc = get_kc("Rice", "Sowing")
    soy_sowing_kc = get_kc("Soybean", "Sowing")
    assert rice_sowing_kc is not None
    assert soy_sowing_kc is not None
    assert rice_sowing_kc == 1.10  # Wetland / flooded nursery
    assert soy_sowing_kc == 0.40   # Initial soybean crop coefficient
    assert rice_sowing_kc != soy_sowing_kc


# 6. Different growth stages affect irrigation calculation (Soybean Flowering vs Sowing)
def test_6_different_stages_affect_water_demand():
    soy_sowing_kc = get_kc("Soybean", "Sowing")
    soy_flowering_kc = get_kc("Soybean", "Flowering")
    assert soy_sowing_kc == 0.40
    assert soy_flowering_kc == 1.15

    forecast = _make_mock_forecast(rain=0.0, et0=5.0)
    res_sowing = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Sowing",
        soil_moisture="dry",
    )
    res_flowering = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Flowering",
        soil_moisture="dry",
    )
    # At 5mm ET0, Soybean Sowing ETc is 5 * 0.40 = 2.0mm/day -> 14.0mm cumulative
    # Soybean Flowering ETc is 5 * 1.15 = 5.75mm/day -> 40.25mm cumulative
    assert res_sowing["cumulative_etc_mm"] < res_flowering["cumulative_etc_mm"]
    assert pytest.approx(res_sowing["cumulative_etc_mm"], 0.1) == 14.0
    assert pytest.approx(res_flowering["cumulative_etc_mm"], 0.1) == 40.25


# 7. Same weather evaluated independently by both engines
def test_7_independent_evaluation_same_weather():
    # Dry, sunny, calm day (Rain=0, Wind=6 km/h, ET0=5.0)
    # Soil is wet (e.g. from previous flood irrigation)
    forecast = _make_mock_forecast(rain=0.0, rain_prob=0.0, wind=6.0, temp_max=31.0, et0=5.0)

    irrigation_res = plan_7day_irrigation_schedule(
        forecast_rows=forecast,
        crop="Cotton",
        growth_stage="Vegetative",
        soil_moisture="wet",
        language="en",
    )
    pesticide_res = assess_pesticide_weather_suitability(
        forecast_rows=forecast,
        crop="Cotton",
        growth_stage="Vegetative",
        language="en",
    )

    # For soil irrigation: wet soil -> DEFER AND RECHECK
    assert irrigation_res["overall_status"] == "DEFER AND RECHECK"

    # For pesticide spraying: calm, warm, dry canopy -> SUITABLE WEATHER WINDOW
    assert pesticide_res["overall_status"] == "SUITABLE WEATHER WINDOW"
    assert pesticide_res["daily_schedule"][0]["status"] == "SUITABLE WEATHER WINDOW"


# 8. Missing wind data does NOT create a SAFE spraying result
def test_8_missing_wind_data_flags_unknown():
    forecast = _make_mock_forecast()
    forecast[0]["Wind (km/h)"] = None

    pesticide_res = assess_pesticide_weather_suitability(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Vegetative",
        language="en",
    )
    day0 = pesticide_res["daily_schedule"][0]
    assert day0["status"] == "UNKNOWN DUE TO MISSING INFORMATION"
    assert "Wind Speed" in day0["reason"] or "wind" in day0["reason"].lower()


# 9. Missing rainfall probability does NOT produce a guaranteed suitable window
def test_9_missing_rain_prob_flags_unknown():
    forecast = _make_mock_forecast()
    forecast[0]["Rain probability (%)"] = None

    pesticide_res = assess_pesticide_weather_suitability(
        forecast_rows=forecast,
        crop="Soybean",
        growth_stage="Vegetative",
        language="en",
    )
    day0 = pesticide_res["daily_schedule"][0]
    assert day0["status"] == "UNKNOWN DUE TO MISSING INFORMATION"
    assert "Rain Probability" in day0["reason"] or "rain" in day0["reason"].lower()


# 10. Unverified pesticide dosage is NEVER displayed
def test_10_unverified_pesticide_dosage_not_displayed():
    # If farmer or system requests an unknown or generic chemical
    label = verify_pesticide_label(crop="Soybean", target_pest="Unknown Weed", chemical_product="Magic Spray 500")
    assert label["verified"] is False
    assert label["status"] in ("UNVERIFIED", "UNVERIFIED_LABEL")
    assert label["recommended_dose"] is None
    assert "cannot be certified" in label["advisory_message"] or "UNVERIFIED" in label["advisory_message"]
    assert "KVK" in label["advisory_message"] or "official label" in label["advisory_message"]

    # Verify that a known CIBRC registered product provides verified dosage
    known_label = verify_pesticide_label(
        crop="Soybean",
        target_pest="Spodoptera / Tobacco Caterpillar (Spodoptera litura)",
        chemical_product="Chlorantraniliprole 18.5% SC",
    )
    assert known_label["verified"] is True
    assert known_label["status"] == "OFFICIAL_LABEL_VERIFIED"
    assert known_label["recommended_dose"] is not None
    assert "Chlorantraniliprole" in known_label["active_ingredient"]


# 11. Multilingual outputs work across both engines (EN, HI, MR)
def test_11_multilingual_outputs():
    forecast = _make_mock_forecast(rain=0.0, wind=8.0, et0=4.5)
    for lang in ["en", "hi", "mr"]:
        irr = plan_7day_irrigation_schedule(
            forecast_rows=forecast,
            crop="Soybean",
            growth_stage="Flowering",
            soil_moisture="dry",
            language=lang,
        )
        assert irr["overall_verdict"] != ""
        assert len(irr["daily_schedule"]) == 7

        pest = assess_pesticide_weather_suitability(
            forecast_rows=forecast,
            crop="Soybean",
            growth_stage="Flowering",
            language=lang,
        )
        assert pest["overall_verdict"] != ""
        assert len(pest["daily_schedule"]) == 7
        # Ensure pollination alert appears in flowering stage
        assert pest["stage_warning"] != ""


# 12. All dashboard sections consume the same current forecast report payload
def test_12_single_source_of_truth_agent_payload(monkeypatch):
    monkeypatch.setattr("core.sources.geocode_location", lambda *a, **kw: {
        "name": "Nashik", "admin1": "Maharashtra", "admin2": "Nashik", "latitude": 20.0, "longitude": 73.78, "country": "India"
    })
    dates = ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"]
    monkeypatch.setattr("core.sources.get_weather_forecast", lambda *a, **kw: {
        "daily": {
            "time": dates,
            "precipitation_sum": [12.0] * 7,
            "precipitation_probability_max": [70.0] * 7,
            "temperature_2m_max": [30.0] * 7,
            "temperature_2m_min": [20.0] * 7,
            "wind_speed_10m_max": [10.0] * 7,
            "et0_fao_evapotranspiration": [4.0] * 7,
        }
    })
    monkeypatch.setattr("core.sources.get_mandi_prices", lambda *a, **kw: {
        "connected": False, "status": "unconfigured", "records": [], "count": 0
    })

    report = run_advisory(
        location="Nashik",
        crop="Soybean",
        growth_stage="Flowering",
        soil_texture="Black Cotton / Vertisol",
        soil_moisture="moist",
        irrigation_method="Drip",
        language="en",
    )

    # Verify both engines are present in the single unified report payload
    assert "irrigation" in report
    assert "pesticide_spray" in report
    assert "risk" in report
    assert "economics_and_water" in report

    # Verify that the forecast length consumed by both is identical
    assert len(report["irrigation"]["daily_schedule"]) == 7
    assert len(report["pesticide_spray"]["daily_schedule"]) == 7
    assert len(report["risk"]["forecast_rows"]) == 7
