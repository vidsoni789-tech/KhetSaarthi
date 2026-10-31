"""Dedicated Agricultural Water Management & Irrigation Planning Engine.

Separate from chemical spraying. Grounded strictly in FAO-56 Penman-Monteith methodology,
crop coefficients (Kc), soil infiltration characteristics, and farmer-observed soil moisture states.

Zero synthetic numbers: if ET0 or rain is missing, flags INSUFFICIENT DATA.
"""
from __future__ import annotations

from typing import Any

from .crop_config import (
    CROP_AGRONOMY_REGISTRY,
    SOIL_CHARACTERISTICS,
)

IRRIGATION_STATUS_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "IRRIGATION MAY BE NEEDED": "💧 IRRIGATION MAY BE NEEDED",
        "DEFER AND RECHECK": "⏳ DEFER AND RECHECK",
        "MONITOR SOIL MOISTURE": "👁️ MONITOR SOIL MOISTURE",
        "INSUFFICIENT DATA": "❓ INSUFFICIENT DATA",
    },
    "hi": {
        "IRRIGATION MAY BE NEEDED": "💧 सिंचाई आवश्यक हो सकती है",
        "DEFER AND RECHECK": "⏳ सिंचाई स्थगित करें व पुनः जाँचें",
        "MONITOR SOIL MOISTURE": "👁️ मिट्टी की नमी पर नजर रखें",
        "INSUFFICIENT DATA": "❓ अपर्याप्त मौसम डेटा",
    },
    "mr": {
        "IRRIGATION MAY BE NEEDED": "💧 सिंचन आवश्यक असू शकते",
        "DEFER AND RECHECK": "⏳ सिंचन पुढे ढकला व फेरतपासणी करा",
        "MONITOR SOIL MOISTURE": "👁️ जमिनीतील ओलाव्यावर लक्ष ठेवा",
        "INSUFFICIENT DATA": "❓ हवामान माहिती अपुरी",
    },
}


def calculate_effective_rainfall(
    rain_mm: float | None,
    soil_texture: str = "Loamy / Medium Alluvial",
) -> float | None:
    """Calculate effective rainfall (Pe) infiltrating the root zone.

    Agronomic Principles:
    - Daily rain < 3.0 mm is lost to canopy interception and soil surface evaporation (Pe = 0.0 mm).
    - Heavy rain generates surface runoff on clayey soils and deep percolation on sandy soils.
    """
    if rain_mm is None:
        return None

    if rain_mm < 3.0:
        return 0.0

    soil_info = SOIL_CHARACTERISTICS.get(soil_texture, SOIL_CHARACTERISTICS["Loamy / Medium Alluvial"])
    eff_factor = soil_info.get("effective_rain_factor", 0.75)
    max_eff = soil_info.get("max_effective_rain_mm_day", 45.0)

    # Infiltrating effective rain bounded by soil infiltration capacity
    return round(min(rain_mm * eff_factor, max_eff), 2)


def evaluate_daily_irrigation_need(
    date_str: str,
    rain_mm: float | None,
    et0_mm: float | None,
    crop: str,
    stage: str,
    soil_texture: str = "Loamy / Medium Alluvial",
    soil_moisture: str = "moist",
    language: str = "en",
) -> dict[str, Any]:
    """Evaluate single-day irrigation urgency based on crop ETc, effective rain, and soil moisture."""
    lang = language if language in ("en", "hi", "mr") else "en"
    crop_info = CROP_AGRONOMY_REGISTRY.get(crop, CROP_AGRONOMY_REGISTRY["Soybean"])
    kc_table = crop_info.get("kc", {})
    kc = kc_table.get(stage, 0.75)
    ky_table = crop_info.get("ky_water_stress", {})
    ky = ky_table.get(stage, 0.8)

    # 1. Missing Data Check: Do not invent numbers
    if et0_mm is None or rain_mm is None:
        missing_var = "ET0" if et0_mm is None else "Rainfall"
        reasons = {
            "en": f"Forecast {missing_var} is missing; crop evapotranspiration (ETc) cannot be computed with integrity.",
            "hi": f"मौसम पूर्वानुमान में {missing_var} का डेटा अनुपलब्ध है; फसल की जल खपत (ETc) का प्रामाणिक अनुमान संभव नहीं है।",
            "mr": f"हवामान अंदाजात {missing_var} ची माहिती उपलब्ध नाही; पिकाची पाण्याची गरज (ETc) विश्वासार्हपणे काढता येत नाही.",
        }
        actions = {
            "en": "Verify local soil moisture manually (hand-feel test) before operating irrigation valves.",
            "hi": "सिंचाई करने से पहले खेत में मिट्टी का लड्डू बनाकर नमी की वास्तविक स्थिति स्वयं जांचें।",
            "mr": "पाणी देण्यापूर्वी शेतात मातीचा गोळा करून प्रत्यक्ष ओलावा तपासा (वाफसा स्थिती खात्री करा).",
        }
        return {
            "date": date_str,
            "rain_mm": rain_mm,
            "effective_rain_mm": None,
            "et0_mm": et0_mm,
            "kc": kc,
            "etc_mm": None,
            "net_deficit_mm": None,
            "soil_moisture": soil_moisture,
            "status": "INSUFFICIENT DATA",
            "localized_status": IRRIGATION_STATUS_LABELS[lang]["INSUFFICIENT DATA"],
            "recommended_action": actions[lang],
            "reason": reasons[lang],
        }

    # 2. Compute ETc and Effective Rain
    etc_mm = round(et0_mm * kc, 2)
    eff_rain = calculate_effective_rainfall(rain_mm, soil_texture) or 0.0
    net_deficit = round(max(0.0, etc_mm - eff_rain), 2)

    # 3. Decision Logic considering farmer's soil moisture state and growth stage
    status: str
    reason_en: str
    reason_hi: str
    reason_mr: str
    action_en: str
    action_hi: str
    action_mr: str

    # Harvest / Maturity Stage: Water restriction to prevent rot and allow ripening
    if stage in ("Maturity / Harvest", "Harvest"):
        status = "DEFER AND RECHECK"
        reason_en = f"Crop is in ripening/harvest stage. Cease irrigation to avoid pod/bulb rot, grain staining, and delayed maturity. (ETc: {etc_mm} mm, Rain: {rain_mm} mm)."
        reason_hi = f"फसल पकने/कटाई की अवस्था में है। फलियों/कंदों के सड़ने से बचने और समय पर कटाई के लिए सिंचाई रोकें (ETc: {etc_mm} मिमी, बारिश: {rain_mm} मिमी)।"
        reason_mr = f"पीक पक्वतेच्या/काढणीच्या टप्प्यात आहे. शेंगा/कंद सडणे टाळण्यासाठी व योग्य पक्वतेसाठी पाणी देणे बंद करा (ETc: {etc_mm} मिमी, पाऊस: {rain_mm} मिमी)."
        action_en = "Withhold irrigation; maintain field drainage channels."
        action_hi = "सिंचाई पूरी तरह बंद रखें; जल निकासी बनाए रखें।"
        action_mr = "सिंचन पूर्णपणे थांबवा; शेतातील पाणी निघण्याचा मार्ग मोकळा ठेवा."

    elif soil_moisture == "wet":
        status = "DEFER AND RECHECK"
        reason_en = f"Soil moisture condition reported as WET. Root zone holds surplus water. Additional irrigation risks root asphyxiation, damping-off, and nutrient leaching."
        reason_hi = f"खेत की मिट्टी में पहले से ही अत्यधिक नमी (गीली) है। अतिरिक्त पानी देने से जड़ों में हवा रुक सकती है और जड़ गलन का खतरा बढ़ जाएगा।"
        reason_mr = f"जमिनीत आधीच जास्तीचा ओलावा (ओली जमीन) आहे. आणखी पाणी दिल्यास मुळांना हवा मिळणार नाही (गुदमरणे) व मुळकुजव्या रोगाचा धोका वाढेल."
        action_en = "Do not irrigate. Check field drainage and monitor for fungal root rot."
        action_hi = "सिंचाई बिल्कुल न करें। जल निकासी जांचें और फफूंद जनित रोगों पर नजर रखें।"
        action_mr = "पाणी देणे टाळा. शेतातील पाण्याचा निचरा तपासा व बुरशीजन्य रोगांकडे लक्ष द्या."

    elif eff_rain >= 5.0 or (rain_mm >= 5.0):
        # Forecast rain provides sufficient moisture
        status = "DEFER AND RECHECK"
        reason_en = f"Forecast rainfall ({rain_mm:.1f} mm, ~{eff_rain:.1f} mm effective) satisfies or exceeds crop water demand (ETc: {etc_mm:.1f} mm). Avoid double-watering."
        reason_hi = f"अनुमानित बारिश ({rain_mm:.1f} मिमी, प्रभावी ~{eff_rain:.1f} मिमी) फसल की जल आवश्यकता (ETc: {etc_mm:.1f} मिमी) को पूरा करती है। दोहरा पानी देने से बचें।"
        reason_mr = f"अंदाजित पाऊस ({rain_mm:.1f} मिमी, प्रभावी ~{eff_rain:.1f} मिमी) पिकाच्या पाण्याची गरज (ETc: {etc_mm:.1f} मिमी) भागवतो. अतिरिक्त पाणी देणे टाळावे."
        action_en = "Postpone irrigation; re-assess soil moisture following the rainfall event."
        action_hi = "सिंचाई स्थगित करें; बारिश होने के बाद पुनः खेत की नमी जांचें।"
        action_mr = "सिंचन पुढे ढकला; पाऊस पडून गेल्यानंतरच जमिनीतील ओलावा तपासा."

    elif soil_moisture == "moist":
        # Moisture is at adequate field capacity ("Vafsa")
        if net_deficit > 4.0 and ky >= 1.0:
            status = "MONITOR SOIL MOISTURE"
            reason_en = f"Adequate soil moisture (Vafsa condition). Daily ETc ({etc_mm:.1f} mm) is drawing moisture during critical {stage} stage (Ky: {ky}). Moisture is currently safe."
            reason_hi = f"मिट्टी में पर्याप्त नमी (वापसा स्थिति) है। संवेदनशील {stage} अवस्था में दैनिक जल खपत ({etc_mm:.1f} मिमी) हो रही है। फिलहाल नमी सुरक्षित है।"
            reason_mr = f"जमिनीत सध्या पुरेशी ओल (वाफसा स्थिती) आहे. संवेदनशील {stage} अवस्थेत पिकाची पाण्याची गरज ({etc_mm:.1f} मिमी) सुरू आहे. सध्या ओलावा पुरेसा आहे."
            action_en = "Monitor soil moisture at 10-15 cm root depth; re-check in 24 hours."
            action_hi = "10-15 सेमी गहराई पर मिट्टी की नमी जांचते रहें; 24 घंटे बाद पुनः आकलन करें।"
            action_mr = "१०-१५ सेंमी खोलीवर मातीतील ओलावा तपासा; २४ तासांनी फेरआढावा घ्यावा."
        else:
            status = "MONITOR SOIL MOISTURE"
            reason_en = f"Soil moisture reported as MOIST (field capacity). Effective rain and residual moisture buffer daily ETc ({etc_mm:.1f} mm)."
            reason_hi = f"मिट्टी में सामान्य नमी उपलब्ध है। उपलब्ध नमी फसल की दैनिक खपत ({etc_mm:.1f} मिमी) के लिए पर्याप्त है।"
            reason_mr = f"जमिनीत वाफसा स्थिती आहे. जमिनीतील उपलब्ध ओलावा पिकाची दैनंदिन गरज ({etc_mm:.1f} मिमी) भागवण्यास पुरेसा आहे."
            action_en = "Hold irrigation; check soil surface friability."
            action_hi = "सिंचाई रोके रखें; मिट्टी की ऊपरी सतह भुरभुरी रहने तक प्रतीक्षा करें।"
            action_mr = "पाणी देणे थांबवा; वाफसा टिकून राहील याची दक्षता घ्या."

    else:
        # Soil moisture is DRY
        if net_deficit >= 1.0:
            status = "IRRIGATION MAY BE NEEDED"
            urgency_txt = "CRITICAL (Flowering water stress)" if (ky >= 1.1) else "Moderate"
            reason_en = f"Soil is DRY and daily ETc ({etc_mm:.1f} mm) exceeds effective rainfall ({eff_rain:.1f} mm). Moisture deficit: {net_deficit:.1f} mm [{urgency_txt}]."
            reason_hi = f"मिट्टी सूखी है और दैनिक जल आवश्यकता ({etc_mm:.1f} मिमी) बारिश ({eff_rain:.1f} मिमी) से अधिक है। नमी की कमी: {net_deficit:.1f} मिमी।"
            reason_mr = f"जमीन कोरडी आहे आणि पिकाची पाण्याची गरज ({etc_mm:.1f} मिमी) पावसापेक्षा ({eff_rain:.1f} मिमी) जास्त आहे. ओलाव्याची तूट: {net_deficit:.1f} मिमी."
            action_en = f"Apply irrigation to replenish ~{net_deficit:.1f} mm root-zone deficit. Prefer early morning or evening application."
            action_hi = f"जड़ों में ~{net_deficit:.1f} मिमी की कमी पूरी करने के लिए सिंचाई करें। सुबह या शाम का समय चुनें।"
            action_mr = f"मुळांमधील ~{net_deficit:.1f} मिमी ओलाव्याची तूट भरून काढण्यासाठी सिंचन करावे. सकाळी किंवा संध्याकाळी पाणी द्यावे."
        else:
            status = "MONITOR SOIL MOISTURE"
            reason_en = f"Soil is dry, but light rain ({rain_mm:.1f} mm) or low ETc ({etc_mm:.1f} mm) temporarily limits deficit."
            reason_hi = f"मिट्टी सूखी है, किंतु हल्की बारिश या कम जल खपत के कारण नमी की कमी सीमित है।"
            reason_mr = f"जमीन कोरडी असली तरी हलका पाऊस किंवा कमी बाष्पीभवनामुळे ओलाव्याची तूट मर्यादित आहे."
            action_en = "Inspect root zone before irrigating."
            action_hi = "सिंचाई से पहले जड़ों के पास नमी का मुआयना करें।"
            action_mr = "पाणी देण्यापूर्वी मुळांजवळील ओल प्रत्यक्ष तपासा."

    reasons = {"en": reason_en, "hi": reason_hi, "mr": reason_mr}
    actions = {"en": action_en, "hi": action_hi, "mr": action_mr}

    return {
        "date": date_str,
        "rain_mm": rain_mm,
        "effective_rain_mm": eff_rain,
        "et0_mm": et0_mm,
        "kc": kc,
        "etc_mm": etc_mm,
        "net_deficit_mm": net_deficit,
        "soil_moisture": soil_moisture,
        "status": status,
        "localized_status": IRRIGATION_STATUS_LABELS[lang].get(status, status),
        "recommended_action": actions[lang],
        "reason": reasons[lang],
    }


def plan_7day_irrigation_schedule(
    daily_dates: list[str] | None = None,
    daily_rain: list[float | None] | None = None,
    daily_et0: list[float | None] | None = None,
    crop: str = "Soybean",
    stage: str = "Vegetative",
    soil_texture: str = "Loamy / Medium Alluvial",
    soil_moisture: str = "moist",
    irrigation_method: str | None = None,
    language: str = "en",
    *,
    forecast_rows: list[dict[str, Any]] | None = None,
    growth_stage: str | None = None,
) -> dict[str, Any]:
    """Execute complete 7-day irrigation planning engine.

    Accepts either (daily_dates, daily_rain, daily_et0) or forecast_rows=[{...}].
    """
    actual_stage = growth_stage or stage

    if forecast_rows is not None:
        daily_dates = [str(r.get("Date", "")) for r in forecast_rows]
        daily_rain = [r.get("Rain (mm)") for r in forecast_rows]
        daily_et0 = [r.get("Reference ET₀ (mm)") for r in forecast_rows]
    else:
        daily_dates = daily_dates or []
        daily_rain = daily_rain or []
        daily_et0 = daily_et0 or []

    lang = language if language in ("en", "hi", "mr") else "en"
    crop_info = CROP_AGRONOMY_REGISTRY.get(crop, CROP_AGRONOMY_REGISTRY["Soybean"])
    kc_table = crop_info.get("kc", {})
    kc_val = kc_table.get(actual_stage, 0.75)
    ky_val = crop_info.get("ky_water_stress", {}).get(actual_stage, 0.8)

    schedule: list[dict[str, Any]] = []
    total_etc = 0.0
    total_eff_rain = 0.0
    total_forecast_rain = 0.0
    calculable_days = 0

    # Simulate dynamic moisture transition across the 7 days
    simulated_moisture = soil_moisture

    for idx, date_str in enumerate(daily_dates):
        r_val = daily_rain[idx] if idx < len(daily_rain) else None
        et0_val = daily_et0[idx] if idx < len(daily_et0) else None

        day_result = evaluate_daily_irrigation_need(
            date_str=date_str,
            rain_mm=r_val,
            et0_mm=et0_val,
            crop=crop,
            stage=actual_stage,
            soil_texture=soil_texture,
            soil_moisture=simulated_moisture,
            language=lang,
        )
        schedule.append(day_result)

        if day_result["etc_mm"] is not None and day_result["effective_rain_mm"] is not None:
            total_etc += day_result["etc_mm"]
            total_eff_rain += day_result["effective_rain_mm"]
            total_forecast_rain += (r_val or 0.0)
            calculable_days += 1

            # Update simulated soil moisture for subsequent days:
            # Significant rain wets soil; high deficit dries it
            if (r_val or 0.0) >= 15.0:
                simulated_moisture = "wet"
            elif (r_val or 0.0) >= 5.0:
                simulated_moisture = "moist"
            elif day_result["net_deficit_mm"] and day_result["net_deficit_mm"] >= 4.0:
                if simulated_moisture == "wet":
                    simulated_moisture = "moist"
                elif simulated_moisture == "moist":
                    simulated_moisture = "dry"

    is_calculable = (calculable_days == len(daily_dates)) and (len(daily_dates) > 0)
    net_deficit = round(max(0.0, total_etc - total_eff_rain), 2) if is_calculable else None

    # Identify data issues if incalculable
    data_issues: list[str] = []
    if any(r is None for r in daily_rain):
        data_issues.append("Rainfall forecast missing")
    if any(e is None for e in daily_et0):
        data_issues.append("Reference ET₀ missing")

    # Count days needing irrigation
    irrigation_days = [d["date"] for d in schedule if d["status"] == "IRRIGATION MAY BE NEEDED"]
    defer_days = [d["date"] for d in schedule if d["status"] == "DEFER AND RECHECK"]

    # Determine overall status & localized overarching verdict
    if not is_calculable:
        overall_status = "INSUFFICIENT DATA"
        overall_verdict = {
            "en": "⚠️ INSUFFICIENT DATA: Incomplete meteorological data for 7-day ET0 / rainfall forecast. Exact cumulative deficit cannot be certified; inspect local soil moisture directly.",
            "hi": "⚠️ अपर्याप्त मौसम डेटा: 7 दिनों के ET0 / वर्षा पूर्वानुमान में डेटा अपूर्ण है। संचयी नमी की कमी का प्रमाणित हिसाब संभव नहीं है; खेत की नमी स्वयं जांचें।",
            "mr": "⚠️ हवामान माहिती अपुरी: ७ दिवसांच्या बाष्पीभवन (ET0) किंवा पावसाच्या माहितीत तूट आहे. एकूण ओलाव्याची तूट निश्चित करता येत नाही; प्रत्यक्ष शेतात ओलावा तपासावा.",
        }[lang]
    elif soil_moisture == "wet" or len(defer_days) >= 5:
        overall_status = "DEFER AND RECHECK"
        overall_verdict = {
            "en": f"⏳ DEFER IRRIGATION: Soil is currently wet or substantial rainfall (~{total_eff_rain:.1f} mm effective) buffers crop demand (7-day ETc: {total_etc:.1f} mm). Avoid waterlogging.",
            "hi": f"⏳ सिंचाई स्थगित करें: खेत में पहले से नमी है या पर्याप्त बारिश (~{total_eff_rain:.1f} मिमी प्रभावी) फसल मांग (7-दिवसीय ETc: {total_etc:.1f} मिमी) को पूरा करती है। जलभराव से बचें।",
            "mr": f"⏳ सिंचन पुढे ढकला: जमिनीत आधीच ओल आहे किंवा समाधानकारक पाऊस (~{total_eff_rain:.1f} मिमी प्रभावी) पिकाची गरज (७ दिवसांचे ETc: {total_etc:.1f} मिमी) भागवतो. पाणी साचू देऊ नका.",
        }[lang]
    elif soil_moisture == "dry" or (net_deficit and net_deficit > 5.0):
        overall_status = "IRRIGATION MAY BE NEEDED"
        overall_verdict = {
            "en": f"💧 IRRIGATION MAY BE NEEDED: Cumulative moisture deficit is {net_deficit:.1f} mm across 7 days (Crop ETc: {total_etc:.1f} mm vs Effective Rain: {total_eff_rain:.1f} mm). Key dry window dates: {', '.join(irrigation_days[:3]) if irrigation_days else 'As needed'}.",
            "hi": f"💧 सिंचाई आवश्यक हो सकती है: 7 दिनों में कुल नमी की कमी {net_deficit:.1f} मिमी है (फसल खपत: {total_etc:.1f} मिमी बनाम प्रभावी बारिश: {total_eff_rain:.1f} मिमी)। मुख्य सूखे दिन: {', '.join(irrigation_days[:3]) if irrigation_days else 'आवश्यकतानुसार'}।",
            "mr": f"💧 सिंचन आवश्यक असू शकते: ७ दिवसांत निव्वळ ओलाव्याची तूट {net_deficit:.1f} मिमी आहे (पिकाची गरज: {total_etc:.1f} मिमी विरूद्ध प्रभावी पाऊस: {total_eff_rain:.1f} मिमी). अनुकूल दिवस: {', '.join(irrigation_days[:3]) if irrigation_days else 'गरजेनुसार'}.",
        }[lang]
    else:
        overall_status = "MONITOR SOIL MOISTURE"
        overall_verdict = {
            "en": f"👁️ MONITOR MOISTURE: 7-day effective rainfall (~{total_eff_rain:.1f} mm) closely tracks crop water demand (ETc: {total_etc:.1f} mm). Residual soil moisture is sufficient; re-check in 48 hours.",
            "hi": f"👁️ नमी पर नजर रखें: 7 दिनों की प्रभावी बारिश (~{total_eff_rain:.1f} मिमी) फसल की खपत (ETc: {total_etc:.1f} मिमी) के लगभग बराबर है। खेत में पर्याप्त नमी है; 48 घंटे बाद पुनः जांचें।",
            "mr": f"👁️ ओलाव्यावर लक्ष ठेवा: ७ दिवसांचा प्रभावी पाऊस (~{total_eff_rain:.1f} मिमी) पिकाच्या गरजेइतकाच (ETc: {total_etc:.1f} मिमी) आहे. जमिनीत पुरेसा ओलावा आहे; ४८ तासांनी फेरतपासणी करावी.",
        }[lang]

    disclaimer = {
        "en": "⚠️ AGRONOMIC HONESTY: Weather forecasts and FAO-56 ETc calculations provide operational guidance, but cannot determine exact root-zone tension. Physical field verification (hand-feel test or tensiometer) is mandatory before operating valves. Precise pump running duration requires verified emitter discharge (L/h) and pressure specifications.",
        "hi": "⚠️ कृषि विज्ञान सत्यता: मौसम पूर्वानुमान और FAO-56 ETc गणना केवल मार्गदर्शन हेतु है, यह खेत की आंतरिक नमी नहीं बता सकती। पानी चलाने से पहले मिट्टी की वास्तविक नमी अवश्य जांचें। मोटर चलाने का सटीक समय ड्रिप नोजल के डिस्चार्ज और प्रेशर पर निर्भर करता है।",
        "mr": "⚠️ कृषी वैज्ञानिक सत्यता: हवामान अंदाज व FAO-56 ETc गणित केवळ मार्गदर्शनासाठी आहे; ते शेतातील मुळांजवळील अचूक ओलावा ठरवू शकत नाही. पाणी देण्यापूर्वी प्रत्यक्ष शेतात जाऊन वाफसा तपासावा. ठिबक सुरू ठेवण्याचा नेमका वेळ ड्रीपर डिस्चार्ज व दाबावर अवलंबून असतो.",
    }[lang]

    return {
        "crop": crop,
        "stage": actual_stage,
        "kc": kc_val,
        "ky_water_stress": ky_val,
        "kc_source": crop_info.get("kc_source", "FAO-56"),
        "soil_texture": soil_texture,
        "initial_soil_moisture": soil_moisture,
        "irrigation_method": irrigation_method,
        "is_calculable": is_calculable,
        "overall_status": overall_status,
        "data_issues": data_issues,
        "cumulative_etc_mm": round(total_etc, 2) if is_calculable else None,
        "total_etc_mm": round(total_etc, 2) if is_calculable else None,
        "total_forecast_rain_mm": round(total_forecast_rain, 2) if is_calculable else None,
        "total_effective_rain_mm": round(total_eff_rain, 2) if is_calculable else None,
        "net_moisture_deficit_mm": net_deficit,
        "irrigation_days": irrigation_days,
        "defer_days": defer_days,
        "daily_schedule": schedule,
        "overall_verdict": overall_verdict,
        "disclaimer": disclaimer,
    }
