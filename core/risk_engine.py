"""Transparent weather-risk scoring, crop-stage advisory rules, and spray suitability engine.

This is an explainable heuristic decision-support index, not a trained ML model
or an official crop-specific forecast.
"""
from __future__ import annotations

from typing import Any

RISK_LABELS = {
    "en": {"Low": "Low", "Moderate": "Moderate", "High": "High", "Severe": "Severe"},
    "hi": {"Low": "कम", "Moderate": "मध्यम", "High": "अधिक", "Severe": "गंभीर"},
    "mr": {"Low": "कमी", "Moderate": "मध्यम", "High": "जास्त", "Severe": "गंभीर"},
}

SPRAY_STATUS_LABELS = {
    "en": {"SAFE": "Safe to Spray", "CAUTION": "Exercise Caution", "AVOID": "Avoid Spraying"},
    "hi": {"SAFE": "छिड़काव के लिए सुरक्षित", "CAUTION": "सावधानी बरतें", "AVOID": "छिड़काव से बचें"},
    "mr": {"SAFE": "फवारणीसाठी सुरक्षित", "CAUTION": "काळजीपूर्वक फवारणी करा", "AVOID": "फवारणी टाळा"},
}

ALERT_TITLES = {
    "en": {
        "heavy_rain": "Heavy Rainfall Risk",
        "rain": "Rainfall Watch",
        "heat": "High Temperature Warning",
        "wind": "High Wind Speed",
        "dry": "Dry Spell Stress",
        "flowering_wet_stress": "Flowering Stage Wet Stress",
        "harvest_wet_risk": "Harvest Moisture Risk",
        "wet_spell": "Persistent Damp Spell",
    },
    "hi": {
        "heavy_rain": "भारी बारिश का खतरा",
        "rain": "बारिश की चेतावनी",
        "heat": "अत्यधिक तापमान चेतावनी",
        "wind": "तेज़ हवा का जोखिम",
        "dry": "सूखे का तनाव",
        "flowering_wet_stress": "फूल अवस्था में नमी का तनाव",
        "harvest_wet_risk": "कटाई अवस्था में नमी का खतरा",
        "wet_spell": "लगातार नम मौसम की स्थिति",
    },
    "mr": {
        "heavy_rain": "मुसळधार पावसाचा धोका",
        "rain": "पावसाचा इशारा",
        "heat": "अतिउष्णतेची चेतावनी",
        "wind": "जोरदार वाऱ्याचा धोका",
        "dry": "कोरड्या हवामानाचा ताण",
        "flowering_wet_stress": "फुलोरा अवस्थेत दमट हवामानाचा ताण",
        "harvest_wet_risk": "काढणी अवस्थेत अवकाळी पावसाचा धोका",
        "wet_spell": "सलग दमट व ढगाळ हवामान",
    },
}

TEXT = {
    "en": {
        "heavy_rain": "Heavy rain is forecast. Keep field drainage channels clear; avoid irrigation and postpone spraying until a suitable dry window.",
        "rain": "Rain is forecast. Check field drainage and avoid applying inputs immediately before rainfall.",
        "heat": "High temperatures are forecast. Check soil moisture and, where irrigation is available, prefer cooler morning/evening hours.",
        "wind": "Strong winds are forecast. Avoid pesticide or foliar spraying during windy conditions to reduce drift.",
        "dry": "A short dry spell is forecast. Inspect soil moisture before irrigating; avoid unnecessary watering.",
        "flowering_wet_stress": "Cloudy, damp weather during flowering increases flower drop and fungal blight risks. Spray only during verified dry/calm intervals.",
        "harvest_wet_risk": "Rain during harvest/maturity threatens mold and grain/bulb discoloration. Cover harvested produce and harvest in dry windows.",
        "wet_spell": "Persistent cloudy and damp conditions forecast. Inspect crops for moisture stress and early foliar disease symptoms.",
        "sowing": "Sowing stage: check field moisture and workability, and follow the locally recommended sowing window for this crop.",
        "vegetative": "Vegetative stage: inspect for waterlogging, lodging and pest/disease symptoms after significant weather changes.",
        "flowering": "Flowering stage: monitor moisture stress closely; avoid field operations or spraying during extreme heat or strong winds.",
        "maturity": "Maturity/harvest stage: use a dry-weather window for harvest and safe drying; protect harvested produce from rain.",
        "general": "Recheck the forecast and your field conditions before acting. Local soil, irrigation and crop variety can change the best decision.",
    },
    "hi": {
        "heavy_rain": "भारी बारिश का पूर्वानुमान है। खेत की जल-निकासी साफ रखें; सिंचाई न करें और छिड़काव के लिए बारिश के बाद का उपयुक्त सूखा समय चुनें।",
        "rain": "बारिश का पूर्वानुमान है। खेत की जल-निकासी जाँचें और बारिश से ठीक पहले कृषि इनपुट डालने से बचें।",
        "heat": "अधिक तापमान का पूर्वानुमान है। मिट्टी की नमी जाँचें और सिंचाई उपलब्ध हो तो सुबह जल्दी या शाम का समय चुनें।",
        "wind": "तेज़ हवा का पूर्वानुमान है। हवा तेज़ होने पर कीटनाशक या पत्तियों पर छिड़काव न करें, ताकि दवा उड़कर न जाए।",
        "dry": "कुछ दिनों तक सूखा रहने की संभावना है। सिंचाई से पहले मिट्टी की नमी जाँचें; अनावश्यक पानी न दें।",
        "flowering_wet_stress": "फूल आने की अवस्था में नम व ढगाळ मौसम से फूल गिरने और फफूंद का खतरा बढ़ता है। केवल शांत व सूखे समय में छिड़काव करें।",
        "harvest_wet_risk": "कटाई अवस्था में बेमौसमी बारिश से उपज खराब होने और रंग बिगड़ने का खतरा है। कटी फसल को तिरपाल से ढकें।",
        "wet_spell": "लगातार नम और बादल छाए रहने का पूर्वानुमान है। फसल में फफूंद और कीट के शुरुआती लक्षणों की निगरानी करें।",
        "sowing": "बुवाई अवस्था: मिट्टी की नमी और खेत की स्थिति जाँचें तथा फसल के लिए स्थानीय अनुशंसित बुवाई समय अपनाएँ।",
        "vegetative": "विकास अवस्था: मौसम बदलने या तेज़ बारिश के बाद जलभराव, फसल गिरने और कीट/रोग के लक्षण देखें।",
        "flowering": "फूल आने की अवस्था: नमी की कमी पर ध्यान दें; तेज़ गर्मी या हवा में खेत का काम और छिड़काव टालें।",
        "maturity": "पकने/कटाई की अवस्था: कटाई और सुखाने के लिए सूखे मौसम का समय चुनें; कटी उपज को बारिश से बचाएँ।",
        "general": "कदम उठाने से पहले मौसम और खेत की स्थिति दोबारा जाँचें। मिट्टी, सिंचाई और किस्म के अनुसार सही निर्णय बदल सकता है।",
    },
    "mr": {
        "heavy_rain": "मुसळधार पावसाचा अंदाज आहे. शेतातील पाण्याचा निचरा मोकळा ठेवा; सिंचन टाळा आणि फवारणीसाठी पावसानंतरचा योग्य कोरडा वेळ निवडा.",
        "rain": "पावसाचा अंदाज आहे. शेतातील निचरा तपासा आणि पावसाच्या अगोदर खते किंवा इतर निविष्ठा देणे टाळा.",
        "heat": "जास्त तापमानाचा अंदाज आहे. जमिनीतील ओलावा तपासा; सिंचन शक्य असल्यास सकाळी लवकर किंवा संध्याकाळी करा.",
        "wind": "जोरदार वाऱ्याचा अंदाज आहे. वारा जोरात असताना कीटकनाशक किंवा पानांवरील फवारणी टाळा.",
        "dry": "काही दिवस कोरडे हवामान राहण्याची शक्यता आहे. सिंचनापूर्वी जमिनीतील ओलावा तपासा; अनावश्यक पाणी देऊ नका.",
        "flowering_wet_stress": "फुलोरा अवस्थेत ढगाळ व दमट हवामानामुळे फुलगळ व करपा/बुरशीजन्य रोगांचा प्रादुर्भाव वाढू शकतो. केवळ कोरड्या वेळेतच फवारणी करा.",
        "harvest_wet_risk": "काढणी अवस्थेत अवकाळी पावसामुळे पीक बुरशी लागून डागाळण्याचा धोका आहे. काढलेले पीक ताडपत्रीने सुरक्षित झाका.",
        "wet_spell": "सलग काही दिवस ढगाळ व ओलसर हवामानाचा अंदाज आहे. शेतात पाणी साचणार नाही याची काळजी घ्या आणि रोगांची पाहणी करा.",
        "sowing": "पेरणी अवस्था: जमिनीतील ओलावा व शेताची स्थिती तपासा आणि पिकासाठी स्थानिक शिफारशीनुसार पेरणी करा.",
        "vegetative": "वाढीची अवस्था: जोरदार हवामान बदलानंतर पाणी साचणे, पीक लोळणे आणि कीड/रोगाची लक्षणे तपासा.",
        "flowering": "फुलोरा अवस्था: ओलाव्याच्या ताणावर लक्ष ठेवा; अतिउष्णता किंवा जोरदार वाऱ्यात शेतकाम व फवारणी टाळा.",
        "maturity": "परिपक्वता/काढणी अवस्था: काढणी व वाळवणीसाठी कोरडे हवामान निवडा आणि काढलेले पीक पावसापासून सुरक्षित ठेवा.",
        "general": "कृती करण्यापूर्वी हवामान आणि शेताची स्थिती पुन्हा तपासा. माती, सिंचन आणि पिकाच्या जातीनुसार योग्य निर्णय बदलू शकतो.",
    },
}


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _series(daily: dict[str, Any], key: str, count: int, required: bool = True) -> list[float | None]:
    raw = daily.get(key)
    if not isinstance(raw, list) or len(raw) < count:
        if required:
            raise ValueError(f"Weather response is missing the required '{key}' daily series.")
        return [None] * count
    values = [_number(raw[i]) for i in range(count)]
    if required and not any(value is not None for value in values):
        raise ValueError(f"Weather response contains no usable values for '{key}'.")
    return values


def _available_max(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    return max(valid) if valid else None


def compute_spray_suitability(
    dates: list[str],
    rain: list[float | None],
    rain_prob: list[float | None],
    wind: list[float | None],
    language: str = "en",
) -> list[dict[str, Any]]:
    """Compute daily 7-day spray and fieldwork suitability schedule."""
    lang = language if language in SPRAY_STATUS_LABELS else "en"
    schedule: list[dict[str, Any]] = []

    for i, day in enumerate(dates):
        r = rain[i] if (i < len(rain) and rain[i] is not None) else 0.0
        p = rain_prob[i] if (i < len(rain_prob) and rain_prob[i] is not None) else 0.0
        w = wind[i] if (i < len(wind) and wind[i] is not None) else 0.0

        if r >= 5.0 or p >= 70.0 or w >= 20.0:
            status = "AVOID"
            if p >= 70.0:
                reason_en = f"High rain chance ({p:.0f}%, {r:.1f}mm rain)"
                reason_hi = f"बारिश की अधिक संभावना ({p:.0f}%, {r:.1f} मिमी)"
                reason_mr = f"पावसाची जास्त शक्यता ({p:.0f}%, {r:.1f} मिमी)"
            elif r >= 5.0:
                reason_en = f"Rain expected ({r:.1f}mm)"
                reason_hi = f"बारिश का अनुमान ({r:.1f} मिमी)"
                reason_mr = f"पावसाचा अंदाज ({r:.1f} मिमी)"
            else:
                reason_en = f"Strong wind drift ({w:.1f} km/h)"
                reason_hi = f"तेज़ हवा से दवा उड़ने का डर ({w:.1f} किमी/घंटा)"
                reason_mr = f"जोरदार वाऱ्यामुळे फवारणी वाया जाण्याची भीती ({w:.1f} किमी/तास)"
        elif r >= 1.5 or p >= 45.0 or w >= 15.0:
            status = "CAUTION"
            if p >= 45.0 or r >= 1.5:
                reason_en = f"Moderate rain chance ({p:.0f}%, {r:.1f}mm rain)"
                reason_hi = f"मध्यम बारिश की संभावना ({p:.0f}%, {r:.1f} मिमी)"
                reason_mr = f"मध्यम पावसाची शक्यता ({p:.0f}%, {r:.1f} मिमी)"
            else:
                reason_en = f"Moderate breeze ({w:.1f} km/h)"
                reason_hi = f"मध्यम हवा ({w:.1f} किमी/घंटा)"
                reason_mr = f"मध्यम वारा ({w:.1f} किमी/तास)"
        else:
            status = "SAFE"
            reason_en = "Favorable dry & calm window for spraying"
            reason_hi = "छिड़काव के लिए अनुकूल सूखा व शांत मौसम"
            reason_mr = "फवारणीसाठी अनुकूल कोरडे व शांत वातावरण"

        reasons = {"en": reason_en, "hi": reason_hi, "mr": reason_mr}

        schedule.append({
            "date": day,
            "status": status,
            "rain_mm": r,
            "rain_prob": p,
            "wind_kmh": w,
            "localized_status": SPRAY_STATUS_LABELS[lang][status],
            "reason": reasons.get(lang, reason_en),
            "reason_en": reason_en,
        })

    return schedule


def assess_weather_risk(
    weather_payload: dict[str, Any],
    crop: str,
    stage: str,
    language: str = "en",
    mandi_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    daily = weather_payload.get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        raise ValueError("Cannot assess risk because the weather forecast is empty.")

    count = len(dates)
    rain = _series(daily, "precipitation_sum", count)
    rain_prob = _series(daily, "precipitation_probability_max", count, required=False)
    tmax = _series(daily, "temperature_2m_max", count)
    tmin = _series(daily, "temperature_2m_min", count)
    wind = _series(daily, "wind_speed_10m_max", count)
    et0 = _series(daily, "et0_fao_evapotranspiration", count, required=False)

    score = 0
    alerts: list[dict[str, Any]] = []

    max_rain = _available_max(rain)
    max_temp = _available_max(tmax)
    max_wind = _available_max(wind)
    max_prob = _available_max(rain_prob)
    if max_rain is None or max_temp is None or max_wind is None:
        raise ValueError("Weather response is incomplete; rainfall, temperature and wind are needed for risk scoring.")

    lang = language if language in RISK_LABELS else "en"

    def _add_alert(alert_type: str, severity: str, fact_en: str, fact_hi: str, fact_mr: str) -> None:
        facts = {"en": fact_en, "hi": fact_hi, "mr": fact_mr}
        loc_fact = facts.get(lang, fact_en)
        loc_title = ALERT_TITLES.get(lang, ALERT_TITLES["en"]).get(alert_type, alert_type.replace("_", " ").title())
        title_en = ALERT_TITLES["en"].get(alert_type, alert_type.replace("_", " ").title())
        alerts.append({
            "type": alert_type,
            "severity": severity,
            "title": title_en,
            "localized_title": loc_title,
            "fact": loc_fact,
            "fact_en": fact_en,
            "localized_fact": loc_fact,
        })

    # 1. Heavy rain / Rain trigger (Preserves existing contract)
    if max_rain >= 50:
        score += 35
        _add_alert(
            "heavy_rain",
            "High",
            f"Maximum daily rainfall forecast: {max_rain:.1f} mm",
            f"पूर्वानुमान में अधिकतम दैनिक बारिश: {max_rain:.1f} मिमी",
            f"अपेक्षित कमाल दैनिक पाऊस: {max_rain:.1f} मिमी",
        )
    elif max_rain >= 25 or (max_prob is not None and max_prob >= 80 and max_rain >= 10):
        score += 22
        prob_en = f"; maximum probability {max_prob:.0f}%" if max_prob is not None else ""
        prob_hi = f"; अधिकतम संभावना {max_prob:.0f}%" if max_prob is not None else ""
        prob_mr = f"; कमाल शक्यता {max_prob:.0f}%" if max_prob is not None else ""
        _add_alert(
            "rain",
            "Moderate",
            f"Rainfall forecast peaks at {max_rain:.1f} mm/day{prob_en}",
            f"अधिकतम बारिश {max_rain:.1f} मिमी/दिन का अनुमान{prob_hi}",
            f"दैनिक पाऊस {max_rain:.1f} मिमी/दिवस अपेक्षित{prob_mr}",
        )

    # 2. Temperature trigger (Preserves existing contract)
    if max_temp >= 40:
        score += 25
        _add_alert(
            "heat",
            "High",
            f"Maximum temperature forecast: {max_temp:.1f} °C",
            f"पूर्वानुमान में अधिकतम तापमान: {max_temp:.1f} °C",
            f"अपेक्षित कमाल तापमान: {max_temp:.1f} °C",
        )
    elif max_temp >= 36:
        score += 15
        _add_alert(
            "heat",
            "Moderate",
            f"Maximum temperature forecast: {max_temp:.1f} °C",
            f"पूर्वानुमान में अधिकतम तापमान: {max_temp:.1f} °C",
            f"अपेक्षित कमाल तापमान: {max_temp:.1f} °C",
        )

    # 3. Wind speed trigger (Preserves existing contract)
    if max_wind >= 35:
        score += 15
        _add_alert(
            "wind",
            "Moderate",
            f"Maximum wind speed forecast: {max_wind:.1f} km/h",
            f"पूर्वानुमान में अधिकतम हवा की गति: {max_wind:.1f} किमी/घंटा",
            f"अपेक्षित कमाल वाऱ्याचा वेग: {max_wind:.1f} किमी/तास",
        )

    # 4. Dry spell trigger (Preserves existing contract)
    first_three_rain = rain[:min(3, count)]
    first_three_temp = tmax[:min(3, count)]
    first_three_et0 = et0[:min(3, count)]
    if len(first_three_rain) == 3 and all(value is not None for value in first_three_rain):
        next_three_rain = sum(value for value in first_three_rain if value is not None)
        next_three_temp = _available_max(first_three_temp)
        next_three_et0 = sum(value for value in first_three_et0 if value is not None) if all(value is not None for value in first_three_et0) else None
        high_demand = (next_three_temp is not None and next_three_temp >= 32) or (next_three_et0 is not None and next_three_et0 >= 15)
        if next_three_rain < 3 and high_demand:
            score += 15
            demand_note_en = f"; reference ET₀ totals {next_three_et0:.1f} mm" if next_three_et0 is not None else ""
            temp_note_en = f"; temperature reaches {next_three_temp:.1f} °C" if next_three_temp is not None else ""

            demand_note_hi = f"; संदर्भ ET₀ {next_three_et0:.1f} मिमी" if next_three_et0 is not None else ""
            temp_note_hi = f"; तापमान {next_three_temp:.1f} °C तक" if next_three_temp is not None else ""

            demand_note_mr = f"; संदर्भ ET₀ {next_three_et0:.1f} मिमी" if next_three_et0 is not None else ""
            temp_note_mr = f"; तापमान {next_three_temp:.1f} °C पर्यंत" if next_three_temp is not None else ""

            _add_alert(
                "dry",
                "Moderate",
                f"Next 3 days: {next_three_rain:.1f} mm forecast rain{temp_note_en}{demand_note_en}",
                f"अगले 3 दिनों में बारिश: {next_three_rain:.1f} मिमी{temp_note_hi}{demand_note_hi}",
                f"पुढील ३ दिवसांत पाऊस: {next_three_rain:.1f} मिमी{temp_note_mr}{demand_note_mr}",
            )

    # 5. Crop-Stage Sensitivity & Persistent Wet Spell Triggers
    valid_rain = [v for v in rain if v is not None]
    cum_rain = sum(valid_rain)
    wet_days_count = sum(1 for v in valid_rain if v >= 1.0)
    stage_clean = (stage or "").strip().lower()
    is_flowering = "flower" in stage_clean
    is_harvest = "matur" in stage_clean or "harvest" in stage_clean

    if is_flowering and (max_prob is not None and max_prob >= 70 or cum_rain >= 10.0 or wet_days_count >= 3):
        score += 18
        prob_str_en = f"peak rain chance {max_prob:.0f}%" if max_prob is not None else ""
        rain_str_en = f"cumulative {cum_rain:.1f} mm across {wet_days_count} wet days"

        prob_str_hi = f"अधिकतम बारिश की संभावना {max_prob:.0f}%" if max_prob is not None else ""
        rain_str_hi = f"{wet_days_count} दिनों में कुल {cum_rain:.1f} मिमी बारिश"

        prob_str_mr = f"कमाल पावसाची शक्यता {max_prob:.0f}%" if max_prob is not None else ""
        rain_str_mr = f"{wet_days_count} दिवसांत एकूण {cum_rain:.1f} मिमी पाऊस"

        _add_alert(
            "flowering_wet_stress",
            "Moderate",
            f"Flowering stage weather sensitivity: {prob_str_en} ({rain_str_en}). Heightened risk of flower drop and fungal blight.",
            f"फूल आने की अवस्था में मौसम संवेदनशीलता: {prob_str_hi} ({rain_str_hi})। फूल झड़ने और फफूंद जनित रोगों का खतरा।",
            f"फुलोरा अवस्थेत दमट हवामानाची संवेदनशीलता: {prob_str_mr} ({rain_str_mr}). फुलगळ व करपा/बुरशीचा प्रादुर्भाव वाढण्याची शक्यता.",
        )
    elif is_harvest and (max_prob is not None and max_prob >= 65 or cum_rain >= 5.0):
        score += 22
        prob_str_en = f"rain probability {max_prob:.0f}%" if max_prob is not None else ""
        rain_str_en = f"forecast rain {cum_rain:.1f} mm"

        prob_str_hi = f"बारिश की संभावना {max_prob:.0f}%" if max_prob is not None else ""
        rain_str_hi = f"अनुमानित बारिश {cum_rain:.1f} मिमी"

        prob_str_mr = f"पावसाची शक्यता {max_prob:.0f}%" if max_prob is not None else ""
        rain_str_mr = f"अपेक्षित पाऊस {cum_rain:.1f} मिमी"

        _add_alert(
            "harvest_wet_risk",
            "Moderate",
            f"Harvest/maturity weather threat: {prob_str_en} ({rain_str_en}). Moisture can cause pod mold, rotting, or bulb discoloration.",
            f"कटाई अवस्था में मौसम का खतरा: {prob_str_hi} ({rain_str_hi})। फली में फफूंद, सड़न या कंद के रंग बिगड़ने का खतरा।",
            f"काढणी अवस्थेत अवकाळी पावसाचा धोका: {prob_str_mr} ({rain_str_mr}). शेंगांना बुरशी लागणे, कुजणे किंवा कांदा डागाळण्याचा धोका.",
        )
    elif wet_days_count >= 3 and cum_rain >= 10.0 and score < 20:
        score += 12
        _add_alert(
            "wet_spell",
            "Moderate",
            f"Persistent damp spell: {cum_rain:.1f} mm rain over {wet_days_count} days with cloud cover.",
            f"लगातार नम मौसम: {wet_days_count} दिनों में {cum_rain:.1f} मिमी बारिश और बादल छाए रहने का अनुमान।",
            f"सलग दमट हवामान: {wet_days_count} दिवसांत {cum_rain:.1f} मिमी पाऊस व ढगाळ वातावरण.",
        )

    score = min(score, 100)
    if score >= 80:
        label = "Severe"
    elif score >= 55:
        label = "High"
    elif score >= 30:
        label = "Moderate"
    else:
        label = "Low"

    # Compute 7-day spray suitability schedule
    spray_schedule = compute_spray_suitability(dates, rain, rain_prob, wind, lang)
    safe_days = [d["date"] for d in spray_schedule if d["status"] == "SAFE"]
    avoid_days = [d["date"] for d in spray_schedule if d["status"] == "AVOID"]
    caution_days = [d["date"] for d in spray_schedule if d["status"] == "CAUTION"]
    best_spray_date = safe_days[0] if safe_days else None

    # Find highest rain and highest wind days
    highest_rain_day = max((r for r in dates if rain[dates.index(r)] is not None), key=lambda d: rain[dates.index(d)] or 0.0, default=None)
    highest_rain_amount = rain[dates.index(highest_rain_day)] if highest_rain_day else 0.0
    highest_rain_prob = rain_prob[dates.index(highest_rain_day)] if (highest_rain_day and rain_prob[dates.index(highest_rain_day)] is not None) else 0.0

    # Build prioritized, date-anchored localized action plan
    actions: list[str] = []

    # Action 1: Field-work / Spraying Window Guidance
    if best_spray_date:
        if lang == "hi":
            actions.append(f"खेत कार्य व छिड़काव के लिए सबसे सुरक्षित दिन: **{best_spray_date}** (शांत हवा व सूखा मौसम)। बारिश वाले दिनों में छिड़काव टालें।")
        elif lang == "mr":
            actions.append(f"शेतकाम व फवारणीसाठी सर्वात अनुकूल दिवस: **{best_spray_date}** (शांत हवामान व कोरडा काळ). पावसाच्या शक्यतेच्या दिवशी फवारणी टाळा.")
        else:
            actions.append(f"Optimal field-work & spraying window: **{best_spray_date}** (favorable calm, dry conditions). Avoid spraying on high-rain-risk days.")
    else:
        if lang == "hi":
            actions.append("अगले सात दिनों में बारिश या तेज़ हवा के कारण छिड़काव के लिए कोई पूरी तरह सुरक्षित दिन नहीं है; दवा छिड़कना टालें।")
        elif lang == "mr":
            actions.append("पाऊस किंवा जोरदार वाऱ्यामुळे पुढील सात दिवसांत फवारणीसाठी पूर्णपणे सुरक्षित दिवस नाही; रासायनिक फवारणी पुढे ढकला.")
        else:
            actions.append("No ideal calm/dry spraying window detected in the next 7 days due to rain/wind. Postpone chemical applications.")

    # Action 2: Peak Weather Alert / Drainage Guidance
    if highest_rain_amount and highest_rain_amount >= 1.5:
        if lang == "hi":
            actions.append(f"अधिकतम बारिश **{highest_rain_day}** को अनुमानित है ({highest_rain_amount:.1f} मिमी, {highest_rain_prob:.0f}% संभावना): खेत की जल-निकासी साफ रखें।")
        elif lang == "mr":
            actions.append(f"सर्वाधिक पाऊस **{highest_rain_day}** रोजी अपेक्षित आहे ({highest_rain_amount:.1f} मिमी, {highest_rain_prob:.0f}% शक्यता): शेतातील पाण्याचा निचरा मोकळा ठेवा.")
        else:
            actions.append(f"Peak rainfall expected on **{highest_rain_day}** ({highest_rain_amount:.1f} mm, {highest_rain_prob:.0f}% chance): keep drainage clear and postpone field operations.")

    # Action 3: Weather alerts from triggers
    for alert in alerts:
        action = TEXT[lang].get(alert["type"])
        if action and action not in actions:
            actions.append(action)

    # Action 4: Crop stage specific recommendation
    stage_key = {"Sowing": "sowing", "Vegetative": "vegetative", "Flowering": "flowering", "Maturity / Harvest": "maturity"}.get(stage, "general")
    stage_action = TEXT[lang][stage_key]
    if stage_action not in actions:
        actions.append(stage_action)

    # Action 5: Mandi / Market Intelligence Action
    if mandi_data and mandi_data.get("connected") and mandi_data.get("records"):
        top_rec = mandi_data["records"][0]
        mkt = top_rec.get("Market", "APMC")
        modal = top_rec.get("Modal price (₹/quintal)", "N/A")
        date = top_rec.get("Date") or top_rec.get("arrival_date", "")
        is_snap = mandi_data.get("is_snapshot") or mandi_data.get("status") == "cached_snapshot"
        if is_snap:
            date_str = f" ({date})" if date else ""
            if lang == "hi":
                actions.append(f"मंडी भाव (सत्यापित ऐतिहासिक स्नैपशॉट): {mkt} मंडी में मॉडल भाव ₹{modal}/क्विंटल{date_str} दर्ज था। सरकारी लाइव एपीआई व्यस्त होने के कारण यह सत्यापित रिकॉर्ड दिखाया जा रहा है; बेचने से पहले स्थानीय APMC से पुष्टि करें।")
            elif lang == "mr":
                actions.append(f"बाजारभाव सल्ला (सत्यापित ऐतिहासिक स्नॅपशॉट): {mkt} बाजारात सरासरी भाव ₹{modal}/क्विंटल{date_str} नोंदवला होता. थेट सरकारी सर्व्हर व्यस्त असल्याने सत्यापित स्नॅपशॉट दाखवला आहे; विक्रीपूर्वी स्थानिक बाजार समितीशी संपर्क साधा.")
            else:
                actions.append(f"Market intelligence (Verified Historical Snapshot): Recorded modal price of ₹{modal}/quintal at {mkt}{date_str}. Live OGD API busy; verify with local APMC before selling.")
        else:
            if lang == "hi":
                actions.append(f"मंडी भाव: {mkt} मंडी में मॉडल भाव ₹{modal}/क्विंटल दर्ज है। उपज बेचने से पहले आवक और तारीख की पुष्टि करें।")
            elif lang == "mr":
                actions.append(f"बाजारभाव सल्ला: {mkt} बाजारपेठेत सरासरी भाव ₹{modal}/क्विंटल नोंदवला गेला आहे. विक्रीचा निर्णय घेण्यापूर्वी आवक तारीख तपासा.")
            else:
                actions.append(f"Market intelligence: AGMARKNET reported modal price of ₹{modal}/quintal at {mkt}. Verify arrival date before making sale decisions.")
    else:
        if lang == "hi":
            actions.append("मंडी भाव: लाइव सरकारी मंडी डेटा अभी उपलब्ध नहीं है; फसल बेचने से पहले स्थानीय APMC या e-NAM दरों की जाँच करें।")
        elif lang == "mr":
            actions.append("बाजारभाव सल्ला: थेट सरकारी बाजारभाव सध्या उपलब्ध नाही; पीक विक्रीपूर्वी स्थानिक बाजार समिती (APMC) किंवा e-NAM चे दर तपासा.")
        else:
            actions.append("Market intelligence: Live mandi data currently unconfigured/unavailable; verify current rates at your local APMC or e-NAM portal before selling.")

    # Action 6: General disclaimer
    actions.append(TEXT[lang]["general"])

    forecast_rows = []
    for i, day in enumerate(dates):
        forecast_rows.append({
            "Date": day,
            "Rain (mm)": rain[i],
            "Rain probability (%)": rain_prob[i],
            "Max temp (°C)": tmax[i],
            "Min temp (°C)": tmin[i],
            "Wind (km/h)": wind[i],
            "Reference ET₀ (mm)": et0[i],
        })

    return {
        "score": score,
        "label": label,
        "localized_label": RISK_LABELS[lang][label],
        "alerts": alerts,
        "actions": actions,
        "forecast_rows": forecast_rows,
        "spray_schedule": spray_schedule,
        "best_spray_window": best_spray_date,
        "avoid_spray_dates": avoid_days,
        "caution_spray_dates": caution_days,
        "summary": {
            "max_rain_mm": max_rain,
            "max_temp_c": max_temp,
            "max_wind_kmh": max_wind,
            "max_rain_probability": max_prob,
            "max_et0_mm": _available_max(et0),
            "cumulative_rain_mm": cum_rain,
        },
        "method": "Transparent heuristic index based on forecast thresholds; not a trained ML prediction.",
        "crop": crop,
        "stage": stage,
    }
