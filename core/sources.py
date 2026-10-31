"""Live data adapters for KhetSaarthi.

No fixture or fallback values are returned: source errors are explicit and transparent.
"""
from __future__ import annotations

import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MANDI_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# Clean commodity nomenclature mapped to official AGMARKNET commodity names
COMMODITY_MAP: dict[str, str] = {
    "Soybean": "Soyabean",
    "Soyabean": "Soyabean",
    "Cotton": "Cotton",
    "Onion": "Onion",
    "Wheat": "Wheat",
    "Rice": "Paddy(Dhan)(Common)",
    "Paddy": "Paddy(Dhan)(Common)",
    "Maize": "Maize",
    "Sugarcane": "Sugarcane",
    "Groundnut": "Groundnut",
    "Tomato": "Tomato",
    "Tur": "Arhar (Tur/Red Gram)(Whole)",
    "Pigeon Pea": "Arhar (Tur/Red Gram)(Whole)",
    "Tur / Pigeon Pea": "Arhar (Tur/Red Gram)(Whole)",
    "Arhar": "Arhar (Tur/Red Gram)(Whole)",
    "Gram": "Gram Raw(Chhota Gram)",
    "Chana": "Gram Raw(Chhota Gram)",
    "Potato": "Potato",
}

# Common state abbreviations for smart geocoding hints
STATE_ABBR_MAP: dict[str, str] = {
    "MH": "Maharashtra",
    "MP": "Madhya Pradesh",
    "GJ": "Gujarat",
    "KA": "Karnataka",
    "AP": "Andhra Pradesh",
    "TS": "Telangana",
    "TG": "Telangana",
    "PB": "Punjab",
    "HR": "Haryana",
    "UP": "Uttar Pradesh",
    "RJ": "Rajasthan",
    "TN": "Tamil Nadu",
    "WB": "West Bengal",
    "BR": "Bihar",
    "OD": "Odisha",
    "KL": "Kerala",
}


def _session() -> requests.Session:
    """Standard HTTP session for Open-Meteo with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "KhetSaarthi/1.0 (hackathon prototype)"})
    return session


def _mandi_session() -> requests.Session:
    """Fast, dedicated session for data.gov.in with low retries for live-demo speed."""
    session = requests.Session()
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=2)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "KhetSaarthi/1.0 (hackathon prototype)"})
    return session


def resolve_data_gov_api_key(api_key: str | None = None) -> str:
    """Resolve data.gov.in API key with explicit empty-string bypass.

    - If api_key is explicitly provided (including ""), it is used directly.
      This allows tests/callers to pass api_key="" to guarantee no fallback to .env.
    - If api_key is None, falls back to DATA_GOV_API_KEY environment variable.
    - If env var is empty, safely checks st.secrets inside a try/except block.
    """
    if api_key is not None:
        return api_key.strip()

    env_val = os.getenv("DATA_GOV_API_KEY", "").strip()
    if env_val:
        return env_val

    try:
        import streamlit as st
        return str(st.secrets.get("DATA_GOV_API_KEY", "")).strip()
    except Exception:
        return ""


def normalize_commodity_name(commodity: str) -> str:
    """Map user/standard commodity name to official AGMARKNET nomenclature."""
    clean = (commodity or "").strip()
    return COMMODITY_MAP.get(clean, clean)


def geocode_location(location_text: str) -> dict[str, Any]:
    """Resolve an Indian place name via Open-Meteo/GeoNames with smart fallback.

    Handles compound inputs like 'Nashik, Maharashtra', 'Lasalgaon, Nashik',
    or 'Baramati, MH' by falling back to primary tokens and candidate scoring.
    """
    if not location_text or len(location_text.strip()) < 2:
        raise ValueError("Enter a village, town, or district with at least 2 characters.")

    raw_query = location_text.strip()
    session = _session()

    # Step 1: Attempt direct geocoding with user-provided query
    results: list[dict[str, Any]] = []
    try:
        response = session.get(
            GEOCODING_URL,
            params={"name": raw_query, "count": 8, "language": "en", "format": "json", "countryCode": "IN"},
            timeout=(4, 10),
        )
        if response.ok:
            results = response.json().get("results") or []
    except Exception:
        results = []

    # Step 2: Smart fallback if direct query returned no results and comma-separated tokens exist
    parts = [p.strip() for p in raw_query.split(",") if p.strip()]
    hints = [p.lower() for p in parts[1:]]
    expanded_hints: set[str] = set(hints)
    for h in hints:
        upper_h = h.upper()
        if upper_h in STATE_ABBR_MAP:
            expanded_hints.add(STATE_ABBR_MAP[upper_h].lower())

    if not results and len(parts) > 1:
        primary = parts[0]
        try:
            response = session.get(
                GEOCODING_URL,
                params={"name": primary, "count": 8, "language": "en", "format": "json", "countryCode": "IN"},
                timeout=(4, 10),
            )
            if response.ok:
                results = response.json().get("results") or []
        except Exception:
            results = []

    if not results:
        raise LookupError(f"No Indian location matched '{location_text}'. Try adding or simplifying the town or district name.")

    # Prioritize candidates matching state/district hints, then by population
    def _rank_candidate(c: dict[str, Any]) -> tuple[int, int]:
        c_admin1 = str(c.get("admin1") or "").lower()
        c_admin2 = str(c.get("admin2") or "").lower()
        hint_match = 0
        if expanded_hints:
            for hint in expanded_hints:
                if hint and (hint in c_admin1 or hint in c_admin2):
                    hint_match = 1
                    break
        pop = int(c.get("population") or 0)
        return (hint_match, pop)

    results.sort(key=_rank_candidate, reverse=True)
    best = results[0]

    return {
        "name": best.get("name", location_text),
        "admin1": best.get("admin1", ""),
        "admin2": best.get("admin2", ""),
        "country": best.get("country", "India"),
        "latitude": float(best["latitude"]),
        "longitude": float(best["longitude"]),
        "timezone": best.get("timezone", "Asia/Kolkata"),
        "candidates": results,
    }


def get_weather_forecast(latitude: float, longitude: float, timezone: str = "auto") -> dict[str, Any]:
    """Fetch live seven-day forecast; values are returned exactly as supplied by Open-Meteo."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "et0_fao_evapotranspiration",
        ]),
        "timezone": timezone or "auto",
        "forecast_days": 7,
    }
    response = _session().get(FORECAST_URL, params=params, timeout=(4, 15))
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload.get("reason", "Weather provider returned an error."))
    daily = payload.get("daily")
    if not daily or not daily.get("time"):
        raise RuntimeError("Weather provider returned no daily forecast for this location.")
    return payload


def _get_field(record: dict[str, Any], *names: str) -> Any:
    """Case-insensitive field lookup for API schema variations."""
    lowered = {str(k).lower(): v for k, v in record.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _parse_mandi_records(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clean and standardize raw AGMARKNET records."""
    records: list[dict[str, Any]] = []
    for item in raw_records:
        records.append({
            "Market": _get_field(item, "market"),
            "District": _get_field(item, "district"),
            "Commodity": _get_field(item, "commodity"),
            "Variety": _get_field(item, "variety"),
            "Date": _get_field(item, "arrival_date"),
            "Min price (₹/quintal)": _get_field(item, "min_price"),
            "Max price (₹/quintal)": _get_field(item, "max_price"),
            "Modal price (₹/quintal)": _get_field(item, "modal_price"),
        })
    return [r for r in records if r.get("Market") and r.get("Modal price (₹/quintal)") is not None]


def get_mandi_prices(
    state: str,
    commodity: str,
    api_key: str | None = None,
    district: str | None = None,
) -> dict[str, Any]:
    """Fetch current daily AGMARKNET prices from data.gov.in.

    Guarantees:
    - 4.5s strict timeout to prevent demo delays.
    - Clean degradation if key missing, API times out, or returns 'Resource lists'.
    - Automatic fallback from district-level query to state-level query if 0 records.
    - Zero hallucinated prices.
    """
    key = resolve_data_gov_api_key(api_key)
    if not key:
        return {
            "connected": False,
            "status": "unconfigured",
            "records": [],
            "count": 0,
            "query_level": "none",
            "message": "DATA_GOV_API_KEY is not configured.",
            "reason": "DATA_GOV_API_KEY is not configured.",
        }

    mapped_commodity = normalize_commodity_name(commodity)
    session = _mandi_session()

    # Strategy: If district provided, attempt district-level query first
    clean_district = (district or "").strip()
    if clean_district:
        params_district = {
            "api-key": key,
            "format": "json",
            "limit": 100,
            "filters[state]": state,
            "filters[district]": clean_district,
            "filters[commodity]": mapped_commodity,
        }
        try:
            resp = session.get(MANDI_URL, params=params_district, timeout=4.5)
            resp.raise_for_status()
            payload = resp.json()

            if payload.get("message") and not payload.get("records"):
                msg = str(payload.get("message"))
                return {
                    "connected": False,
                    "status": "degraded",
                    "reason": f"OGD India API temporarily busy/unavailable ({msg})",
                    "records": [],
                    "count": 0,
                    "query_level": "district",
                    "message": f"Mandi API reported: {msg}. Proceeding with weather advisory.",
                }

            district_records = _parse_mandi_records(payload.get("records") or [])
            if district_records:
                return {
                    "connected": True,
                    "status": "success",
                    "records": district_records,
                    "count": len(district_records),
                    "query_level": "district",
                    "filter_district": clean_district,
                    "filter_state": state,
                    "message": f"Daily AGMARKNET records retrieved for {clean_district} district.",
                }
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
            return {
                "connected": False,
                "status": "degraded",
                "reason": "OGD India API temporarily busy/unavailable (timeout after 4.5s)",
                "records": [],
                "count": 0,
                "query_level": "district",
                "message": "Mandi API timed out after 4.5s. Proceeding with weather-only advisory.",
            }
        except requests.exceptions.RequestException as exc:
            return {
                "connected": False,
                "status": "degraded",
                "reason": f"OGD India API network error: {type(exc).__name__}",
                "records": [],
                "count": 0,
                "query_level": "district",
                "message": f"Mandi API connection failed ({type(exc).__name__}). Proceeding with weather-only advisory.",
            }
        except Exception as exc:
            return {
                "connected": False,
                "status": "degraded",
                "reason": f"OGD India API error: {str(exc)[:100]}",
                "records": [],
                "count": 0,
                "query_level": "district",
                "message": f"Mandi API processing error. Proceeding with weather-only advisory.",
            }

    # State-level query (either directly or as fallback when district had 0 records)
    params_state = {
        "api-key": key,
        "format": "json",
        "limit": 100,
        "filters[state]": state,
        "filters[commodity]": mapped_commodity,
    }
    try:
        resp = session.get(MANDI_URL, params=params_state, timeout=4.5)
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("message") and not payload.get("records"):
            msg = str(payload.get("message"))
            return {
                "connected": False,
                "status": "degraded",
                "reason": f"OGD India API temporarily busy/unavailable ({msg})",
                "records": [],
                "count": 0,
                "query_level": "state",
                "message": f"Mandi API reported: {msg}. Proceeding with weather advisory.",
            }

        state_records = _parse_mandi_records(payload.get("records") or [])
        msg_note = (
            f"Daily AGMARKNET records retrieved for {state} (state-level fallback)."
            if clean_district
            else f"Daily AGMARKNET records retrieved for {state}."
        )
        return {
            "connected": True,
            "status": "success",
            "records": state_records,
            "count": len(state_records),
            "query_level": "state",
            "filter_state": state,
            "message": msg_note if state_records else f"API connected, but 0 daily market records reported for {state} - {mapped_commodity}.",
        }
    except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
        return {
            "connected": False,
            "status": "degraded",
            "reason": "OGD India API temporarily busy/unavailable (timeout after 4.5s)",
            "records": [],
            "count": 0,
            "query_level": "state",
            "message": "Mandi API timed out after 4.5s. Proceeding with weather-only advisory.",
        }
    except requests.exceptions.RequestException as exc:
        return {
            "connected": False,
            "status": "degraded",
            "reason": f"OGD India API network error: {type(exc).__name__}",
            "records": [],
            "count": 0,
            "query_level": "state",
            "message": f"Mandi API connection failed ({type(exc).__name__}). Proceeding with weather-only advisory.",
        }
    except Exception as exc:
        return {
            "connected": False,
            "status": "degraded",
            "reason": f"OGD India API error: {str(exc)[:100]}",
            "records": [],
            "count": 0,
            "query_level": "state",
            "message": "Mandi API processing error. Proceeding with weather-only advisory.",
        }
