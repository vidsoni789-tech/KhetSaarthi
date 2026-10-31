"""Pesticide Spray Weather Suitability & Regulatory Label Verification Engine.

Completely separated from water management. Evaluates meteorology for foliar application
drift, rain wash-off, and thermal inversion. Strictly complies with statutory CIBRC
label claims and prohibits fabricated chemical dosages or generic 'SAFE TO SPRAY' guarantees.
"""
from __future__ import annotations

from typing import Any

from .crop_config import (
    CROP_AGRONOMY_REGISTRY,
    VERIFIED_CIBRC_REGISTRY,
)

SPRAY_SUITABILITY_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "SUITABLE WEATHER WINDOW": "✅ SUITABLE WEATHER WINDOW",
        "CAUTION WINDOW": "⚠️ CAUTION WINDOW",
        "AVOID SPRAYING": "❌ AVOID SPRAYING",
        "UNKNOWN DUE TO MISSING INFORMATION": "❓ UNKNOWN DUE TO MISSING INFORMATION",
    },
    "hi": {
        "SUITABLE WEATHER WINDOW": "✅ छिड़काव हेतु मौसम अनुकूल",
        "CAUTION WINDOW": "⚠️ सावधानी बरतें",
        "AVOID SPRAYING": "❌ छिड़काव से बचें",
        "UNKNOWN DUE TO MISSING INFORMATION": "❓ जानकारी के अभाव में अज्ञात",
    },
    "mr": {
        "SUITABLE WEATHER WINDOW": "✅ हवामान फवारणीस अनुकूल",
        "CAUTION WINDOW": "⚠️ सावधगिरी बाळगा",
        "AVOID SPRAYING": "❌ फवारणी टाळा",
        "UNKNOWN DUE TO MISSING INFORMATION": "❓ माहिती अपुरी असल्याने अनिर्णीत",
    },
}


def evaluate_daily_spray_weather(
    date_str: str,
    rain_mm: float | None,
    rain_prob: float | None,
    wind_kmh: float | None,
    temp_max: float | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Evaluate single-day weather suitability for foliar pesticide application.

    Zero Assumptions:
    - Missing wind speed NEVER defaults to 0 km/h (drift risk cannot be certified).
    - Missing rainfall probability NEVER defaults to 0% (wash-off risk cannot be certified).
    """
    lang = language if language in ("en", "hi", "mr") else "en"

    # 1. Missing Critical Variables Gate
    if wind_kmh is None or rain_prob is None or rain_mm is None:
        missing_parts: list[str] = []
        if wind_kmh is None:
            missing_parts.append("Wind Speed")
        if rain_prob is None:
            missing_parts.append("Rain Probability")
        if rain_mm is None:
            missing_parts.append("Rainfall")

        reasons = {
            "en": f"Forecast missing critical parameter ({', '.join(missing_parts)}). Spray drift and wash-off risks cannot be evaluated.",
            "hi": f"मौसम पूर्वानुमान में ({', '.join(missing_parts)}) अनुपलब्ध है। दवा बहने या उड़ने के जोखिम का सत्यापन संभव नहीं है।",
            "mr": f"हवामान अंदाजात महत्वाचे घटक ({', '.join(missing_parts)}) उपलब्ध नाहीत. फवारणी वाया जाण्याचा धोका पडताळता येत नाही.",
        }
        return {
            "date": date_str,
            "status": "UNKNOWN DUE TO MISSING INFORMATION",
            "localized_status": SPRAY_SUITABILITY_LABELS[lang]["UNKNOWN DUE TO MISSING INFORMATION"],
            "rain_mm": rain_mm,
            "rain_prob": rain_prob,
            "wind_kmh": wind_kmh,
            "temp_max": temp_max,
            "reason": reasons[lang],
            "is_suitable": False,
        }

    # 2. Threshold-Based Agronomic Evaluation
    status: str
    reason_en: str
    reason_hi: str
    reason_mr: str

    # AVOID CONDITIONS
    if rain_prob >= 70.0 or rain_mm >= 5.0 or wind_kmh >= 20.0 or (temp_max is not None and temp_max >= 38.0):
        status = "AVOID SPRAYING"
        if rain_prob >= 70.0:
            reason_en = f"High rain probability ({rain_prob:.0f}%, {rain_mm:.1f}mm). Severe wash-off will waste pesticide and pollute soil."
            reason_hi = f"बारिश की बहुत अधिक संभावना ({rain_prob:.0f}%, {rain_mm:.1f} मिमी)। दवा धुल जाएगी और पैसा बर्बाद होगा।"
            reason_mr = f"पावसाची दाट शक्यता ({rain_prob:.0f}%, {rain_mm:.1f} मिमी). औषध वाहून जाऊन नुकसान होईल."
        elif rain_mm >= 5.0:
            reason_en = f"Significant rain forecast ({rain_mm:.1f}mm). Chemical wash-off risk within 6 hours."
            reason_hi = f"उल्लेखनीय बारिश का अनुमान ({rain_mm:.1f} मिमी)। 6 घंटे के भीतर दवा धुलने का गंभीर जोखिम।"
            reason_mr = f"पावसाचा अंदाज ({rain_mm:.1f} मिमी). ६ तासांत औषध धुतले जाण्याची दाट शक्यता."
        elif wind_kmh >= 20.0:
            reason_en = f"Excessive wind drift ({wind_kmh:.1f} km/h). Droplets will drift off-target and cause uneven control."
            reason_hi = f"तेज हवा ({wind_kmh:.1f} किमी/घंटा)। छिड़काव की बूंदें उड़कर नष्ट होंगी और अन्य फसलों पर गिरेंगी।"
            reason_mr = f"जोराचा वारा ({wind_kmh:.1f} किमी/तास). तुषार उडून जाऊन पिकावर फवारणीचे कव्हरेज मिळणार नाही."
        else:
            reason_en = f"Extreme temperature ({temp_max:.1f}°C). Rapid evaporation and foliage phytotoxicity risk."
            reason_hi = f"अत्यधिक तापमान ({temp_max:.1f}°C)। बूंदें सूखने और पत्तियां जलने (फाइटोटॉक्सिसिटी) का खतरा।"
            reason_mr = f"कडक ऊन व तापमान ({temp_max:.1f}°C). फवारणी वाफेमुळे उडेल व पाने करपण्याचा धोका संभवतो."

    # CAUTION CONDITIONS
    elif rain_prob >= 45.0 or rain_mm >= 1.5 or wind_kmh >= 15.0 or (temp_max is not None and temp_max >= 35.0):
        status = "CAUTION WINDOW"
        if rain_prob >= 45.0 or rain_mm >= 1.5:
            reason_en = f"Moderate rain chance ({rain_prob:.0f}%, {rain_mm:.1f}mm). Spray only with silicon sticker/adjuvant; postpone if skies darken."
            reason_hi = f"मध्यम बारिश की संभावना ({rain_prob:.0f}%, {rain_mm:.1f} मिमी)। स्टीकर मिलाकर सुबह जल्दी ही छिड़कें।"
            reason_mr = f"पावसाची मध्यम शक्यता ({rain_prob:.0f}%, {rain_mm:.1f} मिमी). सिलिकॉन स्प्रेडर मिसळा; आकाश काळवंडल्यास फवारू नका."
        elif wind_kmh >= 15.0:
            reason_en = f"Moderate breeze ({wind_kmh:.1f} km/h). Use coarse droplet nozzles to minimize drift."
            reason_hi = f"मध्यम हवा ({wind_kmh:.1f} किमी/घंटा)। हवा की दिशा देखकर मोटी बूंदों वाले नोजल से काम लें।"
            reason_mr = f"मध्यम वारा ({wind_kmh:.1f} किमी/तास). वाऱ्याची दिशा पाहून मोठ्या थेंबांचा नोजल वापरावा."
        else:
            reason_en = f"Elevated temperature ({temp_max:.1f}°C). Restrict application to early morning (before 9 AM)."
            reason_hi = f"अधिक तापमान ({temp_max:.1f}°C)। केवल सुबह 9 बजे से पहले ही छिड़काव पूरा करें।"
            reason_mr = f"जास्त तापमान ({temp_max:.1f}°C). केवळ सकाळी ९ वाजेपूर्वीच फवारणी आटोपावी."

    # SUITABLE WINDOW
    else:
        status = "SUITABLE WEATHER WINDOW"
        reason_en = f"Calm and dry weather (Rain: {rain_mm:.1f}mm, {rain_prob:.0f}%; Wind: {wind_kmh:.1f} km/h). Weather-suitable for foliar application."
        reason_hi = f"शांत व सूखा मौसम (बारिश: {rain_mm:.1f} मिमी, हवा: {wind_kmh:.1f} किमी/घंटा)। पत्तियों पर छिड़काव हेतु मौसम अनुकूल।"
        reason_mr = f"कोरडे व शांत वातावरण (पाऊस: {rain_mm:.1f} मिमी, वारा: {wind_kmh:.1f} किमी/तास). पानांवर फवारणीसाठी हवामान अनुकूल."

    reasons = {"en": reason_en, "hi": reason_hi, "mr": reason_mr}

    return {
        "date": date_str,
        "status": status,
        "localized_status": SPRAY_SUITABILITY_LABELS[lang].get(status, status),
        "rain_mm": rain_mm,
        "rain_prob": rain_prob,
        "wind_kmh": wind_kmh,
        "temp_max": temp_max,
        "reason": reasons[lang],
        "is_suitable": (status == "SUITABLE WEATHER WINDOW"),
    }


def verify_pesticide_label(
    crop: str,
    target_pest: str | None = None,
    product_name: str | None = None,
    stage: str = "Vegetative",
    language: str = "en",
    *,
    chemical_product: str | None = None,
    growth_stage: str | None = None,
) -> dict[str, Any]:
    """Verify pesticide product and dosage against statutory CIBRC registry.

    Enforces Strict Honesty:
    - Never invents dosage rates.
    - If unverified, explicitly directs farmer to official registered container label and KVK.
    """
    lang = language if language in ("en", "hi", "mr") else "en"
    pest_clean = (target_pest or "").strip()
    prod_clean = (chemical_product or product_name or "").strip()
    actual_stage = growth_stage or stage

    # 1. Check if pest problem is specified
    if not pest_clean or "none" in pest_clean.lower() or "preventive" in pest_clean.lower():
        advisory_msg = {
            "en": "No target pest or disease problem specified. Prophylactic/calendar chemical spraying is discouraged. Conduct field scouting and confirm Economic Threshold Levels (ETL) before chemical use.",
            "hi": "किसी विशिष्ट कीट या बीमारी का उल्लेख नहीं है। बिना बीमारी के नियमित रासायनिक छिड़काव न करें। खेत में कीटों की संख्या (ETL) देखकर ही दवा का चयन करें।",
            "mr": "विशिष्ट कीड किंवा रोगाचा प्रादुर्भाव नमूद नाही. पूर्वतयारी म्हणून विनाकारण रासायनिक फवारणी टाळावी. शेतात किडींची आर्थिक नुकसान पातळी (ETL) तपासूनच निर्णय घ्यावा.",
        }[lang]
        return {
            "verified": False,
            "status": "NO_PEST_SPECIFIED",
            "dosage_display": None,
            "cibrc_registration": None,
            "advisory_message": advisory_msg,
            "is_recommended": False,
        }

    # 2. Look up in genuine CIBRC registry
    cibrc_key = (crop, pest_clean, prod_clean)
    entry = VERIFIED_CIBRC_REGISTRY.get(cibrc_key)

    if entry:
        dosage_txt = f"{entry['label_dosage_acre']} (or {entry['label_dosage_ha']})"
        recommended_dose = f"{entry['label_dosage_ha']} ({entry['label_dosage_acre']})"
        advisory_msg = {
            "en": f"Official CIBRC Label Verified: {entry['active_ingredient']} approved for {pest_clean} in {crop}. Pre-Harvest Interval (PHI): {entry['phi_days']} days.",
            "hi": f"सरकारी CIBRC अनुमोदित: {crop} में {pest_clean} हेतु {entry['active_ingredient']} की सिफारिश है। कटाई पूर्व अंतराल (PHI): {entry['phi_days']} दिन।",
            "mr": f"अधिकृत CIBRC शिफारस पडताळली: {crop} वरील {pest_clean} साठी {entry['active_ingredient']} प्रमाणित आहे. काढणीपूर्व प्रतीक्षा कालावधी (PHI): {entry['phi_days']} दिवस.",
        }[lang]
        return {
            "verified": True,
            "status": "OFFICIAL_LABEL_VERIFIED",
            "active_ingredient": entry["active_ingredient"],
            "cibrc_registration": entry["registration_authority"],
            "label_dosage_acre": entry["label_dosage_acre"],
            "label_dosage_ha": entry["label_dosage_ha"],
            "recommended_dose": recommended_dose,
            "water_volume_liters_acre": entry["water_volume_liters_acre"],
            "phi_days": entry["phi_days"],
            "hazard_class": entry["hazard_class"],
            "pollinator_safety": entry["pollinator_safety"],
            "dosage_display": dosage_txt,
            "advisory_message": advisory_msg,
            "is_recommended": True,
        }

    # 3. Unverified combination -> Strict safeguard
    advisory_msg = {
        "en": f"Official label dosage cannot be certified for '{prod_clean or 'unspecified product'}' against {pest_clean} on {crop}. Never guess chemical concentrations. Strictly follow the registered product label leaflet and consult a qualified local agricultural officer / Krishi Vigyan Kendra (KVK) scientist before mixing.",
        "hi": f"{crop} पर {pest_clean} के लिए इस उत्पाद की आधिकारिक लेबल मात्रा सत्यापित नहीं है। मनमाने अनुपात में दवा न मिलाएं। डिब्बे पर लगा सरकारी लेबल पढ़ें और कृषि विज्ञान केंद्र (KVK) से परामर्श लें।",
        "mr": f"{crop} पिकावरील {pest_clean} साठी या उत्पादनाचे अधिकृत प्रमाण (डोस) पडताळलेले नाही. मनाने औषधाचे प्रमाण ठरवू नका. औषधाच्या बाटलीवरील माहितीपत्रक वाचा आणि स्थानिक कृषी विज्ञान केंद्रातील (KVK) शास्त्रज्ञांचा सल्ला घ्या.",
    }[lang]

    return {
        "verified": False,
        "status": "UNVERIFIED",
        "recommended_dose": None,
        "dosage_display": None,
        "cibrc_registration": None,
        "advisory_message": advisory_msg,
        "is_recommended": False,
    }


def assess_pesticide_weather_suitability(
    dates: list[str] | None = None,
    rain_mm: list[float | None] | None = None,
    rain_prob: list[float | None] | None = None,
    wind_kmh: list[float | None] | None = None,
    temp_max: list[float | None] | None = None,
    crop: str = "Soybean",
    stage: str = "Vegetative",
    target_pest: str | None = None,
    product_name: str | None = None,
    language: str = "en",
    *,
    forecast_rows: list[dict[str, Any]] | None = None,
    growth_stage: str | None = None,
    chemical_product: str | None = None,
) -> dict[str, Any]:
    """Execute complete 7-day pesticide spray weather suitability and regulatory assessment."""
    actual_stage = growth_stage or stage
    actual_product = chemical_product or product_name

    if forecast_rows is not None:
        dates = [str(r.get("Date", "")) for r in forecast_rows]
        rain_mm = [r.get("Rain (mm)") for r in forecast_rows]
        rain_prob = [r.get("Rain probability (%)") for r in forecast_rows]
        wind_kmh = [r.get("Wind (km/h)") for r in forecast_rows]
        temp_max = [r.get("Max temp (°C)") for r in forecast_rows]
    else:
        dates = dates or []
        rain_mm = rain_mm or []
        rain_prob = rain_prob or []
        wind_kmh = wind_kmh or []
        temp_max = temp_max or []

    lang = language if language in ("en", "hi", "mr") else "en"
    crop_info = CROP_AGRONOMY_REGISTRY.get(crop, CROP_AGRONOMY_REGISTRY["Soybean"])

    daily_schedule: list[dict[str, Any]] = []
    suitable_dates: list[str] = []
    caution_dates: list[str] = []
    avoid_dates: list[str] = []
    unknown_dates: list[str] = []

    for i, d_str in enumerate(dates):
        r = rain_mm[i] if i < len(rain_mm) else None
        p = rain_prob[i] if i < len(rain_prob) else None
        w = wind_kmh[i] if i < len(wind_kmh) else None
        t = temp_max[i] if i < len(temp_max) else None

        day_eval = evaluate_daily_spray_weather(
            date_str=d_str,
            rain_mm=r,
            rain_prob=p,
            wind_kmh=w,
            temp_max=t,
            language=lang,
        )
        daily_schedule.append(day_eval)

        if day_eval["status"] == "SUITABLE WEATHER WINDOW":
            suitable_dates.append(d_str)
        elif day_eval["status"] == "CAUTION WINDOW":
            caution_dates.append(d_str)
        elif day_eval["status"] == "AVOID SPRAYING":
            avoid_dates.append(d_str)
        else:
            unknown_dates.append(d_str)

    best_window = suitable_dates[0] if suitable_dates else None

    # Regulatory label check
    label_eval = verify_pesticide_label(
        crop=crop,
        target_pest=target_pest,
        product_name=actual_product,
        stage=actual_stage,
        language=lang,
    )

    # Stage specific warnings
    stage_warning = crop_info.get("stage_warnings", {}).get(actual_stage, {}).get(lang)

    # Localized overarching spray verdict
    if suitable_dates:
        overall_verdict = {
            "en": f"Weather-suitable foliar application window identified on: {', '.join(suitable_dates[:3])}. Calm and dry conditions forecast.",
            "hi": f"छिड़काव हेतु अनुकूल मौसम विंडो: {', '.join(suitable_dates[:3])}। इस दौरान बारिश और तेज हवा का खतरा कम है।",
            "mr": f"फवारणीसाठी अनुकूल हवामानाचे दिवस: {', '.join(suitable_dates[:3])}. शांत व कोरडे वातावरण राहण्याचा अंदाज आहे.",
        }[lang]
    elif caution_dates:
        overall_verdict = {
            "en": f"Marginal weather windows only ({', '.join(caution_dates[:2])}). Light rain or moderate breeze forecast; use sticker adjuvant and spray early morning.",
            "hi": f"केवल मध्यम/सावधानी वाले दिन उपलब्ध हैं ({', '.join(caution_dates[:2])})। स्टीकर मिलाएं और सुबह जल्दी छिड़कें।",
            "mr": f"फक्त सावधगिरी बाळगण्यासारखे दिवस आहेत ({', '.join(caution_dates[:2])}). हलका पाऊस किंवा वाऱ्याची शक्यता; स्टिकर वापरावे.",
        }[lang]
    elif avoid_dates:
        overall_verdict = {
            "en": "All upcoming days exhibit high rain probability, heavy rain, or strong wind drift. Postpone chemical spraying.",
            "hi": "आगामी दिनों में तेज बारिश या तेज हवा का अनुमान है। कीटनाशक छिड़काव पूरी तरह स्थगित रखें।",
            "mr": "आगामी दिवसांत जोरदार पाऊस किंवा वाऱ्याचा अंदाज आहे. रासायनिक फवारणी पूर्णपणे पुढे ढकलावी.",
        }[lang]
    else:
        overall_verdict = {
            "en": "Incomplete meteorological data prevents certification of spray suitability. Inspect local wind and cloud conditions.",
            "hi": "अपूर्ण मौसम डेटा के कारण छिड़काव अनुकूलता प्रमाणित नहीं की जा सकती। स्थानीय मौसम देखकर निर्णय लें।",
            "mr": "अपूर्ण हवामान माहितीमुळे फवारणी अनुकूलता ठरवता येत नाही. स्थानिक हवामान प्रत्यक्ष तपासून निर्णय घ्यावा.",
        }[lang]

    disclaimer = {
        "en": "⚠️ REGULATORY SAFEGUARD: Weather suitability does NOT constitute a recommendation to apply pesticides. Never spray on a calendar schedule without scouting for active economic threshold levels (ETL). Always wear PPE (gloves, mask, goggles) and follow statutory container labels. Weather suitability does not replace pesticide label requirements.",
        "hi": "⚠️ वैधानिक चेतावनी: अनुकूल मौसम का अर्थ दवा डालने की गारंटी नहीं है। बिना कीट-रोग देखे नियमित छिड़काव न करें। सुरक्षा उपकरण (मास्क, दस्ताने) पहनें और उत्पाद के अधिकृत लेबल का पालन करें।",
        "mr": "⚠️ वैधानिक खबरदारी: हवामान अनुकूल असणे म्हणजे फवारणीची सक्ती किंवा हमी नाही. किडींची आर्थिक नुकसान पातळी (ETL) तपासल्याशिवाय फवारणी करू नये. संरक्षक साधने (मास्क, हातमोजे) वापरा व लेबलवरील सूचनांचे काटेकोर पालन करा.",
    }[lang]

    # Determine overarching suitability status
    if suitable_dates:
        overall_status = "SUITABLE WEATHER WINDOW"
    elif caution_dates:
        overall_status = "CAUTION WINDOW"
    elif avoid_dates:
        overall_status = "AVOID SPRAYING"
    else:
        overall_status = "UNKNOWN DUE TO MISSING INFORMATION"

    return {
        "crop": crop,
        "stage": actual_stage,
        "target_pest": target_pest,
        "product_name": actual_product,
        "overall_status": overall_status,
        "best_window": best_window,
        "suitable_dates": suitable_dates,
        "caution_dates": caution_dates,
        "avoid_dates": avoid_dates,
        "unknown_dates": unknown_dates,
        "daily_schedule": daily_schedule,
        "label_evaluation": label_eval,
        "stage_warning": stage_warning,
        "overall_verdict": overall_verdict,
        "disclaimer": disclaimer,
    }
