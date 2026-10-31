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
from core.chat import (
    answer_farmer_query,
    get_active_chat_engine_info,
    get_suggested_questions,
)
from core.crop_config import (
    CROP_AGRONOMY_REGISTRY,
    IRRIGATION_METHODS,
    SOIL_MOISTURE_STATES,
    SUPPORTED_CROPS,
    SUPPORTED_SOIL_TYPES,
    get_crop_config,
    get_kc,
    get_ky,
    get_cibrc_label,
)
from core.economics import (
    apply_weather_stress_deltas,
    compute_crop_water_balance,
    evaluate_mandi_arbitrage_and_hold_risk,
)
from core.irrigation import plan_7day_irrigation_schedule
from core.messaging import (
    clean_phone_number,
    format_whatsapp_advisory_message,
    format_whatsapp_deep_link,
    send_real_whatsapp_message,
)
from core.pesticide_spray import assess_pesticide_weather_suitability, verify_pesticide_label
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
  .badge-irr-need {background: #dbeafe; color: #1e40af; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-irr-defer {background: #fef3c7; color: #92400e; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-irr-monitor {background: #f1f5f9; color: #475569; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-irr-unknown {background: #ede9fe; color: #6b21a8; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-pest-suitable {background: #dcfce7; color: #15803d; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-pest-caution {background: #fef3c7; color: #b45309; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-pest-avoid {background: #fee2e2; color: #b91c1c; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .badge-pest-unknown {background: #f1f5f9; color: #475569; font-weight: 700; padding: 2px 6px; border-radius: 5px; font-size: 0.72rem;}
  .day-metric {font-size: 0.8rem; color: #334155; margin-top: 0.25rem;}
  .day-reason {font-size: 0.72rem; color: #64748b; margin-top: 0.35rem; line-height: 1.2;}
</style>
<div class="hero">
  <h1>🌱 KhetSaarthi</h1>
  <p>Pan-India Multilingual Farm Risk, Precision Irrigation & Market Advisory — Live across all 28 States & UTs of India.</p>
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
    """Retrieve Mandi API key from sidebar input, env, or Streamlit secrets."""
    sb_key = st.session_state.get("sb_data_gov_input", "").strip()
    if sb_key:
        return sb_key
    value = os.getenv("DATA_GOV_API_KEY", "")
    try:
        value = st.secrets.get("DATA_GOV_API_KEY", value)
    except Exception:
        pass
    return str(value or "").strip()


def _get_llm_key() -> str:
    """Retrieve LLM API key from sidebar input, env, or secrets."""
    sb_key = st.session_state.get("sb_llm_key_input", "").strip()
    if sb_key:
        return sb_key
    for key_name in ["GROQ_API_KEY", "GEMINI_API_KEY", "HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"]:
        val = os.getenv(key_name, "").strip()
        if not val:
            try:
                val = str(st.secrets.get(key_name, "")).strip()
            except Exception:
                pass
        if val:
            return val
    return ""


@st.cache_data(ttl=900, show_spinner=False)
def _cached_run_advisory(
    location_text: str,
    crop: str,
    stage: str,
    language: str,
    mandi_commodity: str,
    mandi_api_key: str,
    lot_quintals: float = 20.0,
    soil_texture: str = "Loamy / Medium Alluvial",
    soil_moisture: str = "moist",
    irrigation_method: str | None = None,
    target_pest: str | None = None,
    pesticide_product: str | None = None,
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
        soil_texture=soil_texture,
        soil_moisture=soil_moisture,
        irrigation_method=irrigation_method,
        target_pest=target_pest,
        pesticide_product=pesticide_product,
    )


# --- SIDEBAR CONTROLS & PRESETS ---
with st.sidebar:
    st.markdown("### 🎯 1-Click Pan-India Demos")
    st.caption("Instantly test verified scenarios across North, Central, West & South India:")

    demo_presets = [
        {
            "name": "🌾 Preset 1: Punjab (Ludhiana - Wheat)",
            "location": "Ludhiana, Punjab",
            "crop": "Wheat",
            "stage": "Vegetative",
            "lang_label": "हिन्दी (Hindi)",
            "soil_texture": "Loamy / Medium Alluvial",
            "soil_moisture": "dry",
            "irrigation_method": "Furrow / Flood (पाटपाणी / खुला प्रवाह)",
            "target_pest": "None / Preventive Scouting",
            "pesticide_product": "",
        },
        {
            "name": "🌱 Preset 2: MP (Indore - Soybean)",
            "location": "Indore, Madhya Pradesh",
            "crop": "Soybean",
            "stage": "Flowering",
            "lang_label": "हिन्दी (Hindi)",
            "soil_texture": "Black Cotton / Clayey (Vertisol)",
            "soil_moisture": "moist",
            "irrigation_method": "Drip Irrigation (ठिबक सिंचन / ड्रिप)",
            "target_pest": "Spodoptera / Tobacco Caterpillar (Spodoptera litura)",
            "pesticide_product": "Chlorantraniliprole 18.5% SC",
        },
        {
            "name": "🧅 Preset 3: Maharashtra (Nashik - Onion)",
            "location": "Nashik, Maharashtra",
            "crop": "Onion",
            "stage": "Flowering",
            "lang_label": "मराठी (Marathi)",
            "soil_texture": "Black Cotton / Clayey (Vertisol)",
            "soil_moisture": "moist",
            "irrigation_method": "Drip Irrigation (ठिबक सिंचन / ड्रिप)",
            "target_pest": "Onion Thrips (Thrips tabaci)",
            "pesticide_product": "Spinetoram 11.7% SC",
        },
        {
            "name": "🌿 Preset 4: Gujarat (Rajkot - Cotton)",
            "location": "Rajkot, Gujarat",
            "crop": "Cotton",
            "stage": "Flowering",
            "lang_label": "English",
            "soil_texture": "Loamy / Medium Alluvial",
            "soil_moisture": "moist",
            "irrigation_method": "Drip Irrigation (ठिबक सिंचन / ड्रिप)",
            "target_pest": "Whitefly & Jassids (Sucking pest complex)",
            "pesticide_product": "Flonicamid 50% WG",
        },
        {
            "name": "🌾 Preset 5: Haryana (Karnal - Rice)",
            "location": "Karnal, Haryana",
            "crop": "Rice",
            "stage": "Vegetative",
            "lang_label": "हिन्दी (Hindi)",
            "soil_texture": "Loamy / Medium Alluvial",
            "soil_moisture": "moist",
            "irrigation_method": "Furrow / Flood (पाटपाणी / खुला प्रवाह)",
            "target_pest": "None / Preventive Scouting",
            "pesticide_product": "",
        },
        {
            "name": "🌶️ Preset 6: AP (Guntur - Tomato)",
            "location": "Guntur, Andhra Pradesh",
            "crop": "Tomato",
            "stage": "Flowering",
            "lang_label": "English",
            "soil_texture": "Sandy / Light Murrum",
            "soil_moisture": "dry",
            "irrigation_method": "Drip Irrigation (ठिबक सिंचन / ड्रिप)",
            "target_pest": "Fruit Borer (Helicoverpa armigera)",
            "pesticide_product": "Flubendiamide 39.35% SC",
        },
    ]

    selected_preset = None
    for p in demo_presets:
        if st.button(p["name"], key=f"btn_{p['location']}_{p['crop']}", use_container_width=True):
            selected_preset = p
            st.session_state["location_input"] = p["location"]
            st.session_state["crop_input"] = p["crop"]
            st.session_state["stage_input"] = p["stage"]
            st.session_state["lang_input"] = p["lang_label"]
            st.session_state["soil_texture_input"] = p["soil_texture"]
            st.session_state["soil_moisture_input"] = p["soil_moisture"]
            st.session_state["irr_method_input"] = p["irrigation_method"]
            st.session_state["target_pest_input"] = p["target_pest"]
            st.session_state["pesticide_product_input"] = p["pesticide_product"]

    st.divider()
    st.markdown("### 🌾 Custom Farm Location")
    st.caption("🌍 Enter ANY village, town, tehsil, or district across all 28 Indian States & 8 UTs:")

    default_loc = st.session_state.get("location_input", "Ludhiana, Punjab")
    default_crop = st.session_state.get("crop_input", "Wheat")
    default_stage = st.session_state.get("stage_input", "Vegetative")
    default_lang = st.session_state.get("lang_input", "हिन्दी (Hindi)")
    default_soil_tex = st.session_state.get("soil_texture_input", "Loamy / Medium Alluvial")
    default_soil_mst = st.session_state.get("soil_moisture_input", "moist")
    default_irr_meth = st.session_state.get("irr_method_input", "Drip Irrigation (ठिबक सिंचन / ड्रिप)")
    default_pest = st.session_state.get("target_pest_input", "None / Preventive Scouting")
    default_chem = st.session_state.get("pesticide_product_input", "")

    with st.form("farm_form"):
        location = st.text_input("Village / Town / District / City (Anywhere in India)", value=default_loc, placeholder="e.g. Ludhiana, Punjab / Indore, MP / Varanasi, UP / Guntur, AP / Nashik, MH")
        crop_idx = CROPS.index(default_crop) if default_crop in CROPS else 0
        crop = st.selectbox("Crop", CROPS, index=crop_idx)
        stage_idx = STAGES.index(default_stage) if default_stage in STAGES else 2
        stage = st.selectbox("Current crop stage", STAGES, index=stage_idx)
        lang_keys = list(LANGUAGES.keys())
        lang_idx = lang_keys.index(default_lang) if default_lang in lang_keys else 0
        language_label = st.selectbox("Advisory language", lang_keys, index=lang_idx)

        st.markdown("**💧 Irrigation Field Conditions**")
        soil_tex_idx = SUPPORTED_SOIL_TYPES.index(default_soil_tex) if default_soil_tex in SUPPORTED_SOIL_TYPES else 0
        soil_texture = st.selectbox("Soil Texture", SUPPORTED_SOIL_TYPES, index=soil_tex_idx)
        soil_mst_idx = ["moist", "dry", "wet"].index(default_soil_mst) if default_soil_mst in ["moist", "dry", "wet"] else 0
        soil_moisture = st.selectbox("Observed Soil Moisture", ["moist", "dry", "wet"], index=soil_mst_idx, help="Dry: below wilting point | Moist: field capacity (Vafsa) | Wet: waterlogged/saturated")
        irr_meth_idx = IRRIGATION_METHODS.index(default_irr_meth) if default_irr_meth in IRRIGATION_METHODS else 0
        irrigation_method = st.selectbox("Irrigation Method", IRRIGATION_METHODS, index=irr_meth_idx)

        st.markdown("**🌿 Pesticide Protection Target**")
        crop_cfg = get_crop_config(crop)
        crop_pests = crop_cfg.get("common_pests", ["None / Preventive Scouting"])
        pest_idx = crop_pests.index(default_pest) if default_pest in crop_pests else 0
        target_pest = st.selectbox("Target Pest / Disease", crop_pests, index=pest_idx)
        pesticide_product = st.text_input("Chemical Product Name (Optional)", value=default_chem, placeholder="e.g. Chlorantraniliprole 18.5% SC")

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

    with st.expander("🔑 Advanced Integrations (LLM & WhatsApp)", expanded=False):
        st.caption("Optional credentials for live conversational AI and real WhatsApp push delivery.")
        st.text_input(
            "Groq / Gemini / HF API Key",
            value=os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("HF_TOKEN", ""),
            type="password",
            help="Powers live multi-turn farmer chat via Groq LLaMA 3.3, Gemini 2.5, or Hugging Face. If blank, deterministic engine is used.",
            key="sb_llm_key_input",
        )
        st.text_input(
            "data.gov.in API Key",
            value=os.getenv("DATA_GOV_API_KEY", ""),
            type="password",
            help="For live AGMARKNET mandi arrivals. If blank, verified historical snapshot is used.",
            key="sb_data_gov_input",
        )
        st.markdown("**Outbound WhatsApp Delivery Credentials**")
        st.text_input("Twilio Account SID", value=os.getenv("TWILIO_ACCOUNT_SID", ""), type="password", key="sb_tw_sid")
        st.text_input("Twilio Auth Token", value=os.getenv("TWILIO_AUTH_TOKEN", ""), type="password", key="sb_tw_tok")
        st.text_input("Twilio WhatsApp From", value=os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"), key="sb_tw_from")
        st.text_input("CallMeBot API Key", value=os.getenv("CALLMEBOT_API_KEY", ""), type="password", key="sb_cmb_key")

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
active_soil_texture = selected_preset["soil_texture"] if selected_preset else soil_texture
active_soil_moisture = selected_preset["soil_moisture"] if selected_preset else soil_moisture
active_irr_method = selected_preset["irrigation_method"] if selected_preset else irrigation_method
active_pest = selected_preset["target_pest"] if selected_preset else target_pest
active_product = selected_preset["pesticide_product"] if selected_preset else pesticide_product

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
                    soil_texture=active_soil_texture,
                    soil_moisture=active_soil_moisture,
                    irrigation_method=active_irr_method,
                    target_pest=active_pest,
                    pesticide_product=active_product,
                )
                st.session_state["report"] = report_data
                st.session_state["farm_inputs"] = {
                    "location": active_location,
                    "crop": active_crop,
                    "stage": active_stage,
                    "language": active_lang_label,
                    "lang_code": lang_code,
                    "soil_texture": active_soil_texture,
                    "soil_moisture": active_soil_moisture,
                    "irrigation_method": active_irr_method,
                    "target_pest": active_pest,
                    "pesticide_product": active_product,
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

    st.info("💡 **Hackathon Tip:** Click any of the **1-Click Pan-India Demos** (Punjab, MP, Maharashtra, Gujarat, Haryana, AP) in the sidebar or enter any Indian town/village to test live weather, irrigation, and mandi intelligence across all 28 states!")
    st.stop()
    import sys
    sys.exit(0)


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
    stressed_irr = plan_7day_irrigation_schedule(
        daily_dates=daily_s.get("time", []),
        daily_rain=daily_s.get("precipitation_sum", []),
        daily_et0=daily_s.get("et0_fao_evapotranspiration", []),
        crop=inputs.get("crop", "Soybean"),
        stage=inputs.get("stage", "Flowering"),
        soil_texture=inputs.get("soil_texture", "Black Cotton / Clayey (Vertisol)"),
        soil_moisture=inputs.get("soil_moisture", "moist"),
        irrigation_method=inputs.get("irrigation_method"),
        language=chat_lang,
    )
    stressed_pest = assess_pesticide_weather_suitability(
        dates=daily_s.get("time", []),
        rain_mm=daily_s.get("precipitation_sum", []),
        rain_prob=daily_s.get("precipitation_probability_max", []),
        wind_kmh=daily_s.get("wind_speed_10m_max", []),
        temp_max=daily_s.get("temperature_2m_max", []),
        crop=inputs.get("crop", "Soybean"),
        stage=inputs.get("stage", "Flowering"),
        target_pest=inputs.get("target_pest"),
        product_name=inputs.get("pesticide_product"),
        language=chat_lang,
    )
    active_report = {
        **report,
        "weather": stressed_weather,
        "risk": stressed_risk,
        "irrigation": stressed_irr,
        "pesticide_spray": stressed_pest,
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
irr_data = active_report.get("irrigation", {})
pest_data = active_report.get("pesticide_spray", {})
econ_water = active_report.get("economics_and_water", {})
mandi_econ = econ_water.get("mandi_arbitrage", {})
water_bal = econ_water.get("water_balance", {})

# --- 1. TOP EXECUTIVE KPI STRIP ---
st.markdown("### 📊 Farm Risk & Agronomic Signals")
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
      <div class="kpi-subtext">Deterministic crop-stage heuristic index</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    irr_status = irr_data.get("overall_status", "MONITOR SOIL MOISTURE")
    irr_bg = "#fee2e2" if irr_status == "DEFER AND RECHECK" else ("#dbeafe" if irr_status == "IRRIGATION MAY BE NEEDED" else "#f1f5f9")
    irr_col = "#991b1b" if irr_status == "DEFER AND RECHECK" else ("#1e40af" if irr_status == "IRRIGATION MAY BE NEEDED" else "#475569")
    def_val = irr_data.get("net_moisture_deficit_mm")
    etc_val = irr_data.get("total_etc_mm")
    def_txt = f"Deficit: {def_val:.1f} mm · ETc: {etc_val:.1f} mm" if def_val is not None else "Incalculable (missing ET0)"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">💧 7-Day Irrigation Need</div>
      <div class="kpi-value" style="font-size: 1.15rem; color:{irr_col}; font-weight: 800;">
        {irr_status}
      </div>
      <div class="kpi-subtext">{def_txt} · {inputs.get('soil_moisture', 'moist').upper()} soil</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    pest_status = pest_data.get("overall_status", "SUITABLE WEATHER WINDOW")
    pest_col = "#15803d" if "SUITABLE" in pest_status else ("#b91c1c" if "AVOID" in pest_status else "#b45309")
    s_cnt = len(pest_data.get("suitable_dates", []))
    c_cnt = len(pest_data.get("caution_dates", []))
    a_cnt = len(pest_data.get("avoid_dates", []))
    best_w = pest_data.get("best_window") or "None"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">🌿 Spray Weather Window</div>
      <div class="kpi-value" style="font-size: 1.15rem; color:{pest_col}; font-weight: 800;">
        {best_w}
      </div>
      <div class="kpi-subtext">{s_cnt} Suitable · {c_cnt} Caution · {a_cnt} Avoid</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")


# --- 2. 7-DAY DUAL OPERATIONAL CALENDAR (INDEPENDENT ADVISORY ENGINES) ---
st.markdown("### 🗓️ 7-Day Dual Operational Calendar")
st.caption("💧 **Row 1: Root-Zone Irrigation Need** (Root depth deficit via FAO-56 Penman-Monteith) | 🌿 **Row 2: Foliar Pesticide Weather** (Canopy atmospheric drift & wash-off limits)")

irr_schedule = irr_data.get("daily_schedule", [])
pest_schedule = pest_data.get("daily_schedule", [])
cal_len = max(len(irr_schedule), len(pest_schedule))

if cal_len > 0:
    cols = st.columns(cal_len)
    for idx in range(cal_len):
        i_day = irr_schedule[idx] if idx < len(irr_schedule) else {}
        p_day = pest_schedule[idx] if idx < len(pest_schedule) else {}
        d_date = i_day.get("date") or p_day.get("date") or f"Day {idx+1}"

        # Irrigation status styling
        i_status = i_day.get("status", "MONITOR SOIL MOISTURE")
        if i_status == "IRRIGATION MAY BE NEEDED":
            i_badge_cls = "badge-irr-need"
            i_icon = "💧"
        elif i_status == "DEFER AND RECHECK":
            i_badge_cls = "badge-irr-defer"
            i_icon = "⏳"
        elif i_status == "INSUFFICIENT DATA":
            i_badge_cls = "badge-irr-unknown"
            i_icon = "❓"
        else:
            i_badge_cls = "badge-irr-monitor"
            i_icon = "👁️"

        # Pesticide status styling
        p_status = p_day.get("status", "SUITABLE WEATHER WINDOW")
        if p_status == "SUITABLE WEATHER WINDOW":
            p_badge_cls = "badge-pest-suitable"
            p_icon = "✅"
        elif p_status == "CAUTION WINDOW":
            p_badge_cls = "badge-pest-caution"
            p_icon = "⚠️"
        elif p_status == "AVOID SPRAYING":
            p_badge_cls = "badge-pest-avoid"
            p_icon = "❌"
        else:
            p_badge_cls = "badge-pest-unknown"
            p_icon = "❓"

        i_etc_val = f"{i_day.get('etc_mm'):.1f}" if i_day.get("etc_mm") is not None else "N/A"
        i_eff_val = f"{i_day.get('effective_rain_mm'):.1f}" if i_day.get("effective_rain_mm") is not None else "N/A"
        p_rain_val = f"{p_day.get('rain_mm'):.1f}" if p_day.get("rain_mm") is not None else "0.0"
        p_prob_val = f"{p_day.get('rain_prob'):.0f}" if p_day.get("rain_prob") is not None else "0"
        p_wind_val = f"{p_day.get('wind_kmh'):.1f}" if p_day.get("wind_kmh") is not None else "N/A"

        with cols[idx]:
            st.markdown(f"""
            <div class="day-card" style="min-height: 295px; text-align: left; padding: 0.6rem 0.5rem;">
              <div class="day-date" style="text-align: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 3px;">{d_date}</div>
              
              <!-- SECTION A: SOIL IRRIGATION -->
              <div style="margin-top: 5px; padding: 5px; background: #f8fafc; border-radius: 6px; border-left: 3px solid #3b82f6;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #1e40af;">💧 SOIL WATER</div>
                <div style="margin: 3px 0;"><span class="{i_badge_cls}">{i_icon} {i_day.get('localized_status', i_status)}</span></div>
                <div style="font-size: 0.74rem; color: #334155;">ET<sub>c</sub>: <b>{i_etc_val}</b> mm</div>
                <div style="font-size: 0.74rem; color: #334155;">Eff Rain: <b>{i_eff_val}</b> mm</div>
                <div style="font-size: 0.68rem; color: #64748b; margin-top: 2px; line-height: 1.15;">{i_day.get('reason', '')[:65]}...</div>
              </div>

              <!-- SECTION B: PESTICIDE SPRAY -->
              <div style="margin-top: 6px; padding: 5px; background: #f0fdf4; border-radius: 6px; border-left: 3px solid #10b981;">
                <div style="font-size: 0.70rem; font-weight: 700; color: #065f46;">🌿 PESTICIDE WEATHER</div>
                <div style="margin: 3px 0;"><span class="{p_badge_cls}">{p_icon} {p_day.get('localized_status', p_status)}</span></div>
                <div style="font-size: 0.74rem; color: #334155;">Wind: <b>{p_wind_val}</b> km/h</div>
                <div style="font-size: 0.74rem; color: #334155;">Rain: <b>{p_prob_val}%</b> ({p_rain_val}mm)</div>
                <div style="font-size: 0.68rem; color: #64748b; margin-top: 2px; line-height: 1.15;">{p_day.get('reason', '')[:65]}...</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

st.write("")


# --- 2.1. DEDICATED ENGINE BREAKDOWNS (MODULE 1: IRRIGATION & MODULE 2: PESTICIDE) ---
irr_plan_col, pest_plan_col = st.columns([1, 1])

with irr_plan_col:
    st.markdown("### 💧 Section A: Irrigation Advisory Engine")
    st.caption("Plan root irrigation via FAO-56 Penman-Monteith ETc and soil capacity. Never mixes chemical spray dilution with soil watering.")
    
    irr_verdict = irr_data.get("overall_verdict", "")
    if "DEFER" in irr_data.get("overall_status", ""):
        st.warning(f"**{irr_verdict}**")
    elif "IRRIGATION MAY BE NEEDED" in irr_data.get("overall_status", ""):
        st.info(f"**{irr_verdict}**")
    else:
        st.success(f"**{irr_verdict}**")

    iw1, iw2, iw3, iw4 = st.columns(4)
    with iw1:
        kc_v = irr_data.get("kc")
        st.metric("Crop Stage Kc", f"{kc_v:.2f}" if kc_v is not None else "N/A", help="FAO-56 Table 12 crop coefficient")
    with iw2:
        etc_v = irr_data.get("total_etc_mm")
        st.metric("7-Day ETc Demand", f"{etc_v:.1f} mm" if etc_v is not None else "N/A", help="Crop water requirement = ET0 × Kc")
    with iw3:
        eff_v = irr_data.get("total_effective_rain_mm")
        st.metric("Effective Rain (Peff)", f"{eff_v:.1f} mm" if eff_v is not None else "N/A", help="Discounted for runoff and interception")
    with iw4:
        net_def = irr_data.get("net_moisture_deficit_mm")
        st.metric("Net Soil Deficit", f"{net_def:.1f} mm" if net_def is not None else "N/A", help="Net root moisture deficit")

    st.markdown(f"**Field Profile:** Soil: `{irr_data.get('soil_texture', 'Loamy')}` | Moisture: `{irr_data.get('initial_soil_moisture', 'moist').upper()}` | Method: `{inputs.get('irrigation_method', 'Drip')}`")
    st.caption(irr_data.get("disclaimer", "Verify field moisture before operating valves."))

with pest_plan_col:
    st.markdown("### 🌿 Section B: Pesticide Spray Weather & CIBRC Claims")
    st.caption("Evaluate foliar drift, wash-off risk & statutory CIBRC label claims. Prohibits guessed dosages or unconditional spray guarantees.")

    p_verdict = pest_data.get("overall_verdict", "")
    if "SUITABLE" in pest_data.get("overall_status", ""):
        st.success(f"**{p_verdict}**")
    elif "AVOID" in pest_data.get("overall_status", ""):
        st.error(f"**{p_verdict}**")
    else:
        st.warning(f"**{p_verdict}**")

    # Stage Warning (e.g. Pollinator Warning during Flowering)
    stage_w = pest_data.get("stage_warning")
    if stage_w:
        st.warning(f"⚠️ **Crop Stage Alert:** {stage_w}")

    # Statutory CIBRC Label Claim Card
    lbl = pest_data.get("label_evaluation", {})
    if lbl.get("status") == "OFFICIAL_LABEL_VERIFIED":
        st.markdown(f"""
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 10px 14px; margin-top: 6px;">
          <div style="font-weight: 750; color: #166534; font-size: 0.92rem;">✅ Statutory CIBRC Label Claim Verified</div>
          <div style="font-size: 0.80rem; color: #14532d; margin-top: 2px;"><b>Active Ingredient:</b> {lbl.get('active_ingredient')}</div>
          <div style="font-size: 0.80rem; color: #14532d;"><b>Verified Dosage:</b> <span style="background:#bbf7d0; padding:1px 5px; border-radius:4px; font-weight:700;">{lbl.get('recommended_dose')}</span></div>
          <div style="font-size: 0.80rem; color: #14532d;"><b>Water Volume:</b> {lbl.get('water_volume_liters_acre')} L/Acre · <b>Pre-Harvest Interval (PHI):</b> {lbl.get('phi_days')} Days</div>
          <div style="font-size: 0.75rem; color: #15803d; margin-top: 2px;">🐝 <em>Pollinator Safety:</em> {lbl.get('pollinator_safety')}</div>
        </div>
        """, unsafe_allow_html=True)
    elif lbl.get("status") == "NO_PEST_SPECIFIED":
        st.info(f"📋 **Target Problem:** {lbl.get('advisory_message')}")
    else:
        st.markdown(f"""
        <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; margin-top: 6px;">
          <div style="font-weight: 750; color: #92400e; font-size: 0.92rem;">⚠️ Statutory Label Verification Notice</div>
          <div style="font-size: 0.80rem; color: #78350f; margin-top: 2px;">{lbl.get('advisory_message')}</div>
          <div style="font-size: 0.74rem; color: #b45309; margin-top: 2px;"><em>Notice: Under the Insecticides Act, chemical dosages cannot be certified from crop name alone. Follow registered product container leaflet and consult KVK.</em></div>
        </div>
        """, unsafe_allow_html=True)
    st.caption(pest_data.get("disclaimer", "Weather suitability does not replace container label directives."))

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
    st.markdown("#### 📲 Outbound WhatsApp Push & Village Bulletin")
    st.caption("Deliver real advisories directly to farmer phones via WhatsApp 1-click deep-link, CallMeBot webhook, or Twilio API.")

    advisory_msg = format_whatsapp_advisory_message(report, language=chat_lang)

    farmer_phone = st.text_input(
        "Farmer WhatsApp Phone Number",
        value=st.session_state.get("farmer_phone_input", "+919131374796"),
        key="farmer_phone_input",
        help="Format: +919131374796 or 9131374796. Advisory will be delivered to this recipient.",
    )

    clean_num = clean_phone_number(farmer_phone)
    wa_link = format_whatsapp_deep_link(clean_num, advisory_msg)

    tw_sid = st.session_state.get("sb_tw_sid", "").strip() or os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    tw_token = st.session_state.get("sb_tw_tok", "").strip() or os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    tw_from = st.session_state.get("sb_tw_from", "").strip() or os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886").strip()
    cmb_key = st.session_state.get("sb_cmb_key", "").strip() or os.getenv("CALLMEBOT_API_KEY", "").strip()

    has_api_backend = bool((tw_sid and tw_token) or cmb_key)

    if has_api_backend:
        push_c1, push_c2 = st.columns([1, 1])
        with push_c1:
            send_push_btn = st.button("🚀 Send Real WhatsApp Push (API)", type="primary", use_container_width=True)
        with push_c2:
            st.markdown(
                f'<a href="{wa_link}" target="_blank" style="text-decoration:none;">'
                f'<button style="background:#25D366;color:white;border:none;padding:10px 14px;border-radius:8px;font-weight:700;font-size:0.9rem;cursor:pointer;width:100%;box-shadow:0 2px 6px rgba(37,211,102,0.25);">'
                f'💬 Open in WhatsApp (1-Click)'
                f'</button></a>',
                unsafe_allow_html=True,
            )
        if send_push_btn:
            with st.spinner("Dispatching outbound WhatsApp message via configured HTTP gateway..."):
                disp_result = send_real_whatsapp_message(
                    phone_number=clean_num,
                    message=advisory_msg,
                    twilio_sid=tw_sid or None,
                    twilio_token=tw_token or None,
                    twilio_from=tw_from,
                    callmebot_api_key=cmb_key or None,
                )
                st.session_state["last_wa_dispatch"] = disp_result
    else:
        # Direct 1-Click WhatsApp Delivery (Zero API Keys Needed)
        st.markdown(
            f'<a href="{wa_link}" target="_blank" style="text-decoration:none;">'
            f'<button style="background:linear-gradient(135deg, #25D366 0%, #128C7E 100%);color:white;border:none;padding:12px 20px;border-radius:10px;font-weight:700;font-size:1.02rem;cursor:pointer;width:100%;box-shadow:0 3px 10px rgba(37,211,102,0.3);margin-bottom:8px;display:flex;align-items:center;justify-content:center;gap:8px;">'
            f'💬 Open & Send to {clean_num} on WhatsApp (1-Click) →'
            f'</button></a>',
            unsafe_allow_html=True,
        )

        with st.expander("⚡ Enable Automated Background Server Push (CallMeBot / Twilio)", expanded=False):
            st.caption("Send advisories in the background directly from our server without opening WhatsApp on your device.")
            st.markdown("**Option 1 (100% Free): CallMeBot Webhook**")
            st.caption("1. Send `I allow callmebot to send me messages` to `+34 911 06 18 10` on WhatsApp ([Click here to send](https://api.whatsapp.com/send?phone=34911061810&text=I%20allow%20callmebot%20to%20send%20me%20messages)).")
            st.caption("2. CallMeBot will reply with your API key. Enter it below:")
            inline_cmb = st.text_input("CallMeBot API Key", value=cmb_key, type="password", key="inline_cmb_key")
            if inline_cmb:
                st.session_state["sb_cmb_key"] = inline_cmb

            st.markdown("---")
            st.markdown("**Option 2: Twilio WhatsApp API**")
            inline_tw_sid = st.text_input("Twilio Account SID", value=tw_sid, type="password", key="inline_tw_sid")
            inline_tw_tok = st.text_input("Twilio Auth Token", value=tw_token, type="password", key="inline_tw_tok")
            if inline_tw_sid:
                st.session_state["sb_tw_sid"] = inline_tw_sid
            if inline_tw_tok:
                st.session_state["sb_tw_tok"] = inline_tw_tok

            if st.button("🚀 Dispatch via Server API Gateway", type="primary", use_container_width=True):
                active_sid = inline_tw_sid or tw_sid
                active_tok = inline_tw_tok or tw_token
                active_cmb = inline_cmb or cmb_key
                if (active_sid and active_tok) or active_cmb:
                    with st.spinner("Dispatching outbound WhatsApp message via server gateway..."):
                        disp_result = send_real_whatsapp_message(
                            phone_number=clean_num,
                            message=advisory_msg,
                            twilio_sid=active_sid or None,
                            twilio_token=active_tok or None,
                            twilio_from=tw_from,
                            callmebot_api_key=active_cmb or None,
                        )
                        st.session_state["last_wa_dispatch"] = disp_result
                else:
                    st.warning("Enter your CallMeBot API Key or Twilio credentials above to dispatch via background server API.")

    # Optional Auto-dispatch toggle
    auto_send = st.checkbox(
        "⚡ Auto-Send WhatsApp Alert when Risk Score >= 15",
        value=False,
        key="auto_wa_toggle",
        help="When enabled and risk is elevated (score >= 15), automatically dispatches WhatsApp alert upon report generation.",
    )

    # Handle auto-send trigger
    if auto_send and risk.get("score", 0) >= 15:
        report_sig = f"{place.get('name')}_{risk.get('score')}_{inputs.get('stage')}_{clean_num}"
        if st.session_state.get("last_auto_wa_sig") != report_sig:
            st.session_state["last_auto_wa_sig"] = report_sig
            auto_disp = send_real_whatsapp_message(
                phone_number=clean_num,
                message=advisory_msg,
                twilio_sid=tw_sid or None,
                twilio_token=tw_token or None,
                twilio_from=tw_from,
                callmebot_api_key=cmb_key or None,
            )
            st.session_state["last_wa_dispatch"] = auto_disp
            if auto_disp.get("sent"):
                st.toast(f"⚡ Auto-Alert delivered to {clean_num} (Risk: {risk.get('score')}/100)!", icon="📲")

    if "last_wa_dispatch" in st.session_state:
        disp = st.session_state["last_wa_dispatch"]
        if disp.get("sent"):
            st.success(
                f"✅ **WhatsApp Message Dispatched!**\n\n"
                f"- **Gateway Provider:** `{disp.get('provider')}`\n"
                f"- **Recipient:** `{clean_num}`\n"
                f"- **Message SID / ID:** `{disp.get('message_sid', 'N/A')}`\n"
                f"- **Latency:** `{disp.get('latency_ms', 0)} ms`\n"
                f"- **Status Detail:** {disp.get('status_detail', 'Sent successfully')}"
            )
        else:
            st.success(
                f"📱 **Advisory Ready for {clean_num}!**\n\n"
                f"Click below to launch WhatsApp with the complete advisory prefilled:"
            )
            st.markdown(
                f'<a href="{wa_link}" target="_blank" style="text-decoration:none;">'
                f'<button style="background:#25D366;color:white;border:none;padding:10px 18px;border-radius:8px;font-weight:700;font-size:0.95rem;cursor:pointer;width:100%;box-shadow:0 2px 8px rgba(37,211,102,0.3);margin-bottom:8px;">'
                f'👉 Open WhatsApp Chat with {clean_num} Now'
                f'</button></a>',
                unsafe_allow_html=True,
            )

    with st.expander("📝 View / Copy Formatted Bulletin Text", expanded=False):
        st.text_area("Advisory Bulletin Content", value=advisory_msg, height=130, disabled=True)


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

# Active Conversational Engine Telemetry Badge
active_llm_key = _get_llm_key()
engine_info = get_active_chat_engine_info(llm_api_key=active_llm_key)
if engine_info.get("is_llm"):
    engine_badge = f'<span style="background:#dcfce7;color:#166534;padding:4px 10px;border-radius:12px;font-size:0.82rem;font-weight:700;">🤖 Live Grounded LLM: {str(engine_info.get("provider", "")).upper()} ({engine_info.get("model")})</span>'
else:
    engine_badge = f'<span style="background:#e0f2fe;color:#0369a1;padding:4px 10px;border-radius:12px;font-size:0.82rem;font-weight:700;">📐 Deterministic Grounded Engine | 100% Offline-Safe Heuristics</span>'

chat_hdr_col1, chat_hdr_col2 = st.columns([4, 1])
with chat_hdr_col1:
    st.markdown(f"**Conversational Engine:** {engine_badge}", unsafe_allow_html=True)
with chat_hdr_col2:
    if st.button("🧹 Clear Chat", key="clear_chat_btn", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()

# Render 1-Click Suggested Questions
suggested = get_suggested_questions(chat_lang)
q_cols = st.columns(len(suggested))
for q_idx, sq in enumerate(suggested):
    with q_cols[q_idx]:
        if st.button(sq, key=f"sq_btn_{q_idx}", use_container_width=True):
            history_before = list(st.session_state.get("chat_history", []))
            st.session_state.setdefault("chat_history", []).append({"role": "user", "content": sq})
            with st.spinner("Formulating grounded response..."):
                ans = answer_farmer_query(
                    question=sq,
                    report=report,
                    language=chat_lang,
                    chat_history=history_before,
                    llm_api_key=active_llm_key,
                )
            st.session_state["chat_history"].append({"role": "assistant", "content": ans})
            st.rerun()

# Render chat history
for message in st.session_state.get("chat_history", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("e.g. When can I spray this week? / बारिश कब होगी? / फवारणी कधी करावी?")
if user_question:
    history_before = list(st.session_state.get("chat_history", []))
    st.session_state.setdefault("chat_history", []).append({"role": "user", "content": user_question})
    with st.spinner("Formulating grounded response..."):
        ans = answer_farmer_query(
            question=user_question,
            report=report,
            language=chat_lang,
            chat_history=history_before,
            llm_api_key=active_llm_key,
        )
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
