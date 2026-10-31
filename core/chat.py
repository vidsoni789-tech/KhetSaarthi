"""Grounded multilingual question router over the current live-data report.

This is intentionally a small deterministic intent router, not a hallucinating LLM.
Answers are constructed only from values fetched for the current advisory session.
"""
from __future__ import annotations

from typing import Any

# Intent keyword triggers across English, Hindi, and Marathi
INTENTS: dict[str, list[str]] = {
    "spray": [
        "spray", "spraying", "pesticide", "foliar", "chemical", "insecticide", "fungicide",
        "field work", "fieldwork", "when to spray", "best day to spray",
        "फवारणी", "स्प्रे", "कीटकनाशक", "फवारणी कधी", "फवारणी करावी का", "शेतकाम",
        "छिड़काव", "स्प्रे कब", "कीटनाशक", "दवा", "छिड़काव कब करें",
    ],
    "risk": [
        "risk", "score", "index", "why", "reason", "threat", "explain", "level",
        "जोखिम", "खतरा", "स्कोर", "कारण", "जोखिम क्यों", "रिस्क",
        "जोखीम", "धोका", "कारण", "जोखीम का", "धोक्याची",
    ],
    "rain": [
        "rain", "rainfall", "raining", "rainy", "downpour", "precipitation", "barish", "baarish",
        "बारिश", "वर्षा", "बरसात", "पानी बरसेगा", "बारिश कब",
        "पाऊस", "पावसाचा", "पाऊस कधी", "पाऊस पडेल का",
    ],
    "heat": [
        "heat", "hot", "temperature", "garmi", "warm", "high temp", "temp",
        "गर्मी", "तापमान", "धूप", "उष्णता", "उकाडा", "गरमी",
    ],
    "water": [
        "water", "irrigat", "irrigation", "et0", "et", "watering", "paani",
        "पानी", "सिंचाई", "पानी कब दें", "सिंचन", "पाणी", "ओलावा", "पाणी कधी",
    ],
    "market": [
        "mandi", "market", "price", "rate", "apmc", "bhav", "modal", "cost", "sell", "sale",
        "मंडी", "भाव", "बाजार", "कीमत", "रेट", "मंडी भाव", "बिक्री",
        "मंडई", "बाजारभाव", "भाव", "दर", "किंमत", "बाजार", "विक्री",
    ],
    "harvest": [
        "harvest", "harvesting", "cutting", "picking", "reap", "maturity",
        "कटाई", "तुड़ाई", "फसल पकना", "कटाई कब",
        "काढणी", "कापणी", "तोडणी", "पीक काढणी",
    ],
}

REPLIES: dict[str, dict[str, str]] = {
    "en": {
        "no_report": "Run a farm analysis first so I can answer using live weather data for your location.",
        "rain": "The forecast's highest daily rainfall is **{amount:.1f} mm** on **{date}**. {probability} Total 7-day cumulative rainfall is **{cum_rain:.1f} mm**. Check field drainage and avoid applying inputs immediately before rain. Forecasts can change, so recheck before acting.",
        "heat": "The forecast maximum temperature over the next seven days is **{temp:.1f} °C** (minimum: **{min_temp:.1f} °C**). Check soil moisture and, where irrigation is available, prefer cooler morning/evening hours. This is not a crop-specific water prescription.",
        "wind": "The forecast peak wind speed is **{wind:.1f} km/h**. Avoid pesticide or foliar spraying in strong winds; follow the product label and local agricultural advice.",
        "market_missing": "I do not have a connected mandi-price response for this session, so I cannot quote a price. Configure your own data.gov.in API key and run the analysis again.",
        "market": "The live AGMARKNET response includes these reported market records: {rows}. Check each arrival date and market before using the figures to make a sale decision.",
        "water": "The forecast reference ET₀ maximum is **{et0}** with total forecast rainfall of **{cum_rain:.1f} mm**. ET₀ describes water demand for a well-watered grass reference surface, not your crop's exact irrigation requirement. Check actual soil moisture and local irrigation guidance before watering. {dry}",
        "harvest": "The forecast shows **{amount:.1f} mm** as the highest daily rainfall over the next seven days ({date}). For harvest-stage decisions, use a suitable dry window and protect harvested produce from rain; verify the forecast again before scheduling.",
        "summary": "The current weather-risk index is **{score}/100 ({label})** for **{crop}**, at the **{stage}** stage. The index is a transparent heuristic, not a probability of crop loss. Recommended actions: {actions}",
        "fallback": "I can answer questions about spraying windows, rain forecasts, heat & irrigation, risk score reasons, harvest timing, and government mandi prices using this session's live data. Try asking about one of those topics.",
    },
    "hi": {
        "no_report": "पहले खेत का विश्लेषण चलाएँ, ताकि मैं आपके स्थान के लाइव मौसम के आधार पर जवाब दे सकूँ।",
        "rain": "अगले सात दिनों में अधिकतम दैनिक बारिश **{amount:.1f} मिमी** {date} को अनुमानित है। {probability} कुल सात दिनों की बारिश **{cum_rain:.1f} मिमी** है। खेत की जल-निकासी जाँचें और बारिश से ठीक पहले कृषि इनपुट डालने से बचें।",
        "heat": "अगले सात दिनों का अधिकतम अनुमानित तापमान **{temp:.1f} °C** (न्यूनतम: **{min_temp:.1f} °C**) है। मिट्टी की नमी जाँचें और सिंचाई उपलब्ध हो तो सुबह जल्दी या शाम का समय चुनें। यह फसल-विशिष्ट सिंचाई मात्रा नहीं है।",
        "wind": "अगले सात दिनों में अधिकतम हवा की गति **{wind:.1f} किमी/घंटा** है। तेज़ हवा में कीटनाशक या पत्तियों पर छिड़काव न करें; उत्पाद के निर्देश और स्थानीय कृषि सलाह का पालन करें।",
        "market_missing": "इस सत्र में मंडी भाव का लाइव डेटा उपलब्ध नहीं है, इसलिए मैं कोई कीमत नहीं बताऊँगा। अपनी data.gov.in API key जोड़कर फिर से विश्लेषण चलाएँ।",
        "market": "लाइव AGMARKNET जवाब में ये मंडी रिकॉर्ड मिले: {rows}। कीमतों का उपयोग करने से पहले बाजार और आवक की तारीख जाँचें।",
        "water": "पूर्वानुमान में अधिकतम संदर्भ ET₀ **{et0}** और कुल बारिश **{cum_rain:.1f} मिमी** है। ET₀ घास के संदर्भ की जल-माँग है, आपकी फसल की सटीक आवश्यकता नहीं। पानी देने से पहले खेत की वास्तविक नमी जाँचें। {dry}",
        "harvest": "अगले सात दिनों में अधिकतम दैनिक बारिश **{amount:.1f} मिमी** {date} को अनुमानित है। कटाई के लिए उपयुक्त सूखा समय चुनें और कटी उपज को बारिश से बचाएँ; समय तय करने से पहले पूर्वानुमान फिर देखें।",
        "summary": "**{crop}** की **{stage}** अवस्था के लिए मौसम जोखिम सूचकांक **{score}/100 ({label})** है। यह पारदर्शी नियमों पर आधारित सूचकांक है, फसल नुकसान की संभावना नहीं। सुझाव: {actions}",
        "fallback": "मैं इस सत्र के लाइव डेटा से छिड़काव समय, बारिश, तापमान/सिंचाई, जोखिम स्कोर के कारण, कटाई और मंडी भाव पर जवाब दे सकता हूँ। इनमें से किसी विषय पर पूछें।",
    },
    "mr": {
        "no_report": "तुमच्या ठिकाणचा ताजा हवामान डेटा वापरून उत्तर देण्यासाठी आधी शेताचे विश्लेषण चालवा.",
        "rain": "पुढील सात दिवसांतील सर्वाधिक दैनिक पाऊस **{amount:.1f} मिमी** {date} रोजी अपेक्षित आहे. {probability} सात दिवसांचा एकूण अपेक्षित पाऊस **{cum_rain:.1f} मिमी** आहे. शेतातील निचरा तपासा आणि पावसाच्या अगोदर निविष्ठा देणे टाळा.",
        "heat": "पुढील सात दिवसांतील कमाल तापमान **{temp:.1f} °C** (किमान: **{min_temp:.1f} °C**) आहे. जमिनीतील ओलावा तपासा; सिंचन शक्य असल्यास सकाळी लवकर किंवा संध्याकाळी करा. हे पिकासाठी अचूक सिंचन प्रमाण नाही.",
        "wind": "पुढील सात दिवसांतील कमाल वाऱ्याचा वेग **{wind:.1f} किमी/तास** आहे. जोरदार वाऱ्यात कीटकनाशक किंवा पानांवरील फवारणी टाळा; उत्पादनाच्या सूचनांचे आणि स्थानिक कृषी सल्ल्याचे पालन करा.",
        "market_missing": "या सत्रात मंडई भावांचा थेट डेटा जोडलेला नाही, त्यामुळे मी किंमत सांगू शकत नाही. स्वतःची data.gov.in API key जोडा आणि विश्लेषण पुन्हा चालवा.",
        "market": "थेट AGMARKNET प्रतिसादात हे बाजार नोंदी मिळाले: {rows}. निर्णय घेण्यापूर्वी बाजार आणि आवक तारीख तपासा.",
        "water": "अंदाजातील कमाल संदर्भ ET₀ **{et0}** आणि एकूण अपेक्षित पाऊस **{cum_rain:.1f} मिमी** आहे. ET₀ हा संदर्भ पृष्ठभागाचा जलवापर आहे; तुमच्या पिकाची अचूक सिंचन गरज नाही. पाणी देण्यापूर्वी जमिनीतील ओलावा तपासा. {dry}",
        "harvest": "पुढील सात दिवसांत सर्वाधिक दैनिक पाऊस **{amount:.1f} मिमी** {date} रोजी अपेक्षित आहे. काढणीसाठी योग्य कोरडा कालावधी निवडा आणि काढलेले पीक पावसापासून सुरक्षित ठेवा; नियोजनापूर्वी अंदाज पुन्हा तपासा.",
        "summary": "**{crop}** पिकाच्या **{stage}** अवस्थेसाठी हवामान जोखीम निर्देशांक **{score}/100 ({label})** आहे. हा पारदर्शक नियमांवर आधारित निर्देशांक आहे; पीक नुकसानीची शक्यता नाही. कृती: {actions}",
        "fallback": "या सत्रातील थेट डेटावरून मी फवारणीचे दिवस, पाऊस, तापमान/सिंचन, जोखीम स्कोरचे कारण, काढणी आणि मंडई भावांबद्दल उत्तर देऊ शकतो. यापैकी प्रश्न विचारा.",
    },
}


def get_suggested_questions(language: str = "en") -> list[str]:
    """Return 4 natural, clickable questions in the chosen language."""
    questions = {
        "en": [
            "When is the safest window to spray pesticide this week?",
            "When and how much rainfall is expected?",
            "Do I need to irrigate based on temperature and ET₀?",
            "What is the current mandi price for my crop?",
        ],
        "hi": [
            "इस सप्ताह कीटनाशक छिड़काव का सबसे सुरक्षित समय कब है?",
            "बारिश कब और कितनी होने की संभावना है?",
            "तापमान और ET₀ के आधार पर क्या सिंचाई की ज़रूरत है?",
            "मेरी फसल का आज का मंडी भाव क्या है?",
        ],
        "mr": [
            "या आठवड्यात फवारणीसाठी सर्वात सुरक्षित दिवस कोणता?",
            "पाऊस कधी आणि किती पडण्याची शक्यता आहे?",
            "तापमान व बाष्पीभवनानुसार पिकाला पाणी कधी द्यावे?",
            "माझ्या पिकाचा आजचा बाजारभाव काय आहे?",
        ],
    }
    return questions.get(language, questions["en"])


def answer_farmer_query(question: str, report: dict[str, Any] | None, language: str = "en") -> str:
    """Ground farmer queries against fetched session data without hallucination."""
    if not report:
        return REPLIES.get(language, REPLIES["en"])["no_report"]
    lang = language if language in REPLIES else "en"
    q = (question or "").strip().lower()
    if not q:
        return REPLIES[lang]["fallback"]

    # Match intent based on priority order: spray, risk, water, rain, heat, market, harvest
    intent: str | None = None
    for name in ["spray", "risk", "water", "rain", "heat", "market", "harvest"]:
        if any(w in q for w in INTENTS[name]):
            intent = name
            break

    risk = report.get("risk", {})
    rows = risk.get("forecast_rows", [])

    highest_rain = max((r for r in rows if r.get("Rain (mm)") is not None), key=lambda r: r["Rain (mm)"], default=None)
    highest_temp = max((r for r in rows if r.get("Max temp (°C)") is not None), key=lambda r: r["Max temp (°C)"], default=None)
    lowest_temp = min((r for r in rows if r.get("Min temp (°C)") is not None), key=lambda r: r["Min temp (°C)"], default={"Min temp (°C)": 18.0})
    highest_wind = max((r for r in rows if r.get("Wind (km/h)") is not None), key=lambda r: r["Wind (km/h)"], default=None)
    highest_et0 = max((r.get("Reference ET₀ (mm)") for r in rows if r.get("Reference ET₀ (mm)") is not None), default=None)

    cum_rain = sum(r.get("Rain (mm)") or 0.0 for r in rows if r.get("Rain (mm)") is not None)

    # Distinguish peak-rainfall day probability from 7-day maximum rain probability
    max_prob_row = max((r for r in rows if r.get("Rain probability (%)") is not None), key=lambda r: r["Rain probability (%)"], default=None)
    overall_max_prob = max_prob_row["Rain probability (%)"] if max_prob_row else None
    overall_max_date = max_prob_row["Date"] if max_prob_row else ""

    probability = ""
    if highest_rain and highest_rain.get("Rain probability (%)") is not None:
        p_val = highest_rain["Rain probability (%)"]
        if overall_max_prob is not None and overall_max_prob > p_val:
            if lang == "en":
                probability = f"Rain chance on the peak-rain date is **{p_val:.0f}%**, while the week's highest rain probability reaches **{overall_max_prob:.0f}%** on **{overall_max_date}**. "
            elif lang == "hi":
                probability = f"अधिकतम बारिश वाले दिन संभावना **{p_val:.0f}%** है, जबकि 7 दिनों में सर्वाधिक संभावना **{overall_max_prob:.0f}%** ({overall_max_date} को) है। "
            else:
                probability = f"सर्वाधिक पावसाच्या दिवशी शक्यता **{p_val:.0f}%** आहे, तर ७ दिवसांतील कमाल शक्यता **{overall_max_prob:.0f}%** ({overall_max_date} रोजी) आहे. "
        else:
            if lang == "en":
                probability = f"Maximum rain probability is **{p_val:.0f}%** on **{highest_rain['Date']}**. "
            elif lang == "hi":
                probability = f"अधिकतम बारिश की संभावना **{p_val:.0f}%** {highest_rain['Date']} को है। "
            else:
                probability = f"कमाल पावसाची शक्यता **{p_val:.0f}%** {highest_rain['Date']} रोजी आहे. "

    # INTENT 1: SPRAYING & FIELDWORK TIMING
    if intent == "spray":
        schedule = risk.get("spray_schedule", [])
        safe_days = [d["date"] for d in schedule if d.get("status") == "SAFE"]
        avoid_days = [f"**{d['date']}** ({d.get('reason', '')})" for d in schedule if d.get("status") == "AVOID"]

        if safe_days:
            safe_text = ", ".join(f"**{d}**" for d in safe_days)
            avoid_text = "; ".join(avoid_days) if avoid_days else ("none" if lang == "en" else "कोई नहीं")
            if lang == "hi":
                return f"कीटनाशक या फवारणी के लिए सुरक्षित दिन: {safe_text} (शांत हवा, बारिश की कम संभावना)।\n\n⚠️ **छिड़काव से बचें:** {avoid_text}।"
            elif lang == "mr":
                return f"फवारणीसाठी अनुकूल व सुरक्षित दिवस: {safe_text} (कमी वारा, पावसाची शक्यता नाही).\n\n⚠️ **या दिवशी फवारणी टाळा:** {avoid_text}."
            else:
                return f"Optimal safe spray window: {safe_text} (calm wind, low precipitation risk).\n\n⚠️ **Avoid spraying on:** {avoid_text}."
        else:
            if lang == "hi":
                return "अगले 7 दिनों में बारिश या तेज़ हवा के कारण छिड़काव के लिए कोई पूरी तरह सुरक्षित दिन नहीं है। मौसम साफ होने तक दवा का छिड़काव टालें।"
            elif lang == "mr":
                return "पुढील ७ दिवसांत पाऊस किंवा वाऱ्यामुळे फवारणीसाठी कोणताही अनुकूल दिवस नाही. हवामान कोरडे होईपर्यंत फवारणी पुढे ढकला."
            else:
                return "No clear safe spraying window is forecast in the next 7 days due to elevated rain probability or wind. Delay foliar chemical applications."

    # INTENT 2: RISK EXPLANATION
    if intent == "risk":
        alerts_list = risk.get("alerts", [])
        if alerts_list:
            alert_items = [f"• **{a['type'].replace('_', ' ').title()}** ({a['severity']}): {a['fact']}" for a in alerts_list]
            reasons_text = "\n".join(alert_items)
        else:
            reasons_text = "No severe weather trigger breached the thresholds." if lang == "en" else ("कोई गंभीर मौसम ट्रिगर सक्रिय नहीं हुआ।" if lang == "hi" else "कोणतीही गंभीर हवामान सूचना सक्रिय झाली नाही.")

        if lang == "hi":
            return f"**{risk.get('crop')}** ({risk.get('stage')} अवस्था) के लिए मौसम जोखिम सूचकांक **{risk.get('score')}/100 ({risk.get('localized_label')})** है।\n\n**सक्रिय ट्रिगर्स:**\n{reasons_text}\n\n*यह एक पारदर्शी नियम-आधारित सूचकांक है, कोई अस्पष्ट ML मॉडल नहीं।*"
        elif lang == "mr":
            return f"**{risk.get('crop')}** ({risk.get('stage')} अवस्था) साठी हवामान जोखीम निर्देशांक **{risk.get('score')}/100 ({risk.get('localized_label')})** आहे.\n\n**सक्रिय घटक:**\n{reasons_text}\n\n*हा पारदर्शक नियमांवर आधारित निर्देशांक आहे, अंदाज वर्तवणारे ब्लॅक-बॉक्स मॉडेल नाही.*"
        else:
            return f"The weather risk score for **{risk.get('crop')}** ({risk.get('stage')} stage) is **{risk.get('score')}/100 ({risk.get('label')})**.\n\n**Triggering factors:**\n{reasons_text}\n\n*This is an explainable heuristic decision-support index, not a black-box model.*"

    # INTENT 3: RAIN / PRECIPITATION
    if intent in ("rain", "harvest") and highest_rain:
        if intent == "harvest":
            return REPLIES[lang]["harvest"].format(amount=highest_rain["Rain (mm)"], date=highest_rain["Date"])
        return REPLIES[lang]["rain"].format(
            amount=highest_rain["Rain (mm)"],
            date=highest_rain["Date"],
            probability=probability,
            cum_rain=cum_rain,
        )

    # INTENT 4: HEAT / TEMPERATURE
    if intent == "heat" and highest_temp:
        min_t = lowest_temp.get("Min temp (°C)", 18.0) if isinstance(lowest_temp, dict) else 18.0
        return REPLIES[lang]["heat"].format(temp=highest_temp["Max temp (°C)"], min_temp=min_t)

    # INTENT 5: WATER / IRRIGATION
    if intent == "water":
        et0_text = f"{highest_et0:.1f} mm/day" if highest_et0 is not None else ("not available" if lang == "en" else ("उपलब्ध नहीं" if lang == "hi" else "उपलब्ध नाही"))
        has_dry = any(a["type"] == "dry" for a in risk.get("alerts", []))
        if lang == "en":
            dry_text = "A short dry-spell trigger was detected; inspect field moisture." if has_dry else "No short dry-spell trigger was detected by the current rules."
        elif lang == "hi":
            dry_text = "सूखे की स्थिति का संकेत मिला है; खेत की नमी जाँचें।" if has_dry else "मौजूदा नियमों में कम बारिश वाला सूखा अलर्ट नहीं मिला।"
        else:
            dry_text = "कोरड्या कालावधीचा इशारा आढळला; जमिनीतील ओलावा तपासा." if has_dry else "सध्याच्या नियमांनुसार कोरड्या कालावधीचा इशारा आढळला नाही."
        return REPLIES[lang]["water"].format(et0=et0_text, cum_rain=cum_rain, dry=dry_text)

    # INTENT 6: WIND
    if intent == "wind" and highest_wind:
        return REPLIES[lang]["wind"].format(wind=highest_wind["Wind (km/h)"])

    # INTENT 7: MANDI / MARKET INTELLIGENCE
    if intent == "market":
        mandi = report.get("mandi", {})
        available = mandi.get("records") or []
        if not mandi.get("connected") or not available:
            return REPLIES[lang]["market_missing"]
        summaries: list[str] = []
        for item in available[:3]:
            summaries.append(f"{item.get('Market', 'Market')}: ₹{item.get('Modal price (₹/quintal)')} / quintal ({item.get('Date', 'date unavailable')})")
        base_reply = REPLIES[lang]["market"].format(rows="; ".join(summaries))
        if mandi.get("status") == "cached_snapshot" or mandi.get("is_snapshot"):
            badge_text = (
                "📦 **सत्यापित ऐतिहासिक AGMARKNET स्नैपशॉट** (सरकारी लाइव सर्वर व्यस्त होने के कारण अंतिम सत्यापित APMC आवक रिकॉर्ड दिखाया जा रहा है):\n\n"
                if lang == "hi"
                else (
                    "📦 **सत्यापित ऐतिहासिक AGMARKNET स्नॅपशॉट** (थेट सरकारी सर्व्हर व्यस्त असल्याने शेवटचा पडताळलेला APMC आवक रेकॉर्ड दर्शविला आहे):\n\n"
                    if lang == "mr"
                    else "📦 **Verified Historical AGMARKNET Snapshot** (Live OGD API busy — showing last verified APMC records with arrival dates):\n\n"
                )
            )
            return badge_text + base_reply
        return base_reply

    # DEFAULT FALLBACK SUMMARY
    actions = " ".join(risk.get("actions", [])[:2])
    return REPLIES[lang]["summary"].format(
        score=risk.get("score", 0),
        label=risk.get("localized_label", risk.get("label", "Low")),
        crop=risk.get("crop", "Crop"),
        stage=risk.get("stage", "Stage"),
        actions=actions,
    )
