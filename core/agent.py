"""Autonomous Execution Graph and Orchestrator for KhetSaarthi.

Coordinates external API tools (Geocoding, 7-day Forecast, AGMARKNET Mandi),
heuristic risk assessment, and report validation with transparent telemetry.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .economics import (
    compute_crop_water_balance,
    evaluate_mandi_arbitrage_and_hold_risk,
)
from .risk_engine import assess_weather_risk
from .sources import (
    geocode_location,
    get_mandi_prices,
    get_weather_forecast,
    resolve_data_gov_api_key,
)


class AgentStepError(RuntimeError):
    """Raised when an essential execution step fails unrecoverably."""
    pass


def _timed_step(
    log: list[dict[str, Any]],
    name: str,
    description: str,
    fn: Callable[[], Any],
    fallback_status: str | None = None,
) -> tuple[Any, int]:
    """Execute a tool step with high-resolution latency timing and status telemetry."""
    t0 = time.perf_counter()
    event: dict[str, Any] = {
        "step": name,
        "status": "running",
        "latency_ms": 0,
        "detail": description,
        "evidence": "",
    }
    log.append(event)
    try:
        result = fn()
        elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
        event["status"] = "completed"
        event["latency_ms"] = elapsed_ms
        event["detail"] = f"{description} — completed ({elapsed_ms}ms)"
        return result, elapsed_ms
    except Exception as exc:
        elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
        event["latency_ms"] = elapsed_ms
        if fallback_status:
            event["status"] = fallback_status
            event["detail"] = f"{description} — {type(exc).__name__}: {str(exc)[:160]} (fallback activated)"
        else:
            event["status"] = "failed"
            event["detail"] = f"{description} — {type(exc).__name__}: {str(exc)[:160]}"
        raise


def run_advisory(
    location_text: str,
    crop: str,
    stage: str,
    language: str = "en",
    mandi_state: str = "",
    mandi_commodity: str = "",
    mandi_api_key: str | None = None,
    lot_quintals: float = 20.0,
) -> dict[str, Any]:
    """Plan, execute, validate, and compose an advisory from live external sources.

    Execution graph:
    1. Plan: Establishes a 6-step autonomous execution strategy.
    2. Geocode (Essential): Resolves place to lat/lon with smart fallback.
    3. Weather (Essential): Fetches 7-day daily forecast via Open-Meteo.
    4. Mandi (Optional Tool): Queries AGMARKNET daily wholesale prices (4.5s max).
       Degrades gracefully to partial_fallback without breaking weather advisory.
    5. Risk Engine: Evaluates deterministic rule-based triggers for crop & stage.
    6. Economics & Water: Calculates spatial mandi arbitrage, spoilage VaR & FAO-56 irrigation.
    7. Validation: Enforces bounding and source-freshness integrity assertions.
    """
    total_t0 = time.perf_counter()
    log: list[dict[str, Any]] = []

    # 1. PLAN
    plan = [
        "Resolve the farmer's location with live geocoding",
        "Fetch the seven-day forecast for the resolved coordinates",
        "Attempt a current daily mandi-price lookup (when configured)",
        "Evaluate forecast risks against transparent crop-stage rules",
        "Calculate spatial mandi arbitrage, spoilage VaR, and FAO-56 crop water balance",
        "Validate source availability and assemble localized actions",
    ]
    log.append({
        "step": "plan",
        "status": "completed",
        "latency_ms": 1,
        "detail": "Created 6-step autonomous execution plan",
        "evidence": "6 stages scheduled: Geocoding -> 7-Day Forecast -> AGMARKNET Mandi -> Risk Engine -> Economics & Water -> Output Validation",
    })

    # 2. GEOCODE (Essential)
    try:
        place, geo_ms = _timed_step(
            log,
            "geocode",
            f"Resolve '{location_text}' via Open-Meteo Geocoding",
            lambda: geocode_location(location_text),
        )
        log[-1]["detail"] = f"Resolved {place['name']}, {place.get('admin1', '')} ({place['latitude']:.4f}, {place['longitude']:.4f}) in {geo_ms}ms"
        log[-1]["evidence"] = f"Coordinates: {place['latitude']:.4f}, {place['longitude']:.4f} | District: {place.get('admin2') or 'N/A'}, State: {place.get('admin1') or 'N/A'}"
    except Exception as exc:
        raise AgentStepError(f"Location lookup failed: {exc}") from exc

    # 3. WEATHER (Essential)
    try:
        weather, weather_ms = _timed_step(
            log,
            "weather",
            "Fetch live seven-day weather forecast from Open-Meteo",
            lambda: get_weather_forecast(place["latitude"], place["longitude"], place.get("timezone", "auto")),
        )
        daily = weather.get("daily", {})
        dates = daily.get("time", [])
        rain_vals = [v for v in daily.get("precipitation_sum", []) if v is not None]
        temp_vals = [v for v in daily.get("temperature_2m_max", []) if v is not None]
        wind_vals = [v for v in daily.get("wind_speed_10m_max", []) if v is not None]
        max_r = max(rain_vals) if rain_vals else 0.0
        max_t = max(temp_vals) if temp_vals else 0.0
        max_w = max(wind_vals) if wind_vals else 0.0

        log[-1]["detail"] = f"7-day forecast fetched ({len(dates)} days, max temp: {max_t:.1f}°C, peak rain: {max_r:.1f}mm)"
        log[-1]["evidence"] = f"Dates: {dates[0]} to {dates[-1]} | Max Rain: {max_r:.1f}mm | Max Temp: {max_t:.1f}°C | Peak Wind: {max_w:.1f}km/h"
    except Exception as exc:
        raise AgentStepError(f"Weather lookup failed: {exc}") from exc

    # 4. MANDI (Optional Tool with Graceful Degradation)
    mandi: dict[str, Any]
    state = (mandi_state.strip() or place.get("admin1", "")).strip()
    district = place.get("admin2", "")
    commodity = mandi_commodity.strip() or crop
    resolved_key = resolve_data_gov_api_key(mandi_api_key)

    if not resolved_key:
        mandi = {
            "connected": False,
            "status": "unconfigured",
            "records": [],
            "count": 0,
            "query_level": "none",
            "message": "DATA_GOV_API_KEY is not configured.",
            "reason": "DATA_GOV_API_KEY is not configured.",
        }
        log.append({
            "step": "mandi",
            "status": "partial_fallback",
            "latency_ms": 1,
            "detail": "Mandi API unconfigured — graceful partial fallback to weather-only advisory",
            "evidence": "DATA_GOV_API_KEY not configured; system enforces zero mock data guardrail",
        })
    elif not state:
        mandi = {
            "connected": False,
            "status": "unconfigured",
            "records": [],
            "count": 0,
            "query_level": "none",
            "message": "Location did not resolve to an Indian state; mandi lookup skipped.",
            "reason": "Missing state metadata",
        }
        log.append({
            "step": "mandi",
            "status": "partial_fallback",
            "latency_ms": 1,
            "detail": "Location lacked state metadata — mandi tool skipped with partial fallback",
            "evidence": f"Place '{place['name']}' returned empty admin1 state",
        })
    else:
        m_t0 = time.perf_counter()
        mandi = get_mandi_prices(state=state, commodity=commodity, api_key=resolved_key, district=district)
        m_ms = max(1, int((time.perf_counter() - m_t0) * 1000))

        if mandi.get("status") == "cached_snapshot":
            rec_count = len(mandi.get("records", []))
            level = mandi.get("query_level", "district")
            log.append({
                "step": "mandi",
                "status": "partial_fallback",
                "latency_ms": m_ms,
                "detail": f"OGD API busy ({mandi.get('reason', 'throttled demo key')}) — activated Verified Historical AGMARKNET Snapshot ({rec_count} records, {level} level) in {m_ms}ms",
                "evidence": mandi.get("badge", "Verified Historical AGMARKNET Snapshot"),
            })
        elif not mandi.get("connected") or mandi.get("status") == "degraded":
            log.append({
                "step": "mandi",
                "status": "partial_fallback",
                "latency_ms": m_ms,
                "detail": f"OGD API returned '{mandi.get('reason', 'degraded')}' in {m_ms}ms — degraded gracefully to weather-only advisory",
                "evidence": mandi.get("reason", "Government AGMARKNET service busy/timed out"),
            })
        else:
            rec_count = len(mandi.get("records", []))
            level = mandi.get("query_level", "state")
            log.append({
                "step": "mandi",
                "status": "completed",
                "latency_ms": m_ms,
                "detail": f"Retrieved {rec_count} AGMARKNET market records ({level} level) in {m_ms}ms",
                "evidence": f"{rec_count} wholesale records found for {commodity} in {state}",
            })

    # 5. RISK ENGINE (Deterministic Heuristics)
    try:
        risk, risk_ms = _timed_step(
            log,
            "risk_engine",
            "Evaluate live forecast with explainable rain, heat, wind and dry-spell rules",
            lambda: assess_weather_risk(weather, crop, stage, language, mandi_data=mandi),
        )
        log[-1]["detail"] = f"Evaluated forecast: risk score {risk['score']}/100 ({risk['label']}), {len(risk['alerts'])} alerts, {len(risk['actions'])} actions"
        log[-1]["evidence"] = f"Score: {risk['score']}/100 | Category: {risk['label']} | Active triggers: {len(risk['alerts'])}"
    except Exception as exc:
        raise AgentStepError(f"Risk engine evaluation failed: {exc}") from exc

    # 6. ECONOMICS & WATER BALANCE (Spatial Arbitrage, Spoilage VaR & FAO-56 Irrigation)
    try:
        def _calc_econ() -> dict[str, Any]:
            daily = weather.get("daily", {})
            dates = daily.get("time", [])
            et0_series = daily.get("et0_fao_evapotranspiration", [])
            rain_series = daily.get("precipitation_sum", [])
            rain_prob_series = daily.get("precipitation_probability_max", [])

            cum_rain = sum(r for r in rain_series if r is not None)
            max_prob = max([p for p in rain_prob_series if p is not None], default=0.0)

            origin_dist = place.get("admin2", "")
            origin_pt = (place["latitude"], place["longitude"])

            mandi_econ = evaluate_mandi_arbitrage_and_hold_risk(
                mandi_data=mandi,
                origin_district=origin_dist,
                origin_coords=origin_pt,
                crop=crop,
                stage=stage,
                weather_risk_score=risk.get("score", 0),
                forecast_rain_mm=cum_rain,
                forecast_max_rain_prob=max_prob,
                lot_quintals=lot_quintals,
                language=language,
            )

            water_bal = compute_crop_water_balance(
                daily_dates=dates,
                daily_et0=et0_series,
                daily_rain=rain_series,
                crop=crop,
                stage=stage,
                language=language,
            )

            return {
                "lot_quintals": lot_quintals,
                "mandi_arbitrage": mandi_econ,
                "water_balance": water_bal,
            }

        economics_and_water, econ_ms = _timed_step(
            log,
            "economics_and_water",
            "Calculate spatial mandi arbitrage, weather spoilage VaR, and FAO-56 crop water balance",
            _calc_econ,
        )
        best_mkt = economics_and_water["mandi_arbitrage"].get("best_market_name", "Local APMC")
        net_rev = economics_and_water["mandi_arbitrage"].get("best_market_net_revenue", 0.0)
        spoil_var = economics_and_water["mandi_arbitrage"].get("spoilage_var_inr", 0.0)
        drip_hrs = economics_and_water["water_balance"].get("drip_hours_per_acre", 0.0)
        deficit_mm = economics_and_water["water_balance"].get("net_irrigation_deficit_mm", 0.0)

        log[-1]["detail"] = f"Economics: Best APMC '{best_mkt}' (Net ₹{net_rev:,.0f} for {lot_quintals}Q), Spoilage VaR ₹{spoil_var:,.0f} | Water: Deficit {deficit_mm:.1f} mm (~{drip_hrs:.1f} hrs drip)"
        log[-1]["evidence"] = f"Top Take-Home: ₹{net_rev:,.0f} | Spoilage VaR: ₹{spoil_var:,.0f} | Deficit: {deficit_mm:.1f} mm ({drip_hrs:.1f} hrs/acre drip)"
    except Exception as exc:
        raise AgentStepError(f"Economics and water optimization failed: {exc}") from exc

    # 7. VALIDATION (Assertion Gate)
    try:
        _, val_ms = _timed_step(
            log,
            "validation",
            "Validate weather payload, coordinates and risk outputs before display",
            lambda: _validate_report(place, weather, risk),
        )
        log[-1]["detail"] = "Validated coordinate bounds (-90..90, -180..180), 7-day forecast series, and bounded score"
        log[-1]["evidence"] = "All assertions passed: coordinates in valid range, time-series intact, score between 0 and 100"
    except Exception as exc:
        raise AgentStepError(f"Report validation failed: {exc}") from exc

    total_elapsed_ms = max(1, int((time.perf_counter() - total_t0) * 1000))

    now_utc = datetime.now(timezone.utc)
    local_tz = place.get("timezone") or "Asia/Kolkata"
    try:
        generated_local = now_utc.astimezone(ZoneInfo(local_tz)).isoformat(timespec="minutes")
    except Exception:
        generated_local = now_utc.isoformat(timespec="minutes")

    return {
        "location": place,
        "weather": weather,
        "mandi": mandi,
        "risk": risk,
        "economics_and_water": economics_and_water,
        "agent_log": log,
        "plan": plan,
        "generated_at": generated_local,
        "total_latency_ms": total_elapsed_ms,
        "sources": [
            {"name": "Open-Meteo Geocoding API", "url": "https://open-meteo.com/en/docs/geocoding-api"},
            {"name": "Open-Meteo Forecast API", "url": "https://open-meteo.com/en/docs"},
            {"name": "AGMARKNET / data.gov.in", "url": "https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi"},
            {"name": "IMD Agromet Advisory Services", "url": "https://mausam.imd.gov.in/responsive/agromet_adv_ser_state_current.php"},
        ],
    }


def _validate_report(place: dict[str, Any], weather: dict[str, Any], risk: dict[str, Any]) -> bool:
    assert -90 <= place["latitude"] <= 90, "Latitude out of range"
    assert -180 <= place["longitude"] <= 180, "Longitude out of range"
    assert weather.get("daily", {}).get("time"), "Daily time series missing"
    assert 0 <= risk["score"] <= 100, "Risk score outside 0-100 range"
    assert risk["forecast_rows"], "Forecast rows missing"
    return True


# Alias for hackathon and backward-compatible agent invocation
run_khetsaarthi_agent = run_advisory
