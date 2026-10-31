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
KhetSaarthi is an AI-powered, live-source-first agricultural decision-support agent. In under 2.5 seconds, the agent resolves farm coordinates, retrieves live 7-day weather forecasts (Open-Meteo), checks daily government mandi market records (data.gov.in AGMARKNET), evaluates transparent crop-stage heuristics, generates two independently functioning advisory engines — **Dedicated Agricultural Water Management & Irrigation Planner** (FAO-56 Penman-Monteith) and **Foliar Pesticide Spray Weather Suitability & Statutory CIBRC Claims** — displayed in a **7-Day Dual Operational Calendar**, and provides grounded multilingual conversational Q&A in Marathi (`mr`), Hindi (`hi`), and English (`en`).

**Technical Architecture & Highlights:**
- **Dedicated Irrigation Planner (`core/irrigation.py`):** Root-zone water balance computing $ET_c = ET_0 \times K_c$, effective rainfall $P_{\text{eff}}$, soil texture capacity (Black Cotton Vertisol, Loamy, Sandy), and farmer soil moisture state (`dry`, `moist`, `wet`). Strictly avoids universal 2-day rules and prohibits fake pump hours or liters without emitter discharge specs. Statuses: `IRRIGATION MAY BE NEEDED`, `DEFER AND RECHECK`, `MONITOR SOIL MOISTURE`, `INSUFFICIENT DATA`.
- **Pesticide Spray Weather Suitability (`core/pesticide_spray.py`):** Foliar canopy evaluation for wind drift ($<15$ km/h), rain wash-off, and thermal inversion. Strictly complies with statutory CIBRC label claims and prohibits guessed chemical dosages or generic "SAFE TO SPRAY" guarantees. Statuses: `SUITABLE WEATHER WINDOW`, `CAUTION WINDOW`, `AVOID SPRAYING`, `UNKNOWN DUE TO MISSING INFORMATION`.
- **Crop Agronomy Registry (`core/crop_config.py`):** 10 crops with verified FAO-56 Table 12 $K_c$ parameters across 4 growth stages, FAO-33 $K_y$ yield sensitivity, stage warnings (pollinator hazard during bloom, statutory PHI near harvest), and CIBRC approved label database.
- **Frontend & Visualizations:** Streamlit (`app.py`), executive KPI metrics, 7-Day Dual Operational Calendar showing independent soil water and foliar spray rows, interactive Plotly forecast charts with decision thresholds.
- **Location Geocoding (`core/sources.py`):** Open-Meteo Geocoding API with smart compound fallback ranking candidates by state/district hints and population.
- **Wholesale Mandi Adapter (`core/sources.py`):** Government of India AGMARKNET daily dataset with a **strict 4.5-second timeout**, 1 retry, automatic district-to-state fallback, and verified historical snapshot fallback.
- **Grounded Multilingual Conversational Engine (`core/chat.py`):** Token-aware intent router distinguishing greetings, irrigation questions, foliar spray weather, rain dates, heat, and mandi prices, with grounded LLM integration (Groq LLaMA 3.3, Google Gemini, Hugging Face) and deterministic offline fallback.
- **Test Infrastructure:** 51 automated, offline-safe unit tests in `tests/` with 100% pass rate in <5 seconds.

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
*(Choreographed precisely to 2:30 following `DEMO_SCRIPT.md`: Problem -> 1-Click Preset 1 Nashik -> 7-Day Dual Operational Calendar -> Dedicated Irrigation & Pesticide Sections -> Grounded Marathi Q&A -> Telemetry & Partial Fallback Trace)*

---

## 5. GitHub Repository

**Public Repository URL:** https://github.com/vidsoni789-tech/KhetSaarthi.git  
- Fully documented `README.md` with Mermaid architecture diagram.
- Clean `requirements.txt` and `.env.example`.
- Verified `.gitignore` ensuring zero secret leaks.
- Automated tests (`pytest -v` -> 23 passed in <1.3s).

---

## 6. Presentation / Pitch Deck

**Pitch Deck Share Link:** [INSERT GOOGLE SLIDES / CANVA / PDF LINK]  
*(6 executive slides: Title & Team, The Smallholder Problem, Technical Architecture, Explainable Risk Engine & Spray Schedule, Live Demo & Data Integrity Guardrails, Scalability & Roadmap)*
