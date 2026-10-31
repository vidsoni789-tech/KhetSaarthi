"""KhetSaarthi 🌱 — Multilingual Farm Risk & Market Advisory Assistant.

Hackathon Architecture:
- Live Geocoding & 7-Day Forecast (Open-Meteo)
- Daily AGMARKNET Wholesale Prices (data.gov.in) with fast 4.5s graceful degradation
- Deterministic Crop-Stage Sensitivity Heuristics & 7-Day Spray Schedule
- Grounded Intent-Based Q&A in English, Hindi, and Marathi
- Zero Hallucinated Weather or Mandi Prices
"""
from __future__ import annotations

import os
import urllib.parse
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from core.agent import AgentStepError, run_advisory
from core.chat import answer_farmer_query, get_suggested_questions
from core.economics import (
    apply_weather_stress_deltas,
    compute_crop_water_balance,
    evaluate_mandi_arbitrage_and_hold_risk,
)
from core.risk_engine import assess_weather_risk
from core.sources import COMMODITY_MAP

load_dotenv()

st.set_page_config(
    page_title="KhetSaarthi 🌱 | Farm Risk & Market Advisory",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
  .block-container {padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1440px;}
  .hero {
    padding: 1.25rem 1.6rem;
    border-radius: 16px;
    background: linear-gradient(125deg, #103b29 0%, #1c5e3d 50%, #2f855a 100%);
    color: white;
    margin-bottom: 1rem;
    box-shadow: 0 4px 16px rgba(16, 59, 41, 0.15);
  }
  .hero h1 {margin: 0; font-size: 2.2rem; font-weight: 750; color: #ffffff;}
  .hero p {margin: .35rem 0 0; opacity: .92; font-size: 1.02rem;}
  .source-pill {
    display: inline-block;
    padding: .2rem .55rem;
    border-radius: 999px;
    background: #edf7f0;
    color: #23633d;
    font-size: .78rem;
    font-weight: 600;
    margin: .1rem .2rem .1rem 0;
  }
  .kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .kpi-label {font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b; margin-bottom: 0.2rem;}
  .kpi-value {font-size: 1.55rem; font-weight: 750; color: #0f172a; line-height: 1.2;}
  .kpi-subtext {font-size: 0.82rem; color: #64748b; margin-top: 0.3rem;}
  .day-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem 0.5rem;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    min-height: 175px;
  }
  .day-date {font-size: 0.88rem; font-weight: 700; color: #1e293b; margin-bottom: 0.3rem;}
  .badge-safe {background: #dcfce7; color: #15803d; font-weight: 700; padding: 3px 6px; border-radius: 6px; font-size: 0.74rem;}
  .badge-caution {background: #fef3c7; color: #b45309; font-weight: 700; padding: 3px 6px; border-radius: 6px; font-size: 0.74rem;}
  .badge-avoid {background: #fee2e2; color: #b91c1c; font-weight: 700; padding: 3px 6px; border-radius: 6px; font-size: 0.74rem;}
  .day-metric {font-size: 0.8rem; color: #334155; margin-top: 0.25rem;}
  .day-reason {font-size: 0.72rem; color: #64748b; margin-top: 0.35rem; line-height: 1.2;}
</style>
<div class="hero">
  <h1>🌱 KhetSaarthi</h1>
  <p>Multilingual Farm Risk & Market Advisory Assistant — Live Weather, AGMARKNET Prices & Heuristic Field Decisions.</p>
</div>
""", unsafe_allow_html=True)

LANGUAGES: dict[str, str] = {"मराठी (Marathi)": "mr", "हिन्दी (Hindi)": "hi", "English": "en"}
LANG_LABEL_TO_CODE: dict[str, str] = {"मराठी (Marathi)": "mr", "हिन्दी (Hindi)": "hi", "English": "en"}
LANG_CODE_TO_LABEL: dict[str, str] = {"mr": "मराठी (Marathi)", "hi": "हिन्दी (Hindi)", "en": "English"}

CROPS: list[str] = [
    "Soybean", "Cotton", "Onion", "Wheat", "Rice", "Maize",
    "Sugarcane", "Groundnut", "Tomato", "Tur / Pigeon Pea"
]
STAGES: list[str] = ["Sowing", "Vegetative", "Flowering", "Maturity / Harvest"]


def _get_api_key() -> str:
    """Retrieve API key from env or Streamlit secrets."""
    value = os.getenv("DATA_GOV_API_KEY", "")
    try:
        value = st.secrets.get("DATA_GOV_API_KEY", value)
    except Exception:
        pass
    return str(value or "").strip()


@st.cache_data(ttl=900, show_spinner=False)
def _cached_run_advisory(
    location_text: str,
    crop: str,
    stage: str,
    language: str,
    mandi_commodity: str,
    mandi_api_key: str,
    lot_quintals: float = 20.0,
) -> dict:
    """Cache external API calls for 15 minutes to guarantee rapid demo responsiveness."""
    return run_advisory(
        location_text=location_text,
        crop=crop,
        stage=stage,
        language=language,
        mandi_commodity=mandi_commodity,
        mandi_api_key=mandi_api_key,
        lot_quintals=lot_quintals,
    )


# --- SIDEBAR CONTROLS & PRESETS ---
with st.sidebar:
    st.markdown("### 🎯 1-Click Judge Demos")
    st.caption("Instantly test verified Maharashtra scenarios with zero typing:")

    demo_presets = [
        {
            "name": "🌱 Preset 1: Nashik (Flowering Wet Stress)",
            "location": "Nashik, Maharashtra",
            "crop": "Soybean",
            "stage": "Flowering",
            "lang_label": "मराठी (Marathi)",
        },
        {
            "name": "🌾 Preset 2: Latur (Harvest Spoilage Risk)",
            "location": "Latur, Maharashtra",
            "crop": "Soybean",
            "stage": "Maturity / Harvest",
            "lang_label": "हिन्दी (Hindi)",
        },
        {
            "name": "🧅 Preset 3: Lasalgaon (Smart Fallback)",
            "location": "Lasalgaon, Nashik",
            "crop": "Onion",
            "stage": "Vegetative",
            "lang_label": "English",
        },
    ]

    selected_preset = None
    for p in demo_presets:
        if st.button(p["name"], key=f"btn_{p['location']}", use_container_width=True):
            selected_preset = p
            st.session_state["location_input"] = p["location"]
            st.session_state["crop_input"] = p["crop"]
            st.session_state["stage_input"] = p["stage"]
            st.session_state["lang_input"] = p["lang_label"]

    st.divider()
    st.markdown("### 🌾 Custom Farm Details")

    default_loc = st.session_state.get("location_input", "Nashik, Maharashtra")
    default_crop = st.session_state.get("crop_input", "Soybean")
    default_stage = st.session_state.get("stage_input", "Flowering")
    default_lang = st.session_state.get("lang_input", "मराठी (Marathi)")

    with st.form("farm_form"):
        location = st.text_input("Village / Town / District", value=default_loc, placeholder="e.g. Nashik, Maharashtra")
        crop_idx = CROPS.index(default_crop) if default_crop in CROPS else 0
        crop = st.selectbox("Crop", CROPS, index=crop_idx)
        stage_idx = STAGES.index(default_stage) if default_stage in STAGES else 2
        stage = st.selectbox("Current crop stage", STAGES, index=stage_idx)
        lang_keys = list(LANGUAGES.keys())
        lang_idx = lang_keys.index(default_lang) if default_lang in lang_keys else 0
        language_label = st.selectbox("Advisory language", lang_keys, index=lang_idx)
        submitted = st.form_submit_button("Analyse my farm →", type="primary", use_container_width=True)

    st.divider()
    st.markdown("### 💰 Lot Economics & Simulation")
    lot_quintals = st.slider(
        "🌾 Harvest Lot Size (Quintals)",
        min_value=5,
        max_value=100,
        value=int(st.session_state.get("lot_quintals_input", 20)),
        step=5,
        key="lot_slider",
        help="Used to compute spatial transport freight, net take-home revenue, and spoilage Value-at-Risk.",
    )
    st.session_state["lot_quintals_input"] = lot_quintals

    with st.expander("🧪 Judge Stress-Test / What-If", expanded=False):
        st.caption("Simulate counterfactual weather deltas on top of live baseline to test extreme triggers on stage.")
        sim_rain = st.slider("Rain Surge (+mm on Days 1-3)", min_value=0, max_value=60, value=0, step=5, key="sim_rain")
        sim_temp = st.slider("Heatwave Shift (+°C)", min_value=0, max_value=10, value=0, step=1, key="sim_temp")
        sim_wind = st.slider("Wind Gust Override (+km/h)", min_value=0, max_value=40, value=0, step=5, key="sim_wind")
        is_stress_active = (sim_rain > 0 or sim_temp > 0 or sim_wind > 0)

    st.divider()
    st.caption("Live Data Connections")
    st.markdown('<span class="source-pill">Open-Meteo · Live 7-Day Forecast</span>', unsafe_allow_html=True)
    report_obj = st.session_state.get("report")
    mandi_obj = report_obj.get("mandi", {}) if report_obj else {}
    if mandi_obj.get("status") == "cached_snapshot":
        st.markdown('<span class="source-pill" style="background:#fef3c7;color:#92400e;">data.gov.in · Snapshot Fallback</span>', unsafe_allow_html=True)
    elif _get_api_key():
        st.markdown('<span class="source-pill">data.gov.in · AGMARKNET Active</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="source-pill" style="background:#fee2e2;color:#991b1b;">data.gov.in · API Key Needed</span>', unsafe_allow_html=True)
    st.caption("Government AGMARKNET prices are published daily; missing keys gracefully degrade to weather advisory without mock data.")


# Trigger analysis if form submitted or preset clicked
should_run = submitted or (selected_preset is not None)
active_location = selected_preset["location"] if selected_preset else location
active_crop = selected_preset["crop"] if selected_preset else crop
active_stage = selected_preset["stage"] if selected_preset else stage
active_lang_label = selected_preset["lang_label"] if selected_preset else language_label

if should_run:
    if not active_location.strip():
        st.error("Enter a village, town, or district first.")
    else:
        with st.spinner("KhetSaarthi agent is orchestrating live APIs & evaluating crop heuristics…"):
            try:
                lang_code = LANGUAGES[active_lang_label]
                mapped_comm = COMMODITY_MAP.get(active_crop, active_crop)
                report_data = _cached_run_advisory(
                    location_text=active_location,
                    crop=active_crop,
                    stage=active_stage,
                    language=lang_code,
                    mandi_commodity=mapped_comm,
                    mandi_api_key=_get_api_key(),
                    lot_quintals=float(lot_quintals),
                )
                st.session_state["report"] = report_data
                st.session_state["farm_inputs"] = {
                    "location": active_location,
                    "crop": active_crop,
                    "stage": active_stage,
                    "language": active_lang_label,
                    "lang_code": lang_code,
                }
                st.session_state["chat_history"] = []
            except AgentStepError as exc:
                st.error(str(exc))
                st.info("The agent adheres to strict integrity and does not substitute mock data. Check your network or location spelling.")

report = st.session_state.get("report")

if not report:
    st.subheader("Actionable, Grounded Risk Intelligence for Indian Farmers")
    st.write("Select a **1-Click Demo Preset** in the sidebar or enter your farm location to fetch fresh forecast data and evaluate transparent crop-stage rules.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Weather Horizon", "7 Days (Daily)")
    c2.metric("Supported Languages", "Marathi, Hindi, English")
    c3.metric("Mandi Dataset", "data.gov.in AGMARKNET")
    c4.metric("Integrity Guardrail", "Zero Fabricated Data")

    st.info("💡 **Hackathon Tip:** Click **'🌱 Preset 1: Nashik'** in the sidebar to observe live wet-spell heuristics, the 7-day spray suitability schedule, and grounded Marathi Q&A.")
    st.stop()


# Extract key report components
inputs = st.session_state.get("farm_inputs", {})
chat_lang = inputs.get("lang_code", "mr")

active_report = report
if is_stress_active:
    st.warning(
        f"🧪 **COUNTERFACTUAL STRESS-TEST MODE ACTIVE:** Simulating weather deltas on top of live Open-Meteo baseline "
        f"(Rain: **+{sim_rain} mm**, Temp: **+{sim_temp} °C**, Wind: **+{sim_wind} km/h**). "
        f"Underlying live Open-Meteo data remains pure and unmutated."
    )
    stressed_weather = apply_weather_stress_deltas(report["weather"], sim_rain, sim_temp, sim_wind)
    stressed_risk = assess_weather_risk(
        stressed_weather,
        inputs.get("crop", "Soybean"),
        inputs.get("stage", "Flowering"),
        chat_lang,
        mandi_data=report.get("mandi"),
    )
    daily_s = stressed_weather.get("daily", {})
    rain_s = sum(r for r in daily_s.get("precipitation_sum", []) if r is not None)
    prob_s = max([p for p in daily_s.get("precipitation_probability_max", []) if p is not None], default=0.0)
    stressed_econ = evaluate_mandi_arbitrage_and_hold_risk(
        mandi_data=report.get("mandi"),
        origin_district=report["location"].get("admin2", ""),
        origin_coords=(report["location"]["latitude"], report["location"]["longitude"]),
        crop=inputs.get("crop", "Soybean"),
        stage=inputs.get("stage", "Flowering"),
        weather_risk_score=stressed_risk.get("score", 0),
        forecast_rain_mm=rain_s,
        forecast_max_rain_prob=prob_s,
        lot_quintals=float(lot_quintals),
        language=chat_lang,
    )
    stressed_water = compute_crop_water_balance(
        daily_dates=daily_s.get("time", []),
        daily_et0=daily_s.get("et0_fao_evapotranspiration", []),
        daily_rain=daily_s.get("precipitation_sum", []),
        crop=inputs.get("crop", "Soybean"),
        stage=inputs.get("stage", "Flowering"),
        language=chat_lang,
    )
    active_report = {
        **report,
        "weather": stressed_weather,
        "risk": stressed_risk,
        "economics_and_water": {
            "lot_quintals": float(lot_quintals),
            "mandi_arbitrage": stressed_econ,
            "water_balance": stressed_water,
        },
    }
elif float(lot_quintals) != float(report.get("economics_and_water", {}).get("lot_quintals", 20.0)):
    daily_b = report["weather"].get("daily", {})
    rain_b = sum(r for r in daily_b.get("precipitation_sum", []) if r is not None)
    prob_b = max([p for p in daily_b.get("precipitation_probability_max", []) if p is not None], default=0.0)
    econ_ref = evaluate_mandi_arbitrage_and_hold_risk(
        mandi_data=report.get("mandi"),
        origin_district=report["location"].get("admin2", ""),
        origin_coords=(report["location"]["latitude"], report["location"]["longitude"]),
        crop=inputs.get("crop", "Soybean"),
        stage=inputs.get("stage", "Flowering"),
        weather_risk_score=report["risk"].get("score", 0),
        forecast_rain_mm=rain_b,
        forecast_max_rain_prob=prob_b,
        lot_quintals=float(lot_quintals),
        language=chat_lang,
    )
    active_report = {
        **report,
        "economics_and_water": {
            **report.get("economics_and_water", {}),
            "lot_quintals": float(lot_quintals),
            "mandi_arbitrage": econ_ref,
        },
    }

place = active_report["location"]
risk = active_report["risk"]
mandi = active_report["mandi"]
econ_water = active_report.get("economics_and_water", {})
mandi_econ = econ_water.get("mandi_arbitrage", {})
water_bal = econ_water.get("water_balance", {})

safe_days = risk.get("spray_schedule", [])
safe_count = sum(1 for d in safe_days if d.get("status") == "SAFE")
caution_count = sum(1 for d in safe_days if d.get("status") == "CAUTION")
avoid_count = sum(1 for d in safe_days if d.get("status") == "AVOID")


# --- 1. TOP EXECUTIVE KPI STRIP ---
st.markdown("### 📊 Farm Risk & Market Signals")
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Farm Location</div>
      <div class="kpi-value">{place['name']}</div>
      <div class="kpi-subtext">{place.get('admin2', '')}, {place.get('admin1', '')} · {place['latitude']:.3f}°N, {place['longitude']:.3f}°E</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    score = risk["score"]
    badge_color = "#15803d" if score < 30 else ("#b45309" if score < 55 else "#b91c1c")
    badge_bg = "#dcfce7" if score < 30 else ("#fef3c7" if score < 55 else "#fee2e2")
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Weather Risk Index</div>
      <div class="kpi-value">{score}<span style="font-size: 1rem; color: #64748b;"> / 100</span>
        <span style="font-size: 0.8rem; background:{badge_bg}; color:{badge_color}; padding: 2px 7px; border-radius: 6px; margin-left: 6px;">{risk['localized_label']}</span>
      </div>
      <div class="kpi-subtext">Deterministic heuristic index (not ML)</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    best_date = risk.get("best_spray_window") or "None"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Optimal Spray Window</div>
      <div class="kpi-value">{best_date}</div>
      <div class="kpi-subtext">{safe_count} Safe · {caution_count} Caution · {avoid_count} Avoid</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    if mandi.get("status") == "cached_snapshot" or mandi.get("is_snapshot"):
        top_rec = mandi["records"][0] if mandi.get("records") else {}
        modal_val = f"₹{top_rec.get('Modal price (₹/quintal)', 'N/A')}/Q"
        mkt_name = f"📦 Snapshot: {top_rec.get('Market', 'APMC')} ({top_rec.get('Date', '')})"
    elif mandi.get("connected") and mandi.get("records"):
        top_rec = mandi["records"][0]
        modal_val = f"₹{top_rec.get('Modal price (₹/quintal)', 'N/A')}/Q"
        mkt_name = f"{top_rec.get('Market', 'Mandi')} ({mandi.get('query_level', 'state')})"
    else:
        modal_val = mandi.get("status", "Degraded").title()
        mkt_name = f"Latency: {report.get('total_latency_ms', 0)} ms (No mock prices)"

    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Mandi Market Signal</div>
      <div class="kpi-value">{modal_val}</div>
      <div class="kpi-subtext">{mkt_name}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")


# --- 2. 7-DAY FIELD & SPRAY SUITABILITY SCHEDULE ---
st.markdown("### 🗓️ 7-Day Field & Spraying Suitability Schedule")
st.caption("Daily agronomic suitability: **AVOID** (Rain ≥ 5mm, Prob ≥ 70%, Wind ≥ 20 km/h) | **CAUTION** (Rain ≥ 1.5mm, Prob ≥ 45%, Wind ≥ 15 km/h) | **SAFE** (Calm & dry)")

schedule_days = risk.get("spray_schedule", [])
if schedule_days:
    cols = st.columns(len(schedule_days))
    for idx, day in enumerate(schedule_days):
        with cols[idx]:
            status = day.get("status", "SAFE")
            badge_class = f"badge-{status.lower()}"
            badge_icon = {"SAFE": "✅", "CAUTION": "⚠️", "AVOID": "❌"}.get(status, "•")
            st.markdown(f"""
            <div class="day-card">
              <div class="day-date">{day['date']}</div>
              <div class="{badge_class}">{badge_icon} {day.get('localized_status', status)}</div>
              <div class="day-metric" style="margin-top: 0.6rem;">💧 <b>{day.get('rain_mm', 0):.1f}</b> mm</div>
              <div class="day-metric">🌧️ <b>{day.get('rain_prob', 0):.0f}%</b> chance</div>
              <div class="day-metric">💨 <b>{day.get('wind_kmh', 0):.1f}</b> km/h</div>
              <div class="day-reason">{day.get('reason', '')}</div>
            </div>
            """, unsafe_allow_html=True)

st.write("")


# --- 3. ALERTS, ACTIONS & PLOTLY CHARTS ---
col_left, col_right = st.columns([1.15, 1])

with col_left:
    st.subheader("🚨 Active Weather Alerts")
    if risk["alerts"]:
        for alert in risk["alerts"]:
            level = alert["severity"]
            title = alert.get("localized_title", alert["type"].replace("_", " ").title())
            fact = alert.get("localized_fact", alert["fact"])
            if level == "High":
                st.error(f"**{title}** — {fact}")
            else:
                st.warning(f"**{title}** — {fact}")
    else:
        st.success("No critical weather triggers breached risk thresholds for this 7-day forecast window.")

    st.subheader("📋 Prioritized Decision Actions")
    for i, action in enumerate(risk["actions"], start=1):
        st.markdown(f"**{i}.** {action}")

with col_right:
    st.subheader("📈 7-Day Forecast & Decision Thresholds")
    forecast_df = pd.DataFrame(risk["forecast_rows"])

    # Chart 1: Rain & Spray Threshold
    fig_rain = px.bar(
        forecast_df,
        x="Date",
        y="Rain (mm)",
        hover_data=["Rain probability (%)", "Max temp (°C)", "Wind (km/h)"],
        title="Daily Rainfall with Spray Avoid Threshold (5mm)",
    )
    fig_rain.add_hline(y=5.0, line_dash="dash", line_color="#ef4444", annotation_text="Spray Avoid Threshold (5mm)")
    fig_rain.update_layout(height=260, margin=dict(l=5, r=5, t=35, b=5), xaxis_title="", yaxis_title="Rain (mm)")
    st.plotly_chart(fig_rain, use_container_width=True)

    # Chart 2: Temperature & Heat Alert Threshold
    fig_temp = px.line(
        forecast_df,
        x="Date",
        y=["Max temp (°C)", "Min temp (°C)"],
        markers=True,
        title="Temperature Range with Heat Watch Threshold (36°C)",
    )
    fig_temp.add_hline(y=36.0, line_dash="dash", line_color="#f59e0b", annotation_text="Heat Watch (36°C)")
    fig_temp.update_layout(height=250, margin=dict(l=5, r=5, t=35, b=5), xaxis_title="", yaxis_title="Temp (°C)", legend_title="")
    st.plotly_chart(fig_temp, use_container_width=True)

    # Chart 3: Wind Speed with Drift Threshold
    fig_wind = px.line(
        forecast_df,
        x="Date",
        y="Wind (km/h)",
        markers=True,
        title="Wind Speed with Foliar Drift Limit (20 km/h)",
    )
    fig_wind.add_hline(y=20.0, line_dash="dash", line_color="#dc2626", annotation_text="Spray Drift Limit (20 km/h)")
    fig_wind.update_layout(height=230, margin=dict(l=5, r=5, t=35, b=5), xaxis_title="", yaxis_title="Wind (km/h)")
    st.plotly_chart(fig_wind, use_container_width=True)


# --- 3.5. 💰 SPATIAL MANDI ARBITRAGE & SPOILAGE VaR + 💧 FAO-56 PRECISION IRRIGATION ---
st.divider()
st.subheader("💰 Spatial Mandi Arbitrage & Spoilage VaR (Decision Science)")
st.caption(f"Financial decisions and FAO-56 irrigation requirements optimized for **{lot_quintals} Quintals** lot size.")

ec1, ec2, ec3, ec4 = st.columns(4)
with ec1:
    net_rev_val = mandi_econ.get("best_market_net_revenue", 0.0)
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Expected Net Take-Home</div>
      <div class="kpi-value">₹{net_rev_val:,.0f}</div>
      <div class="kpi-subtext">For {lot_quintals}Q lot (After ₹1.50/Q/km road freight)</div>
    </div>
    """, unsafe_allow_html=True)

with ec2:
    best_mkt_name = mandi_econ.get("best_market_name", "APMC")
    best_net_p = mandi_econ.get("best_market_net_price", 0.0)
    best_dist = mandi_econ.get("best_market_distance_km", 0.0)
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Top Realizable Market</div>
      <div class="kpi-value">{best_mkt_name}</div>
      <div class="kpi-subtext">₹{best_net_p:,.0f}/Q net · {best_dist:.0f} km road distance</div>
    </div>
    """, unsafe_allow_html=True)

with ec3:
    spoil_var = mandi_econ.get("spoilage_var_inr", 0.0)
    spoil_pct = mandi_econ.get("spoilage_risk_pct", 0.0)
    rec_code = mandi_econ.get("recommendation_code", "SAFE_TO_HOLD")
    badge_bg = "#fee2e2" if rec_code == "SELL_NOW" else ("#fef3c7" if rec_code == "PROTECT_HARVEST" else "#dcfce7")
    badge_c = "#991b1b" if rec_code == "SELL_NOW" else ("#92400e" if rec_code == "PROTECT_HARVEST" else "#166534")
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Weather Spoilage VaR</div>
      <div class="kpi-value">₹{spoil_var:,.0f}
        <span style="font-size:0.75rem; background:{badge_bg}; color:{badge_c}; padding:2px 6px; border-radius:5px; margin-left:4px;">{rec_code.replace('_', ' ')}</span>
      </div>
      <div class="kpi-subtext">{spoil_pct:.1f}% estimated quality discount risk</div>
    </div>
    """, unsafe_allow_html=True)

with ec4:
    def_mm = water_bal.get("net_irrigation_deficit_mm", 0.0)
    drip_h = water_bal.get("drip_hours_per_acre", 0.0)
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">7-Day Irrigation Deficit</div>
      <div class="kpi-value">{def_mm:.1f} mm</div>
      <div class="kpi-subtext">~{drip_h:.1f} hours drip/acre (FAO-56 ETc: {water_bal.get('total_etc_mm', 0):.1f} mm)</div>
    </div>
    """, unsafe_allow_html=True)

col_econ_left, col_econ_right = st.columns([1.15, 1])

with col_econ_left:
    st.markdown("#### 🛣️ Spatial Mandi Arbitrage Ranking")
    rankings = mandi_econ.get("market_rankings", [])
    if rankings:
        df_rank = pd.DataFrame([
            {
                "Market": r["market"],
                "District": r["district"],
                "Distance (km)": f"{r['distance_km']:.0f} km",
                "Raw Modal": f"₹{r['raw_modal_price']:,.0f}/Q",
                "Freight/Q": f"₹{r['transport_cost_per_q']:.1f}",
                "Net Price/Q": f"₹{r['net_price_per_q']:,.0f}",
                "Total Freight (₹)": f"₹{r['total_transport_cost_inr']:,.0f}",
                "Net Take-Home (₹)": f"₹{r['net_take_home_inr']:,.0f}",
            }
            for r in rankings
        ])
        st.dataframe(df_rank, use_container_width=True, hide_index=True)
        st.info(f"💡 **Spatial Arbitrage Insight:** Transporting {lot_quintals}Q to **{best_mkt_name}** yields maximum net earnings of **₹{net_rev_val:,.0f}** after deducting road freight.")
    else:
        st.info("Market arbitrage table will display when AGMARKNET market records are retrieved or configured.")

    st.markdown(f"**Action Recommendation:** {mandi_econ.get('localized_recommendation', '')}")

with col_econ_right:
    st.markdown("#### 💧 FAO-56 Crop Evapotranspiration & Water Balance")
    st.markdown(f"""
    - **Crop & Stage Coefficient ($K_c$):** `{water_bal.get('kc', 0.75):.2f}`
    - **7-Day Cumulative Crop Water Demand ($\text{{ET}}_c$):** `{water_bal.get('total_etc_mm', 0):.1f} mm`
    - **7-Day Effective Rainfall ($P_{{\\text{{eff}}}}$):** `{water_bal.get('effective_rain_mm', 0):.1f} mm`
    - **Net Moisture Deficit:** `{def_mm:.1f} mm`
    - **Total Water Needed:** `{water_bal.get('liters_per_acre_needed', 0):,.0f} Liters / Acre`
    - **Recommended Drip Run-Time:** `~{drip_h:.1f} Hours / Acre` *(standard 16,000 L/hr drip flow)*
    """)
    st.success(water_bal.get("localized_verdict", ""))


# --- 3.6. 🔊 MULTILINGUAL VOICE ADVISORY & 📲 OFFLINE WHATSAPP BULLETIN ---
st.divider()
st.subheader("🔊 Multilingual Audio Advisory & 📲 Offline WhatsApp Bulletin")

voice_col, wa_col = st.columns([1, 1])

with voice_col:
    st.markdown("#### 🎙️ Listen Aloud (Zero-Dependency Speech)")
    st.caption("Native browser speech synthesis in Marathi (`mr-IN`), Hindi (`hi-IN`), or English (`en-IN`).")

    # Construct voice text
    if chat_lang == "mr":
        speech_text = (
            f"शेतकरी मित्रांनो, {place['name']} साठी {inputs.get('crop', '')} पिकाचा हवामान जोखीम निर्देशांक "
            f"{risk['score']} आहे, {risk.get('localized_label', '')}. "
            f"फवारणीसाठी अनुकूल दिवस {risk.get('best_spray_window', 'कोरडे दिवस')}. "
            f"{risk.get('actions', [''])[0]} "
            f"{water_bal.get('localized_verdict', '')} "
            f"{mandi_econ.get('localized_recommendation', '')}"
        )
    elif chat_lang == "hi":
        speech_text = (
            f"किसान भाइयों, {place['name']} के लिए {inputs.get('crop', '')} फसल का मौसम जोखिम सूचकांक "
            f"{risk['score']} है, {risk.get('localized_label', '')}। "
            f"छिड़काव के लिए सबसे सुरक्षित दिन {risk.get('best_spray_window', 'सूखे दिन')} है। "
            f"{risk.get('actions', [''])[0]} "
            f"{water_bal.get('localized_verdict', '')} "
            f"{mandi_econ.get('localized_recommendation', '')}"
        )
    else:
        speech_text = (
            f"Farmer advisory for {place['name']}, {inputs.get('crop', '')}. "
            f"Weather risk index is {risk['score']} out of 100, {risk.get('label', '')}. "
            f"Optimal spray window is {risk.get('best_spray_window', 'dry days')}. "
            f"{risk.get('actions', [''])[0]} "
            f"{water_bal.get('localized_verdict', '')} "
            f"{mandi_econ.get('localized_recommendation', '')}"
        )

    clean_speech = speech_text.replace('"', '\\"').replace("'", "\\'").replace("\n", " ").replace("**", "").replace("#", "")
    speech_lang_code = {"mr": "mr-IN", "hi": "hi-IN", "en": "en-IN"}.get(chat_lang, "en-IN")

    voice_html = f"""
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 14px 18px; margin: 8px 0;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
        <div>
          <span style="font-weight: 700; color: #166534; font-size: 1.05rem;">🔊 Audio Broadcast ({speech_lang_code})</span>
          <div id="voice-status" style="font-size: 0.82rem; color: #047857; margin-top: 2px;">Click Play to speak risk summary aloud.</div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button onclick="playVoice()" style="background: #15803d; color: white; border: none; padding: 9px 18px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.92rem; box-shadow: 0 2px 6px rgba(21,128,61,0.25);">
            ▶️ Play (ऐका / सुनो)
          </button>
          <button onclick="stopVoice()" style="background: #dc2626; color: white; border: none; padding: 9px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.92rem;">
            ⏹️ Stop
          </button>
        </div>
      </div>
    </div>
    <script>
      function playVoice() {{
        if (!('speechSynthesis' in window)) {{
          document.getElementById('voice-status').innerText = 'Browser speech synthesis not supported on this device.';
          return;
        }}
        window.speechSynthesis.cancel();
        const text = "{clean_speech}";
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = "{speech_lang_code}";
        utter.rate = 0.92;
        utter.onstart = function() {{
          document.getElementById('voice-status').innerText = '🎙️ Speaking advisory aloud in {speech_lang_code}...';
        }};
        utter.onend = function() {{
          document.getElementById('voice-status').innerText = '✅ Finished speaking advisory.';
        }};
        utter.onerror = function() {{
          document.getElementById('voice-status').innerText = 'Audio paused / stopped.';
        }};
        window.speechSynthesis.speak(utter);
      }}
      function stopVoice() {{
        if ('speechSynthesis' in window) {{
          window.speechSynthesis.cancel();
          document.getElementById('voice-status').innerText = '⏹️ Audio stopped.';
        }}
      }}
    </script>
    """
    st.components.v1.html(voice_html, height=100)

with wa_col:
    st.markdown("#### 📲 1-Click WhatsApp & SMS Bulletin")
    st.caption("Formatted village bulletin ready to share with 500+ farmers via WhatsApp or 2G SMS.")

    bulletin_msg = (
        f"🌱 *KhetSaarthi Krishi Advisory*\\n"
        f"📍 *Location:* {place['name']}, {place.get('admin1', 'Maharashtra')}\\n"
        f"🌾 *Crop:* {inputs.get('crop', '')} ({inputs.get('stage', '')})\\n"
        f"⚠️ *Weather Risk:* {risk['score']}/100 ({risk.get('localized_label', '')})\\n"
        f"🗓️ *Safe Spray Window:* {risk.get('best_spray_window', 'None')}\\n"
        f"💧 *Irrigation Deficit:* {water_bal.get('net_irrigation_deficit_mm', 0):.1f} mm (~{water_bal.get('drip_hours_per_acre', 0):.1f} hrs drip/acre)\\n"
        f"🛒 *Best Market:* {mandi_econ.get('best_market_name', 'APMC')} (Modal: ₹{mandi_econ.get('best_market_raw_price', 0):,.0f}/Q | Net: ₹{mandi_econ.get('best_market_net_revenue', 0):,.0f} for {lot_quintals}Q)\\n"
        f"💰 *Spoilage VaR:* ₹{mandi_econ.get('spoilage_var_inr', 0):,.0f} ({mandi_econ.get('recommendation_code', 'SAFE')})\\n\\n"
        f"👉 *Action:* {risk.get('actions', [''])[0]}\\n\\n"
        f"📢 _Shared via KhetSaarthi 🌱 — Open-Meteo & AGMARKNET Decision Science._"
    )

    st.text_area("Copy-ready Bulletin Text", value=bulletin_msg, height=120, label_visibility="collapsed")
    encoded_bulletin = urllib.parse.quote(bulletin_msg)
    st.markdown(
        f'<a href="https://wa.me/?text={encoded_bulletin}" target="_blank" style="text-decoration:none;">'
        f'<button style="background:#25D366;color:white;border:none;padding:10px 20px;border-radius:8px;font-weight:700;font-size:0.95rem;cursor:pointer;width:100%;box-shadow:0 2px 6px rgba(37,211,102,0.25);">'
        f'📲 Share Bulletin to WhatsApp Group (1-Click)'
        f'</button></a>',
        unsafe_allow_html=True,
    )


# --- 4. MANDI PRICE INTELLIGENCE ---
st.divider()
st.subheader("🛒 Mandi Price Intelligence (data.gov.in AGMARKNET)")

if mandi.get("status") == "cached_snapshot" or mandi.get("is_snapshot"):
    st.warning("📦 **Verified Historical AGMARKNET Snapshot Active**\n\nThe live OGD India government API (`data.gov.in`) is currently busy/throttled for public demo keys. KhetSaarthi is displaying the last verified real APMC arrival records with recorded dates. Rates are NOT estimated or synthetic.")
    mandi_df = pd.DataFrame(mandi["records"])
    st.caption(f"Retrieved {len(mandi_df)} verified snapshot records for {inputs.get('crop')} ({mandi.get('query_level', 'district')} level). Note the exact arrival date for each market.")
    st.dataframe(mandi_df, use_container_width=True, hide_index=True)
elif mandi.get("connected") and mandi.get("records"):
    mandi_df = pd.DataFrame(mandi["records"])
    st.caption(f"Retrieved {len(mandi_df)} matching wholesale records ({mandi.get('query_level', 'state')} query). Verify arrival dates before executing farmgate sales.")
    st.dataframe(mandi_df, use_container_width=True, hide_index=True)
elif mandi.get("connected"):
    st.info(f"API connected successfully, but returned 0 daily market records for {place.get('admin1')} - {inputs.get('crop')}. No price is estimated.")
else:
    st.warning("Mandi prices are not displayed because the data.gov.in API key is not configured or the government service is temporarily busy. No synthetic prices are shown.")
    st.markdown("Register a free API key at [data.gov.in](https://data.gov.in/) and add `DATA_GOV_API_KEY` to `.env` or Streamlit secrets.")
    if mandi.get("reason"):
        st.caption(f"Status Note: {mandi['reason']}")


# --- 5. GROUNDED MULTILINGUAL CHAT WITH 1-CLICK PROMPTS ---
st.divider()
st.subheader("💬 Ask KhetSaarthi (Grounded Multilingual Q&A)")
st.caption("Ask questions about spraying windows, rainfall dates, temperature & irrigation, risk causes, or mandi rates. Zero hallucinated numbers.")

# Render 1-Click Suggested Questions
suggested = get_suggested_questions(chat_lang)
q_cols = st.columns(len(suggested))
for q_idx, sq in enumerate(suggested):
    with q_cols[q_idx]:
        if st.button(sq, key=f"sq_btn_{q_idx}", use_container_width=True):
            st.session_state.setdefault("chat_history", []).append({"role": "user", "content": sq})
            ans = answer_farmer_query(sq, report, chat_lang)
            st.session_state["chat_history"].append({"role": "assistant", "content": ans})
            st.rerun()

# Render chat history
for message in st.session_state.get("chat_history", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("e.g. When can I spray this week? / बारिश कब होगी? / फवारणी कधी करावी?")
if user_question:
    st.session_state.setdefault("chat_history", []).append({"role": "user", "content": user_question})
    ans = answer_farmer_query(user_question, report, chat_lang)
    st.session_state["chat_history"].append({"role": "assistant", "content": ans})
    st.rerun()


# --- 6. AGENT EXECUTION TRACE & TRUST FOOTER ---
with st.expander("🔍 Agent Execution Trace & Telemetry (Inspect Every Tool Call)"):
    if "total_latency_ms" in report:
        st.caption(f"⚡ Total pipeline execution latency: **{report['total_latency_ms']} ms**")
    st.markdown("**Execution Plan**")
    for i, item in enumerate(report["plan"], 1):
        st.write(f"{i}. {item}")
    st.markdown("**Runtime Step Telemetry**")
    for event in report["agent_log"]:
        icon = {
            "completed": "✅",
            "success": "✅",
            "partial_fallback": "⚠️",
            "failed": "❌",
            "skipped": "⏭️",
            "running": "⏳",
        }.get(event.get("status"), "•")
        latency = f" `{event.get('latency_ms', 0)}ms`" if "latency_ms" in event else ""
        st.write(f"{icon} **{event['step']}**{latency} — {event['detail']}")
        if event.get("evidence"):
            st.markdown(f"<div style='margin-left: 1.8rem; font-size: 0.85rem; color: #555;'>↳ <em>Evidence:</em> {event['evidence']}</div>", unsafe_allow_html=True)

with st.expander("🛡️ Authoritative Verification Links, Freshness & Disclaimers"):
    st.markdown("""
- [IMD Agromet Advisory Services — District Agricultural Bulletins](https://mausam.imd.gov.in/responsive/agromet_adv_ser_state_current.php)
- [Open-Meteo Geocoding & Weather Forecast API Docs](https://open-meteo.com/en/docs)
- [Government of India data.gov.in AGMARKNET Daily Prices](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)

**Model & Agronomic Honesty:**
1. The Weather Risk Index is an explainable heuristic decision-support index (0–100), **not a black-box machine-learning model** and not an official IMD district bulletin.
2. The prototype enforces strict data integrity: if external mandi or weather services are unreachable, it reports an honest partial fallback rather than inventing synthetic numbers.
3. Soil and field microclimates vary: farmers should verify local soil drainage, irrigation access, and consult local Krishi Vigyan Kendra (KVK) officers before executing high-stakes chemical applications.
""")

st.divider()
st.caption("🌱 KhetSaarthi · Built for Hackathon Excellence · Live-Source Architecture · Zero Mock Data")
