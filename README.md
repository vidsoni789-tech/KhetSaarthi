# KhetSaarthi 🌱

**An AI-Powered Multilingual Agricultural Risk & Resource Advisory Agent for Indian Farmers.**

KhetSaarthi bridges the gap between fragmented meteorological data and volatile wholesale markets. Designed for smallholder farmers (with an initial focus on Maharashtra), it autonomously ingests live 7-day weather forecasts and daily Government of India (AGMARKNET) mandi prices, synthesizes explainable crop-stage risk heuristics, generates a daily spray & fieldwork suitability schedule, and provides grounded multilingual conversational Q&A in **Marathi (मराठी)**, **Hindi (हिन्दी)**, and **English**.

> **Data-Integrity Guardrail (Strict & Non-Negotiable):** Zero fabricated weather or synthetic mandi prices. When government market APIs are busy or unconfigured, the system triggers transparent `PARTIAL_FALLBACK`, delivering the full weather risk advisory while honestly explaining the data limitation.

---

## 🌟 Key Technical Capabilities

1. **Smart Geocoding Fallback (`core/sources.py`):**
   - Resolves Indian place names via Open-Meteo & GeoNames.
   - Compound query parsing: splits compound strings (e.g. `"Lasalgaon, Nashik"`, `"Baramati, MH"`) to retry primary place tokens and score candidates matching state/district hints and population.
2. **Fast-Timeout AGMARKNET Adapter with District-to-State Fallback (`core/sources.py`):**
   - Connects to `data.gov.in` daily wholesale mandi feed.
   - Enforces a **4.5-second strict timeout** and 1 retry to guarantee sub-3-second live demo performance.
   - Attempts district-level matching first; if 0 records exist, automatically falls back to state-level aggregation (`query_level="state"`).
   - Catches server timeouts or `"Resource lists"` busy responses cleanly without unhandled exceptions.
3. **Deterministic Crop-Stage Sensitivity Matrix (`core/risk_engine.py`):**
   - Transparent 0–100 heuristic risk index evaluating heavy rain (≥50mm), heat stress (≥36°C / 40°C), wind drift (≥35 km/h), and 3-day short dry spells.
   - **`flowering_wet_stress`**: Flags flower drop, cloud stress, and fungal/blight risks during flowering stages (Soybean, Cotton, Tur, Onion, Tomato) when rain probability ≥70% or multi-day rain ≥10mm.
   - **`harvest_wet_risk`**: Flags mold, pod rotting, and bulb discoloration risks during harvest/maturity when unseasonal rain is detected.
4. **7-Day Spray & Field-Work Suitability Schedule (`core/risk_engine.py`):**
   - Computes daily agronomic operational status:
     - `❌ AVOID`: Rain ≥ 5.0mm, rain probability ≥ 70%, or wind speed ≥ 20.0 km/h.
     - `⚠️ CAUTION`: Rain ≥ 1.5mm, rain probability ≥ 45%, or wind speed ≥ 15.0 km/h.
     - `✅ SAFE`: Calm, dry window suitable for pesticide or foliar application.
   - Fully localized status badges and reasons in English, Hindi, and Marathi.
5. **Grounded Multilingual Intent Router (`core/chat.py`):**
   - Zero-hallucination Q&A router grounded strictly in the current advisory session's fetched metrics.
   - Accurately answers inquiries regarding spray timing windows, rainfall dates, temperature & irrigation (ET₀), risk score attribution, and mandi rates.
   - Provides 4 natural 1-click suggested question prompts per language for instant judge exploration.
6. **Executive Streamlit Decision Dashboard (`app.py`):**
   - **1-Click Judge Demo Presets** for instant live evaluation (`Nashik`, `Latur`, `Lasalgaon`).
   - Executive 4-metric KPI summary strip.
   - Responsive 7-day visual spray suitability card strip.
   - Plotly forecast charts with decision threshold reference lines (5mm rain avoid line, 36°C heat watch, 20 km/h spray drift limit).
   - Autonomous execution trace showing step-by-step latency in milliseconds and verification evidence.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Farmer_Interface [Farmer / Judge Interface]
        UI[Streamlit Web Dashboard]
        Presets[1-Click Demo Presets]
        ChatUI[Grounded Multilingual Chat]
    end

    subgraph Agent_Core [Autonomous Agent Orchestrator: core/agent.py]
        Plan[1. Execution Plan]
        Trace[Telemetry & Latency Logger]
        Val[6. Bounding & Integrity Assertion Gate]
    end

    subgraph Data_Adapters [External Adapters: core/sources.py]
        Geo[Open-Meteo Geocoding<br>Smart Comma Fallback]
        Weather[Open-Meteo 7-Day Forecast<br>Rain, Temp, Wind, ET₀]
        Mandi[AGMARKNET data.gov.in<br>4.5s Fast Timeout & District Fallback]
    end

    subgraph Reasoning_Engine [Explainable Engines]
        RiskEng[core/risk_engine.py<br>Crop-Stage Matrix & 7-Day Spray Schedule]
        ChatRouter[core/chat.py<br>Grounded Multilingual Q&A Router]
    end

    subgraph Output_Presentation [Executive Presentation]
        KPI[Executive KPI Cards]
        SprayStrip[7-Day Spray Suitability Strip]
        Charts[Plotly Charts with Reference Thresholds]
        TraceView[Step Telemetry & Verification Links]
    end

    Presets --> UI
    UI --> Plan
    Plan --> Geo
    Geo --> Weather
    Geo --> Mandi
    Weather --> RiskEng
    Mandi -.->|Optional Tool / Partial Fallback| RiskEng
    RiskEng --> Val
    Val --> Trace
    Trace --> KPI
    Trace --> SprayStrip
    Trace --> Charts
    Trace --> TraceView
    ChatUI <--> ChatRouter
    ChatRouter -.->|Session Anchored Values| RiskEng
```

---

## 📋 Data Sources & API Protocols

| Source | Role | Protocol / Auth | Fallback Policy |
|---|---|---|---|
| **[Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api)** | Place to Lat/Lon resolution | Public REST API | Smart fallback: splits comma queries, ranks by state hints & population |
| **[Open-Meteo Forecast](https://open-meteo.com/en/docs)** | 7-day daily forecast: rain, temp, wind, ET₀ | Public REST API | Strict timeout (15s); essential step (raises explicit `AgentStepError` on failure) |
| **[data.gov.in AGMARKNET](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)** | Daily wholesale market arrivals & modal prices | REST API with API Key | **4.5s fast timeout**; district-to-state fallback; when public demo key is throttled (`Resource lists`), seamlessly activates **Verified Historical AGMARKNET Snapshot** with explicit badge and recorded arrival dates; missing keys gracefully degrade to weather-only advisory with zero fabricated prices |
| **[IMD Agromet](https://mausam.imd.gov.in/responsive/agromet_adv_ser_state_current.php)** | Authoritative district agronomic bulletins | Verification link | Reference verification link in UI footer |

---

## 🚀 Local Setup & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.12 and 3.13)
- Active internet connection

### Step-by-Step Setup (Windows PowerShell)

```powershell
# 1. Clone repository & navigate to directory
git clone https://github.com/vidsoni789-tech/KhetSaarthi.git
cd KhetSaarthi

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Configure Mandi API Key
Copy-Item .env.example .env
# Edit .env and insert your DATA_GOV_API_KEY if available

# 5. Run the Automated Test Suite (24 Tests)
python -m pytest -v

# 6. Launch the Streamlit Application
streamlit run app.py
```

---

## ☁️ Streamlit Community Cloud Deployment

1. Push this repository to a public GitHub repository.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and create an application:
   - **Repository:** `vidsoni789-tech/KhetSaarthi`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. In **App Settings → Secrets**, configure your optional AGMARKNET API key:
   ```toml
   DATA_GOV_API_KEY = "your_key_here"
   ```
4. Click **Deploy**. The app will boot cleanly and serve live advisories worldwide.

---

## 🧪 Automated Testing & Verification

The project includes 24 automated, offline-safe unit tests in `tests/`:

```powershell
python -m pytest -v
```

```text
============================= test session starts =============================
collected 24 items

tests\test_phase3_risk_and_chat.py .........                             [ 37%]
tests\test_risk_engine.py .....                                          [ 58%]
tests\test_sources_and_agent.py ..........                               [100%]

============================= 24 passed in 0.35s ==============================
```

To run the live external API smoke test (requires network access):
```powershell
python scripts/smoke_test_phase3.py
```

---

## 👥 Hackathon Team & Viva Preparation

Every team member must be prepared to defend the architecture, heuristic math, and execution traces. Consult **[`TEAM_VIVA_GUIDE.md`](TEAM_VIVA_GUIDE.md)** for:
- Line-by-line codebase walkthrough
- Complete heuristic threshold & scoring table
- 6 tough judge Q&A answers
- Step-by-step 2–3 minute demo choreography
