# Hackathon Submission Draft — KhetSaarthi 🌱

**Track:** Climate, Resource Infrastructure & Global Supply Resilience  
**Project Name:** KhetSaarthi 🌱 (Multilingual Farm Risk & Market Advisory Agent)

---

## 1. Problem Statement

**Target Issue & Context:**
India's 140 million smallholder farmers face intensifying climate volatility and extreme local microclimate fluctuations. Weather forecasts (often presented as raw numbers in mm or % probability), daily market rates, and extension advisories are scattered across disparate portals, in English, or behind dense PDF circulars. Critical field decisions — such as spraying pesticides before unseasonal rains, irrigating during dry spells, or harvesting before damp conditions trigger pod rot — are routinely miscalculated, leading to preventable crop losses of 15–25% and distress selling at unfavorable prices.

**Target Audience:**
Smallholder farmers, Farmer Producer Organizations (FPOs), and agricultural extension workers across rural India (initial deployment focused on Maharashtra: Soybean, Cotton, Onion, Wheat, Tur/Pigeon Pea, Tomato).

---

## 2. Solution Description

**High-Level Overview:**
KhetSaarthi is an AI-powered, live-source-first agricultural risk advisory agent. In under 2.5 seconds, the agent resolves farm coordinates, retrieves live 7-day weather forecasts (Open-Meteo), checks daily government mandi market records (data.gov.in AGMARKNET), evaluates transparent crop-stage heuristics, generates an operational 7-day spray suitability schedule (`SAFE` / `CAUTION` / `AVOID`), and provides grounded multilingual Q&A in Marathi (`mr`), Hindi (`hi`), and English (`en`).

**Technical Architecture & Highlights:**
- **Frontend & Visualizations:** Streamlit (`app.py`), executive KPI metrics, responsive 7-day spray suitability card strip, interactive Plotly charts with agronomic decision thresholds (5mm spray avoid line, 36°C heat watch, 20 km/h spray drift line).
- **Location Geocoding (`core/sources.py`):** Open-Meteo Geocoding API with smart compound fallback: parses multi-token queries like `"Lasalgaon, Nashik"` or `"Baramati, MH"` to rank candidates by state/district hints and population.
- **Meteorological Adapter (`core/sources.py`):** Open-Meteo 7-Day Forecast API (daily max/min temp, precipitation sum, precipitation probability %, wind speed 10m max, and reference evapotranspiration ET₀).
- **Wholesale Mandi Adapter (`core/sources.py`):** Government of India AGMARKNET daily dataset with a **strict 4.5-second timeout**, 1 retry, and automatic district-to-state fallback.
- **Autonomous Agent Orchestrator (`core/agent.py`):** Explicit 6-step execution plan, high-resolution millisecond latency tracking (`latency_ms`), assertion-based validation gate, and graceful `PARTIAL_FALLBACK` handling if government APIs time out or return `"Resource lists"`.
- **Explainable Risk Engine (`core/risk_engine.py`):** Deterministic 0–100 heuristic risk scoring; evaluates heavy rain (≥50mm), heat stress (≥36°C / 40°C), wind drift (≥35 km/h), short dry spells, and specialized stage-sensitive triggers (`flowering_wet_stress`, `harvest_wet_risk`, `wet_spell`).
- **Grounded Multilingual Chat Router (`core/chat.py`):** Zero-hallucination intent router answering questions on spraying schedules, rainfall dates, temperature & irrigation (ET₀), risk score attribution, and mandi rates. Features 4 1-click suggested prompts per language.
- **Test Infrastructure:** 23 automated, offline-safe unit tests in `tests/` with 100% pass rate in <1.3 seconds.

**Strict Data-Integrity Guardrails:**
- Never hardcodes or fabricates mock weather or synthetic mandi prices.
- If data.gov.in is unconfigured or busy, the system transparently notes the partial fallback while continuing to deliver the complete weather and spraying advisory.
- Risk index is explicitly identified as an explainable heuristic decision-support tool (not a black-box ML model).
- Includes authoritative verification links to IMD Agromet (`mausam.imd.gov.in/agromet`).

---

## 3. Prototype Link

**Live Deployment URL:** [INSERT TESTED STREAMLIT COMMUNITY CLOUD URL]  
*(Tested headlessly on port 8501: HTTP 200 OK)*

---

## 4. Demo Video

**2–3 Minute Live Walkthrough:** [INSERT LOOM / YOUTUBE / DRIVE LINK]  
*(Choreographed precisely to 2:30 following `DEMO_SCRIPT.md`: Problem -> 1-Click Preset 1 Nashik -> 7-Day Spray Strip -> Grounded Marathi Q&A -> Telemetry & Partial Fallback Trace)*

---

## 5. GitHub Repository

**Public Repository URL:** [INSERT PUBLIC GITHUB URL]  
- Fully documented `README.md` with Mermaid architecture diagram.
- Clean `requirements.txt` and `.env.example`.
- Verified `.gitignore` ensuring zero secret leaks.
- Automated tests (`pytest -v` -> 23 passed in <1.3s).

---

## 6. Presentation / Pitch Deck

**Pitch Deck Share Link:** [INSERT GOOGLE SLIDES / CANVA / PDF LINK]  
*(6 executive slides: Title & Team, The Smallholder Problem, Technical Architecture, Explainable Risk Engine & Spray Schedule, Live Demo & Data Integrity Guardrails, Scalability & Roadmap)*
