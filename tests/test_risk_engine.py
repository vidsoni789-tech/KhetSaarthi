from core.risk_engine import assess_weather_risk


def test_low_risk_weather_returns_stage_action():
    payload = {"daily": {
        "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
        "precipitation_sum": [0, 0, 0],
        "precipitation_probability_max": [5, 5, 5],
        "temperature_2m_max": [27, 28, 29],
        "temperature_2m_min": [18, 18, 19],
        "wind_speed_10m_max": [8, 9, 10],
    }}
    result = assess_weather_risk(payload, "Soybean", "Vegetative", "en")
    assert result["score"] == 0
    assert result["label"] == "Low"
    assert any("Vegetative stage" in item for item in result["actions"])


def test_heavy_rain_and_heat_raise_risk():
    payload = {"daily": {
        "time": ["2026-11-01", "2026-11-02", "2026-11-03"],
        "precipitation_sum": [55, 2, 0],
        "precipitation_probability_max": [90, 20, 0],
        "temperature_2m_max": [41, 38, 37],
        "temperature_2m_min": [27, 26, 25],
        "wind_speed_10m_max": [12, 10, 8],
    }}
    result = assess_weather_risk(payload, "Cotton", "Flowering", "hi")
    assert result["score"] >= 60
    assert result["label"] in {"High", "Severe"}
    assert result["alerts"]
    assert result["localized_label"]


def test_missing_weather_series_is_not_assumed_to_be_zero():
    import pytest

    payload = {"daily": {
        "time": ["2026-11-01"],
        "precipitation_sum": [None],
        "temperature_2m_max": [28],
        "temperature_2m_min": [18],
        "wind_speed_10m_max": [10],
    }}
    with pytest.raises(ValueError, match="no usable values|incomplete"):
        assess_weather_risk(payload, "Soybean", "Sowing", "en")


def test_grounded_chat_uses_forecast_values_and_language():
    from core.chat import answer_farmer_query

    report = {
        "risk": {
            "score": 22,
            "label": "Low",
            "localized_label": "Low",
            "crop": "Soybean",
            "stage": "Vegetative",
            "actions": ["Inspect the field."],
            "alerts": [],
            "forecast_rows": [
                {"Date": "2026-11-01", "Rain (mm)": 2.0, "Rain probability (%)": 40, "Max temp (°C)": 30.0, "Wind (km/h)": 10.0, "Reference ET₀ (mm)": 4.0},
                {"Date": "2026-11-02", "Rain (mm)": 18.0, "Rain probability (%)": 80, "Max temp (°C)": 31.0, "Wind (km/h)": 12.0, "Reference ET₀ (mm)": 5.0},
            ],
        },
        "mandi": {"connected": False, "records": []},
    }
    answer = answer_farmer_query("Will there be rain?", report, "en")
    assert "18.0 mm" in answer
    assert "2026-11-02" in answer

    hindi_answer = answer_farmer_query("बारिश कब होगी?", report, "hi")
    assert "18.0 मिमी" in hindi_answer


def test_chat_never_invents_a_mandi_price_when_disconnected():
    from core.chat import answer_farmer_query

    report = {
        "risk": {"score": 0, "localized_label": "Low", "crop": "Wheat", "stage": "Sowing", "actions": [], "alerts": [], "forecast_rows": []},
        "mandi": {"connected": False, "records": []},
    }
    answer = answer_farmer_query("What is today's mandi price?", report, "en")
    assert "cannot quote a price" in answer
