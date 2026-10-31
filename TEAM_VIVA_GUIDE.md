# 🎓 KhetSaarthi — Team Viva & Technical Defense Guide

**Purpose:** This document ensures that **every member of our team** can confidently and independently explain the code, API protocols, mathematical risk thresholds, and agent execution graph to judges during the hackathon evaluation.

---

## 1. File-by-File Code Walkthrough

### 📁 `app.py` (Streamlit Presentation Layer)
- **Lines 15–33:** Page config (`layout="wide"`) and custom CSS styling (hero header, KPI cards, responsive 7-day spray cards, and metric badges).
- **Lines 35–48:** Core dictionaries: `CROPS` (10 major Indian crops including `Tur / Pigeon Pea`), `STAGES`, `LANGUAGES` (Marathi, Hindi, English), and `COMMODITY_MAP` mapping crops to official AGMARKNET nomenclature.
- **Lines 51–57:** `_get_api_key()`: Resolves `DATA_GOV_API_KEY` with priority: environment variable -> Streamlit Cloud app secrets (`st.secrets`).
- **Lines 60–68:** `@st.cache_data(ttl=900)`: Caches API results for 15 minutes by query parameters so that chat interactions or tab changes incur **0ms network latency**.
- **Lines 71–125:** Sidebar controls: renders **3 One-Click Judge Demo Presets** (Nashik, Latur, Lasalgaon) and manual form inputs.
- **Lines 155–205:** Top Executive KPI Strip: 4 cards showing location coordinates, heuristic score with color badge, earliest safe spray window, and mandi market signal.
- **Lines 208–235:** Visual 7-day Spray Suitability card strip with status badges (`✅ SAFE`, `⚠️ CAUTION`, `❌ AVOID`), rain mm, probability %, wind speed, and agronomic reasoning.
- **Lines 238–285:** Left/Right layout: Active Weather Alerts (fully localized) & Prioritized Actions alongside 3 Plotly charts with dashed decision threshold lines (5mm rain limit, 36°C heat watch, 20 km/h wind limit).
- **Lines 290–335:** Grounded Multilingual Chat: renders 4 1-click suggested question buttons (`get_suggested_questions`), chat history, and chat input.
- **Lines 340–375:** Agent Execution Trace: expands step-by-step telemetry (`completed`, `partial_fallback`, `latency_ms`, `evidence`) and authoritative verification links to IMD Agromet.

---

### 📁 `core/agent.py` (Autonomous Execution Graph)
- **`class AgentStepError(RuntimeError)`:** Custom exception raised only when an *essential* step (geocoding or weather) fails unrecoverably.
- **`_timed_step(...)`:** Wrapper taking any step lambda, timing execution via `time.perf_counter()`, and logging `step`, `status` (`running` -> `completed` / `failed`), `latency_ms`, and `evidence`.
- **`run_advisory(...)`:** The central orchestrator executing a strict 6-step directed graph:
  1. `plan`: Establishes the 5-step execution strategy.
  2. `geocode`: Calls Open-Meteo geocoding to resolve coordinates (lat/lon).
  3. `weather`: Calls Open-Meteo 7-day forecast API.
  4. `mandi`: Calls data.gov.in AGMARKNET. If unconfigured, times out, or returns `"Resource lists"`, logs `status="partial_fallback"` with latency and continues seamlessly.
  5. `risk_engine`: Calls `assess_weather_risk(...)` passing weather, crop, stage, language, and mandi result.
  6. `validation`: Calls `_validate_report(...)` enforcing assertions (lat/lon bounds, non-empty forecast, bounded 0–100 score).

---

### 📁 `core/risk_engine.py` (Explainable Heuristics & Spray Engine)
- **`compute_spray_suitability(...)`:** Evaluates daily operational conditions for foliar application:
  - `❌ AVOID`: If Rain ≥ 5.0 mm OR Rain Probability ≥ 70% OR Wind Speed ≥ 20.0 km/h.
  - `⚠️ CAUTION`: If Rain ≥ 1.5 mm OR Rain Probability ≥ 45% OR Wind Speed ≥ 15.0 km/h.
  - `✅ SAFE`: Calm, dry conditions.
  - Returns localized status badges and agronomic reasons in English, Hindi, and Marathi.
- **`assess_weather_risk(...)`:** Deterministic scoring algorithm aggregating points up to a maximum cap of 100:
  - Heavy Rain (≥50mm): `+35` pts (High)
  - Moderate Rain (≥25mm or prob ≥ 80% with rain ≥ 10mm): `+22` pts (Moderate)
  - High Heat (≥40°C): `+25` pts (High) | Moderate Heat (≥36°C): `+15` pts (Moderate)
  - High Wind (≥35 km/h): `+15` pts (Moderate)
  - 3-Day Dry Spell (<3mm rain with temp ≥ 32°C or ET₀ ≥ 15mm): `+15` pts (Moderate)
  - **`flowering_wet_stress`**: `+18` pts (Moderate) if Flowering stage AND (rain prob ≥ 70% OR cumulative rain ≥ 10mm OR ≥3 wet days).
  - **`harvest_wet_risk`**: `+22` pts (Moderate) if Harvest/Maturity stage AND (rain prob ≥ 65% OR rain ≥ 5mm).
  - **`wet_spell`**: `+12` pts if general multi-day wet spell detected.
- **Score Classification:** `0–29`: Low | `30–54`: Moderate | `55–79`: High | `80–100`: Severe.
- **Date-Anchored Action Plan:** Automatically identifies the earliest `SAFE` spray window date, peak rainfall date, stage recommendations, and market rate actions.

---

### 📁 `core/sources.py` (Live External Data Adapters)
- **`_session()` & `_mandi_session()`:** Two distinct HTTP connection pools. Open-Meteo uses standard retries; Mandi uses a **strict 4.5s timeout and 1 retry** so demo execution never hangs.
- **`resolve_data_gov_api_key(api_key)`:** Explicit empty-string check: passing `api_key=""` guarantees bypassing `.env` during testing/toggles.
- **`geocode_location(location_text)`:** Smart fallback geocoding. If `"Lasalgaon, Nashik"` returns 0 results, splits comma tokens, retries with `"Lasalgaon"`, and ranks candidates using `STATE_ABBR_MAP` (`MH -> Maharashtra`) and population.
- **`get_weather_forecast(lat, lon)`:** Fetches 7 daily series from Open-Meteo: `weather_code`, `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `precipitation_probability_max`, `wind_speed_10m_max`, and `et0_fao_evapotranspiration`.
- **`get_mandi_prices(state, commodity, api_key, district)`:** Queries data.gov.in AGMARKNET. Attempts district-level query first; if 0 records, automatically falls back to state-level aggregation (`query_level="state"`).

---

### 📁 `core/chat.py` (Grounded Multilingual Q&A Router)
- **`INTENTS`:** Priority-ordered keyword dictionary across English, Hindi, and Marathi: `spray`, `risk`, `water`, `rain`, `heat`, `market`, `harvest`.
- **`get_suggested_questions(language)`:** Returns 4 natural 1-click prompts per language.
- **`answer_farmer_query(question, report, language)`:** Grounded intent parser that formats answers strictly from the active session's `report` dictionary:
  - Cites exact `SAFE` vs `AVOID` dates from `spray_schedule`.
  - Cites 7-day peak rain date, mm, rain probability %, and cumulative rain.
  - Explains the exact active triggers behind the risk score.
  - Cites AGMARKNET modal price if connected; otherwise transparently states that live mandi data is unavailable and advises local APMC verification without guessing.

---

## 2. Heuristic Rules & Scoring Cheat-Sheet

| Trigger Code | Condition Thresholds | Points Added | Severity Level | Agronomic Risk Implication |
|---|---|---|---|---|
| `heavy_rain` | Max daily rain ≥ 50.0 mm | **+35** | High | Severe waterlogging, root suffocation, field input wash-off |
| `rain` | Rain ≥ 25.0 mm OR (prob ≥ 80% & rain ≥ 10mm) | **+22** | Moderate | Drainage check needed; delay foliar fertilizer/pesticides |
| `heat` (High) | Max temperature ≥ 40.0 °C | **+25** | High | Pollen sterility, thermal stress, moisture depletion |
| `heat` (Moderate) | Max temperature ≥ 36.0 °C | **+15** | Moderate | Increased evapotranspiration; irrigate in early morning |
| `wind` | Max wind speed ≥ 35.0 km/h | **+15** | Moderate | Severe pesticide spray drift; risk of plant lodging |
| `dry` | 3-day rain < 3mm AND (Temp ≥ 32°C or ET₀ ≥ 15mm) | **+15** | Moderate | Emerging soil moisture deficit; verify root-zone moisture |
| `flowering_wet_stress` | Flowering stage AND (Prob ≥ 70% or Rain ≥ 10mm or ≥3 wet days) | **+18** | Moderate | Flower drop, poor pollination, fungal/anthracnose blight |
| `harvest_wet_risk` | Harvest stage AND (Prob ≥ 65% or Rain ≥ 5mm) | **+22** | Moderate | Pod mold, grain sprouting, onion bulb discoloration |
| `wet_spell` | General crop AND (Rain ≥ 10mm across ≥3 wet days) | **+12** | Moderate | Extended cloud cover, reduced photosynthesis |

---

## 3. Spray Suitability Matrix Cheat-Sheet

| Operational Status | Decision Rule (Daily) | Recommended Action | Localized Label (MR / HI / EN) |
|---|---|---|---|
| **`AVOID`** | Rain ≥ 5.0 mm **OR** Rain Prob ≥ 70% **OR** Wind ≥ 20.0 km/h | **Do NOT spray.** High wash-off or drift risk. | ❌ फवारणी टाळा / छिड़काव से बचें / Avoid Spraying |
| **`CAUTION`** | Rain ≥ 1.5 mm **OR** Rain Prob ≥ 45% **OR** Wind ≥ 15.0 km/h | **Exercise caution.** Spray only systemic inputs in calm morning window. | ⚠️ काळजीपूर्वक फवारणी करा / सावधानी बरतें / Exercise Caution |
| **`SAFE`** | Rain < 1.5 mm **AND** Rain Prob < 45% **AND** Wind < 15.0 km/h | **Optimal window.** Ideal calm, dry conditions for foliar absorption. | ✅ फवारणीसाठी सुरक्षित / छिड़काव के लिए सुरक्षित / Safe to Spray |

---

## 4. Top 6 Tough Judge Questions & Winning Answers

### 1. "Why didn't you use a trained Machine Learning model like XGBoost or a neural network for the risk score?"
> *"In smallholder agriculture, black-box predictions destroy farmer trust. If a neural network predicts an 85% risk score, an extension worker cannot explain *why* to a farmer in Nashik. Our heuristic engine is **100% deterministic and explainable**: it pinpoints the exact meteorological trigger (e.g. 82% rain probability during flowering), cites the exact dates, and provides transparent math aligned with Indian Council of Agricultural Research (ICAR) guidelines."*

### 2. "Why don't you use an LLM API (like GPT-4 or Gemini) directly for answering farmer questions?"
> *"LLMs have non-zero hallucination rates and high per-token latency. If an LLM hallucinates a fake mandi price of ₹4,800/quintal or tells a farmer that tomorrow has 0% rain when a storm is coming, the farmer suffers direct economic loss. Our grounded intent router is **deterministic, cost-free, offline-capable**, and operates with **0ms latency** by referencing verified session values."*

### 3. "What happens when the government `data.gov.in` AGMARKNET API times out or crashes?"
> *"Most apps freeze or crash when government portals lag. In `core/sources.py`, we engineered a dedicated `_mandi_session()` with a **strict 4.5-second timeout and 1 retry**. If the API times out or returns `"Resource lists"`, our agent executes a **`PARTIAL_FALLBACK`**, logs the event in the execution trace, and delivers the complete weather and spraying advisory without making the user wait."*

### 4. "How do you handle ambiguous village names or spelling variations in rural India?"
> *"We built **Smart Geocoding Fallback** in `core/sources.py`. If a user enters `"Lasalgaon, Nashik"`, Open-Meteo returns 0 results for the compound string. Our parser automatically splits the comma, queries `"Lasalgaon"`, and ranks candidates by matching state abbreviations (`MH -> Maharashtra`), district hints (`admin2`), and population. You can verify this live with Preset 3!"*

### 5. "How does your solution scale to other states or crops?"
> *"The system is completely modular: adding a new crop requires adding its AGMARKNET commodity mapping in `COMMODITY_MAP` and any crop-specific stage thresholds in `core/risk_engine.py`. Because Open-Meteo covers the entire Indian subcontinent and AGMARKNET tracks 300+ commodities across all 28 states, KhetSaarthi is immediately national-ready without architectural changes."*

### 6. "How do you prove that your application is reliable and crash-proof?"
> *"We maintain a suite of **23 automated unit tests** in `tests/` covering API key isolation, mock timeout handling, geocoding fallback, stage risk triggers, spray schedules, and multilingual Q&A. The entire test suite executes in **under 1 second** with a 100% pass rate, and our Streamlit application boots cleanly with HTTP 200 OK."*

