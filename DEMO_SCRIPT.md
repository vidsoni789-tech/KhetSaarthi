# 🎙️ KhetSaarthi — 2 to 3 Minute Live Pitch & Demo Script

**Target Time:** 2 minutes 30 seconds  
**Demo Target:** Judges & Hackathon Evaluators  
**Live URL:** [Insert Streamlit Community Cloud URL]

---

## ⏱️ Live Demonstration Choreography

### 0:00 – 0:30 | The Problem & Our Unique Value Proposition (USP)
> *"Judges, smallholder farmers in India don't suffer from a lack of data — they suffer from fragmented data. A farmer gets a weather forecast in millimeters, a mandi rate from a distant market, and agronomic guidelines in a PDF. None of them talk to each other.*
>
> *Meet **KhetSaarthi 🌱** — an autonomous agricultural risk and resource advisory agent. It ingests live 7-day weather forecasts and daily government AGMARKNET wholesale prices, runs explainable crop-stage risk rules, generates a daily field-work spray schedule, and answers farmer questions in their native language with zero hallucination."*

---

### 0:30 – 1:15 | 1-Click Demo Preset 1: Nashik (Flowering Wet Stress in Marathi)
*(Action: Click the sidebar button: **'🌱 Preset 1: Nashik (Flowering Wet Stress)'**)*

> *"Notice how the app loads in under 2 seconds. The agent has resolved Nashik, Maharashtra, fetched live 7-day meteorological data from Open-Meteo, attempted the government mandi feed, and evaluated crop-stage rules in Marathi.*
>
> *Look at our **Top KPI Strip**:*
> 1. *Location: Nashik (19.997°N, 73.791°E).*
> 2. *Risk Score: **18/100 (कमी - Low)**. But notice it's not zero! A naive model would say 3 to 4mm rain is safe. But our engine knows this Soybean crop is in its **Flowering stage**.*
> 3. *Alert: Because of an **82% rain chance** across 4 consecutive damp days, the agent flags elevated flower drop and fungal blight risks!*
>
> *Right below is our killer feature — the **7-Day Spray Suitability Schedule**:*
> *Today, Oct 31, is marked **✅ सुरक्षित (SAFE)** with 1.3mm and calm 12 km/h winds. But Nov 1 to Nov 3 are explicitly marked **❌ फवारणी टाळा (AVOID)** due to 75% to 82% rain probability. A farmer knows exactly what to do today without calculating weather math."*

---

### 1:15 – 1:45 | Grounded Multilingual Q&A & Threshold Plotly Charts
*(Action: Scroll down to **Ask KhetSaarthi** and click the first 1-click prompt: **'या आठवड्यात फवारणीसाठी सर्वात सुरक्षित दिवस कोणता?'**)*

> *"Farmers don't want to type complex prompts on a mobile keyboard. We provide 1-click grounded questions.*
>
> *I click the spray question in Marathi. Instantly — with **zero network latency** because it references our cached session data — it replies:*
> *'फवारणीसाठी अनुकूल दिवस: 2026-10-31, 2026-11-05, 2026-11-06. टाळा: 2026-11-01, 2026-11-02, 2026-11-03.'*
>
> *Notice that every single number quoted by the assistant matches the exact forecast rows. It does not use a black-box LLM to hallucinate fake weather.*
>
> *On the right, our Plotly charts feature **agronomic decision thresholds**: a 5mm horizontal line showing spray limits, a 36°C heat stress threshold, and a 20 km/h spray drift line."*

---

### 1:45 – 2:30 | Agent Autonomy, Graceful Resilience & Trust
*(Action: Expand the **'🔍 Agent Execution Trace & Telemetry'** expander)*

> *"Finally, let's inspect the engine under the hood. Our agent orchestrator doesn't hide behind a spinner.*
>
> *In the execution trace, you see each tool call with exact execution latencies in milliseconds:*
> 1. *`geocode`: Open-Meteo resolved in ~600ms.*
> 2. *`weather`: 7-day daily forecast retrieved in ~600ms.*
> 3. *`mandi`: When the government data.gov.in endpoint returned 'Resource lists' or timed out, our custom session enforced a strict **4.5-second timeout** and automatically logged a **`PARTIAL_FALLBACK`**.*
>
> *It did not crash. It did not invent a fake ₹4,500 market price. It delivered the full weather advisory and told the farmer honestly to check their local APMC.*
>
> *We have 23 automated unit tests, strict model honesty, and verification links to IMD Agromet.*
> *KhetSaarthi delivers real, practical, resilient intelligence to Indian agriculture. Thank you!"*

---

## 🎯 Anticipated Judge Q&A & Winning Rebuttals

### Q1: "Why did you use deterministic rules instead of training a deep learning or XGBoost model?"
**Answer:**
> *"In agronomy, trust and explainability are life-and-death matters for smallholders. An XGBoost model trained on historical data cannot explain to a farmer why today's 4mm rain at flowering warrants delaying pesticide application. Our rules-based heuristic is 100% deterministic, audit-proof, and can be customized to local Agricultural University (KVK) guidelines without retraining or data drift risks."*

### Q2: "What prevents your chat assistant from hallucinating numbers?"
**Answer:**
> *"The chat module is an intent-based router strictly bounded to the session's verified report dictionary. It pulls directly from `report['risk']['spray_schedule']` and `report['risk']['forecast_rows']`. If a value isn't present in the live API response, the system is hardcoded to state that the data is unavailable rather than generating a statistical guess."*

### Q3: "What happens if a farmer enters a remote village or misspelled name like 'Lasalgaon, Nashik'?"
**Answer:**
> *"We built Smart Geocoding Fallback in `core/sources.py`. If Open-Meteo returns zero results for a compound query, our algorithm automatically splits the tokens, queries the primary locality name, and ranks candidates based on state and district hints (`admin1`, `admin2`) and population. You can test this right now with Preset 3!"*

### Q4: "What happens when data.gov.in AGMARKNET goes down or takes 30 seconds to respond?"
**Answer:**
> *"Most apps freeze or crash when government portals lag. We built a dedicated `_mandi_session()` with a strict 4.5-second timeout and 1 retry. If the API is busy or unconfigured, the agent executes a `PARTIAL_FALLBACK`, logs the latency in the execution trace, and continues delivering the essential weather and spraying advisory without delay."*
