"""Unit tests for Phase 3: Explainable Risk Engine & Grounded Multilingual Q&A."""
from __future__ import annotations

import pytest

from core.chat import answer_farmer_query, get_suggested_questions
from core.risk_engine import assess_weather_risk, compute_spray_suitability


def test_compute_spray_suitability_thresholds():
    """Verify SAFE, CAUTION, AVOID logic based on rain, rain probability, and wind."""
    dates = ["2026-11-01", "2026-11-02", "2026-11-03"]
    rain = [0.0, 2.0, 6.0]
    rain_prob = [10.0, 50.0, 85.0]
    wind = [8.0, 16.0, 22.0]

    schedule = compute_spray_suitability(dates, rain, rain_prob, wind, "en")
    assert len(schedule) == 3

    # Day 1: 0mm rain, 10% prob, 8 km/h wind -> SAFE
    assert schedule[0]["status"] == "SAFE"
    assert "Favorable" in schedule[0]["reason"]

    # Day 2: 2.0mm rain, 50% prob, 16 km/h wind -> CAUTION
    assert schedule[1]["status"] == "CAUTION"
    assert schedule[1]["localized_status"] == "Exercise Caution"

    # Day 3: 6.0mm rain, 85% prob, 22 km/h wind -> AVOID
    assert schedule[2]["status"] == "AVOID"
    assert schedule[2]["localized_status"] == "Avoid Spraying"


def test_flowering_stage_wet_stress_trigger():
    """Flowering stage under high rain probability (>70%) triggers flowering_wet_stress alert."""
    payload = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "precipitation_sum": [1.5, 3.5, 2.0],
            "precipitation_probability_max": [45, 80, 75],
            "temperature_2m_max": [29, 30, 28],
            "temperature_2m_min": [19, 19, 18],
            "wind_speed_10m_max": [10, 12, 11],
        }
    }
    result = assess_weather_risk(payload, "Soybean", "Flowering", "en")
    assert result["score"] >= 18
    assert any(a["type"] == "flowering_wet_stress" for a in result["alerts"])
    assert result["best_spray_window"] is not None or len(result["avoid_spray_dates"]) > 0


def test_harvest_stage_moisture_threat_trigger():
    """Harvest stage under unseasonal dampness triggers harvest_wet_risk alert."""
    payload = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "precipitation_sum": [2.0, 4.0, 1.0],
            "precipitation_probability_max": [40, 75, 50],
            "temperature_2m_max": [31, 30, 31],
            "temperature_2m_min": [19, 19, 19],
            "wind_speed_10m_max": [9, 10, 8],
        }
    }
    result = assess_weather_risk(payload, "Onion", "Maturity / Harvest", "mr")
    assert result["score"] >= 20
    assert any(a["type"] == "harvest_wet_risk" for a in result["alerts"])
    assert "काढणी" in " ".join(result["actions"])


def test_prioritized_actions_cite_dates_and_spray_window():
    """Actions must dynamically cite the best spray window and highest rain risk date."""
    payload = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "precipitation_sum": [0.0, 8.5, 0.0],
            "precipitation_probability_max": [5, 85, 10],
            "temperature_2m_max": [29, 27, 28],
            "temperature_2m_min": [18, 17, 18],
            "wind_speed_10m_max": [9, 14, 10],
        }
    }
    result = assess_weather_risk(payload, "Soybean", "Vegetative", "en")
    actions_text = " ".join(result["actions"])

    # Must cite best spray window (2026-11-01 or 2026-11-03)
    assert "2026-11-01" in actions_text or "2026-11-03" in actions_text
    # Must cite peak rain date (2026-11-02)
    assert "2026-11-02" in actions_text


def test_get_suggested_questions():
    """Helper returns 4 natural questions for each supported language."""
    for lang in ["en", "hi", "mr"]:
        questions = get_suggested_questions(lang)
        assert len(questions) == 4
        assert all(isinstance(q, str) and len(q) > 10 for q in questions)


def test_grounded_chat_spray_intent_multilingual():
    """Verify chat correctly answers spray window inquiries in English, Hindi, and Marathi."""
    report = {
        "risk": {
            "score": 18,
            "label": "Low",
            "localized_label": "कमी",
            "crop": "Soybean",
            "stage": "Flowering",
            "actions": [],
            "alerts": [],
            "forecast_rows": [
                {"Date": "2026-11-01", "Rain (mm)": 0.0, "Rain probability (%)": 10, "Max temp (°C)": 30.0, "Wind (km/h)": 10.0, "Reference ET₀ (mm)": 4.0},
                {"Date": "2026-11-02", "Rain (mm)": 5.0, "Rain probability (%)": 85, "Max temp (°C)": 28.0, "Wind (km/h)": 18.0, "Reference ET₀ (mm)": 3.5},
            ],
            "spray_schedule": [
                {"date": "2026-11-01", "status": "SAFE", "reason": "Favorable dry & calm window"},
                {"date": "2026-11-02", "status": "AVOID", "reason": "High rain chance (85%, 5.0mm)"},
            ],
        },
        "mandi": {"connected": False, "records": []},
    }

    # English query
    ans_en = answer_farmer_query("When can I spray pesticide this week?", report, "en")
    assert "2026-11-01" in ans_en
    assert "Avoid spraying" in ans_en
    assert "2026-11-02" in ans_en

    # Marathi query
    ans_mr = answer_farmer_query("फवारणी कधी करावी?", report, "mr")
    assert "2026-11-01" in ans_mr
    assert "फवारणी टाळा" in ans_mr

    # Hindi query
    ans_hi = answer_farmer_query("कीटनाशक स्प्रे कब करें?", report, "hi")
    assert "2026-11-01" in ans_hi
    assert "छिड़काव से बचें" in ans_hi


def test_grounded_chat_risk_explanation():
    """Chat explains risk score and active triggers deterministically."""
    report = {
        "risk": {
            "score": 40,
            "label": "Moderate",
            "localized_label": "मध्यम",
            "crop": "Cotton",
            "stage": "Flowering",
            "actions": [],
            "alerts": [
                {"type": "flowering_wet_stress", "severity": "Moderate", "fact": "Peak rain chance 80% (cumulative 12.5mm)"}
            ],
            "forecast_rows": [
                {"Date": "2026-11-01", "Rain (mm)": 4.0, "Rain probability (%)": 80, "Max temp (°C)": 31.0, "Wind (km/h)": 12.0, "Reference ET₀ (mm)": 4.0}
            ],
        },
        "mandi": {"connected": False, "records": []},
    }

    ans_en = answer_farmer_query("Why is the risk score 40?", report, "en")
    assert "40/100" in ans_en
    assert "Cotton" in ans_en
    assert "Flowering Wet Stress" in ans_en


def test_localized_alert_messages():
    """Verify alert titles and facts are properly localized in Marathi and Hindi."""
    payload = {
        "daily": {
            "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "precipitation_sum": [1.5, 3.5, 2.0],
            "precipitation_probability_max": [45, 80, 75],
            "temperature_2m_max": [29, 30, 28],
            "temperature_2m_min": [19, 19, 18],
            "wind_speed_10m_max": [10, 12, 11],
        }
    }

    # Test Marathi localization
    res_mr = assess_weather_risk(payload, "Soybean", "Flowering", "mr")
    alert_mr = res_mr["alerts"][0]
    assert "फुलोरा" in alert_mr["localized_title"]
    assert "फुलोरा" in alert_mr["fact"] or "फुलोरा" in alert_mr["localized_fact"]

    # Test Hindi localization
    res_hi = assess_weather_risk(payload, "Soybean", "Flowering", "hi")
    alert_hi = res_hi["alerts"][0]
    assert "फूल" in alert_hi["localized_title"]
    assert "फूल" in alert_hi["fact"] or "फूल" in alert_hi["localized_fact"]


def test_chat_reports_week_max_probability_accurately():
    """Verify chat distinguishes peak-rain day probability from week's maximum probability."""
    report = {
        "risk": {
            "score": 25,
            "label": "Moderate",
            "localized_label": "मध्यम",
            "crop": "Soybean",
            "stage": "Flowering",
            "actions": [],
            "alerts": [],
            "forecast_rows": [
                {"Date": "2026-11-01", "Rain (mm)": 1.0, "Rain probability (%)": 40, "Max temp (°C)": 30.0, "Wind (km/h)": 10.0},
                {"Date": "2026-11-02", "Rain (mm)": 3.8, "Rain probability (%)": 82, "Max temp (°C)": 29.0, "Wind (km/h)": 12.0},
                {"Date": "2026-11-03", "Rain (mm)": 4.7, "Rain probability (%)": 78, "Max temp (°C)": 29.5, "Wind (km/h)": 11.0},
            ],
        },
        "mandi": {"connected": False, "records": []},
    }

    ans_hi = answer_farmer_query("बारिश कब होगी?", report, "hi")
    # Peak rain is 4.7mm on 2026-11-03 (78%), but week's max probability is 82% on 2026-11-02
    assert "4.7 मिमी" in ans_hi
    assert "78%" in ans_hi
    assert "82%" in ans_hi
    assert "2026-11-02" in ans_hi

