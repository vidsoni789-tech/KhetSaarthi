"""Unit tests for Phase 4.5 LLM Grounded Chat & Real Messaging Delivery Engine."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from core.chat import (
    answer_farmer_query,
    build_grounded_system_prompt,
    call_llm_chat,
    get_active_chat_engine_info,
    resolve_llm_config,
)
from core.messaging import (
    clean_phone_number,
    format_whatsapp_advisory_message,
    format_whatsapp_deep_link,
    send_real_whatsapp_message,
)


@pytest.fixture
def sample_report():
    return {
        "location": {
            "name": "Nashik",
            "admin1": "Maharashtra",
            "admin2": "Nashik",
            "latitude": 19.9973,
            "longitude": 73.7910,
        },
        "risk": {
            "score": 18,
            "label": "Low",
            "localized_label": "कमी",
            "crop": "Soybean",
            "stage": "Flowering",
            "best_spray_window": "2026-10-31",
            "alerts": [
                {
                    "type": "flowering_wet_stress",
                    "severity": "Moderate",
                    "fact": "Maximum rain probability 82% during flowering stage",
                }
            ],
            "actions": [
                "Optimal spraying window: 2026-10-31 (favorable calm, dry conditions).",
                "Peak rainfall expected on 2026-11-03 (4.7 mm, 78% chance).",
            ],
            "spray_schedule": [
                {"date": "2026-10-31", "status": "SAFE", "rain_mm": 1.3, "rain_prob": 43, "wind_kmh": 12.6, "reason": "Calm and dry"},
                {"date": "2026-11-01", "status": "AVOID", "rain_mm": 2.1, "rain_prob": 75, "wind_kmh": 13.7, "reason": "Rain likely (75%)"},
                {"date": "2026-11-02", "status": "AVOID", "rain_mm": 3.8, "rain_prob": 82, "wind_kmh": 13.6, "reason": "Rain likely (82%)"},
            ],
            "forecast_rows": [
                {"Date": "2026-10-31", "Rain (mm)": 1.3, "Rain probability (%)": 43, "Max temp (°C)": 30.5, "Min temp (°C)": 18.0, "Wind (km/h)": 12.6, "Reference ET₀ (mm)": 4.5},
                {"Date": "2026-11-01", "Rain (mm)": 2.1, "Rain probability (%)": 75, "Max temp (°C)": 29.8, "Min temp (°C)": 17.5, "Wind (km/h)": 13.7, "Reference ET₀ (mm)": 4.2},
                {"Date": "2026-11-02", "Rain (mm)": 3.8, "Rain probability (%)": 82, "Max temp (°C)": 28.5, "Min temp (°C)": 18.2, "Wind (km/h)": 13.6, "Reference ET₀ (mm)": 3.9},
            ],
        },
        "mandi": {
            "connected": True,
            "status": "cached_snapshot",
            "is_snapshot": True,
            "records": [
                {
                    "Market": "Nashik",
                    "District": "Nashik",
                    "Commodity": "Soyabean",
                    "Variety": "Yellow",
                    "Date": "28/10/2026",
                    "Min price (₹/quintal)": "4100",
                    "Max price (₹/quintal)": "4650",
                    "Modal price (₹/quintal)": "4480",
                }
            ],
        },
        "economics_and_water": {
            "lot_quintals": 20.0,
            "mandi_arbitrage": {
                "best_market_name": "Nashik",
                "best_market_raw_price": 4480.0,
                "best_market_distance_km": 25.0,
                "best_market_net_price": 4442.5,
                "best_market_net_revenue": 88850.0,
                "spoilage_var_inr": 0.0,
                "spoilage_risk_pct": 0.0,
                "recommendation_code": "SAFE_TO_HOLD",
            },
            "water_balance": {
                "kc": 1.15,
                "total_etc_mm": 14.5,
                "effective_rain_mm": 5.8,
                "net_irrigation_deficit_mm": 8.7,
                "drip_hours_per_acre": 2.2,
                "localized_verdict": "Net moisture deficit of 8.7 mm",
            },
        },
    }


def test_deterministic_fallback_when_no_llm_key(sample_report, monkeypatch):
    """When no LLM keys exist in env, chat router strictly uses deterministic grounded replies."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)

    ans = answer_farmer_query("When is the best day to spray?", sample_report, "en")
    assert "Optimal safe spray window" in ans
    assert "2026-10-31" in ans
    assert "Avoid spraying on" in ans

    # Telemetry badge check
    info = get_active_chat_engine_info()
    assert info["is_llm"] is False
    assert "Deterministic" in info["provider"]


def test_live_llm_chat_mocked_success(sample_report):
    """When LLM API succeeds, answer_farmer_query returns the grounded LLM content."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "शेतकरी मित्रांनो, नाशिक परिसरासाठी ३१ ऑक्टोबर २०२६ हा फवारणीसाठी सर्वोत्तम आणि सुरक्षित दिवस आहे.",
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_resp):
        ans = answer_farmer_query(
            question="फवारणी कधी करावी?",
            report=sample_report,
            language="mr",
            llm_api_key="gsk_mock_test_key_12345",
        )
        assert "नाशिक परिसरासाठी" in ans
        assert "३१ ऑक्टोबर २०२६" in ans


def test_build_grounded_system_prompt_structure(sample_report):
    """Grounded system prompt must contain strict zero-hallucination rules and full context."""
    prompt = build_grounded_system_prompt(sample_report, "mr")
    assert "KhetSaarthi" in prompt
    assert "Nashik" in prompt
    assert "Soybean" in prompt
    assert "Flowering" in prompt
    assert "18/100" in prompt
    assert "2026-10-31" in prompt
    assert "STRICT BEHAVIORAL GUARDRAILS" in prompt


def test_clean_phone_number_normalization():
    """Verify clean_phone_number handles standard Indian mobile formats."""
    assert clean_phone_number("9876543210") == "+919876543210"
    assert clean_phone_number("09876543210") == "+919876543210"
    assert clean_phone_number("+91 98765 43210") == "+919876543210"
    assert clean_phone_number("+91-98765-43210") == "+919876543210"
    assert clean_phone_number("") == ""


def test_format_whatsapp_advisory_message_multilingual(sample_report):
    """Formatted WhatsApp message must contain real dates, crop details, and prices."""
    msg_mr = format_whatsapp_advisory_message(sample_report, "mr")
    assert "खेतसारथी कृषी सल्ला" in msg_mr
    assert "Nashik" in msg_mr
    assert "Soybean (Flowering)" in msg_mr
    assert "18/100" in msg_mr
    assert "2026-10-31" in msg_mr
    assert "₹4,480/Q" in msg_mr
    assert "₹2,240 प्रति ५० किलो पोते" in msg_mr

    msg_hi = format_whatsapp_advisory_message(sample_report, "hi")
    assert "खेतसारथी कृषि परामर्श" in msg_hi
    assert "2026-10-31" in msg_hi

    msg_en = format_whatsapp_advisory_message(sample_report, "en")
    assert "KhetSaarthi Farm Risk Advisory" in msg_en
    assert "2026-10-31" in msg_en


def test_format_whatsapp_deep_link(sample_report):
    """WhatsApp deep-link must URL-encode text and address the clean number."""
    msg = "Test Advisory Message"
    link = format_whatsapp_deep_link("+91 98765 43210", msg)
    assert "https://api.whatsapp.com/send?phone=919876543210" in link
    assert "Test%20Advisory%20Message" in link


def test_send_real_whatsapp_message_unconfigured():
    """When no backend API credentials are provided, cleanly return unconfigured status with deep link."""
    res = send_real_whatsapp_message(
        phone_number="9876543210",
        message="Hello farmer",
        twilio_sid="",
        twilio_token="",
        callmebot_api_key="",
    )
    assert res["sent"] is False
    assert "Direct WhatsApp Launcher" in res["provider"]
    assert "deep_link" in res
    assert "api.whatsapp.com" in res["deep_link"]


def test_send_real_whatsapp_message_twilio_mock():
    """When Twilio credentials provided, make real HTTP POST request to Twilio endpoint."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "sid": "SM1234567890abcdef",
        "status": "queued",
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        res = send_real_whatsapp_message(
            phone_number="+919876543210",
            message="KhetSaarthi alert",
            twilio_sid="ACmocked_sid_123456",
            twilio_token="mocked_token_secret",
            twilio_from="+14155238886",
        )

        assert res["sent"] is True
        assert res["provider"] == "Twilio WhatsApp API"
        assert res["message_sid"] == "SM1234567890abcdef"
        assert "Queued/Sent via Twilio" in res["status_detail"]

        # Verify endpoint called
        called_url = mock_post.call_args[0][0]
        assert "api.twilio.com/2010-04-01/Accounts/ACmocked_sid_123456/Messages.json" in called_url
