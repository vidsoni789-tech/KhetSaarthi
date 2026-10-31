"""Decision-Science & Economics Module for KhetSaarthi.

Provides deterministic, grounded agricultural economics:
1. Spatial Mandi Arbitrage & Net Take-Home Revenue (₹) ranking after road transport deduction.
2. Weather Spoilage Value-at-Risk (VaR in ₹) based on crop growth stage & 7-day forecast.
3. FAO-56 Evapotranspiration (ETc = ET0 * Kc) & Precision Irrigation Deficit (hours/acre).
"""
from __future__ import annotations

import copy
import math
from typing import Any

# Standard road transport freight rate in Maharashtra (₹ per quintal per km)
DEFAULT_TRANSPORT_RATE_PER_Q_KM: float = 1.50

# Approximate road winding factor over straight-line Haversine distance
ROAD_TORTUOSITY_FACTOR: float = 1.25

# Standard drip irrigation flow rate (liters per hour per acre for typical micro-irrigation)
DRIP_FLOW_RATE_L_PER_HOUR_ACRE: float = 16000.0

# 1 mm of water over 1 acre = 4,046.86 liters
LITERS_PER_MM_ACRE: float = 4046.86

# Maharashtra District Coordinates Lookup (Centroids for distance estimation)
MAHARASHTRA_DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "ahmednagar": (19.0952, 74.7480),
    "ahilyanagar": (19.0952, 74.7480),
    "akola": (20.7002, 77.0082),
    "amravati": (20.9374, 77.7796),
    "aurangabad": (19.8762, 75.3433),
    "chhatrapati sambhajinagar": (19.8762, 75.3433),
    "beed": (18.9891, 75.7601),
    "bhandara": (21.1667, 79.6500),
    "buldhana": (20.5312, 76.1843),
    "chandrapur": (19.9615, 79.2961),
    "dhule": (20.9042, 74.7749),
    "gadchiroli": (20.1809, 80.0017),
    "gondia": (21.4554, 80.1965),
    "hingoli": (19.7196, 77.1483),
    "jalgaon": (21.0077, 75.5626),
    "jalna": (19.8347, 75.8816),
    "kolhapur": (16.7050, 74.2433),
    "latur": (18.4088, 76.5604),
    "mumbai": (19.0760, 72.8777),
    "mumbai suburban": (19.0760, 72.8777),
    "nagpur": (21.1458, 79.0882),
    "nanded": (19.1383, 77.3210),
    "nandurbar": (21.3697, 74.2403),
    "nashik": (19.9975, 73.7898),
    "osmanabad": (18.1856, 76.0419),
    "dharashiv": (18.1856, 76.0419),
    "palghar": (19.6967, 72.7699),
    "parbhani": (19.2612, 76.7767),
    "pune": (18.5204, 73.8567),
    "raigad": (18.5158, 73.1822),
    "ratnagiri": (16.9902, 73.3120),
    "sangli": (16.8524, 74.5815),
    "satara": (17.6805, 74.0183),
    "sindhudurg": (16.1186, 73.6976),
    "solapur": (17.6599, 75.9064),
    "thane": (19.2183, 72.9781),
    "wardha": (20.7453, 78.6022),
    "washim": (20.1112, 77.1345),
    "yavatmal": (20.3888, 78.1204),
}

# FAO-56 Crop Coefficients (Kc) across growth stages
FAO_CROP_COEFFICIENTS: dict[str, dict[str, float]] = {
    "Soybean": {
        "Sowing": 0.40,
        "Vegetative": 0.80,
        "Flowering": 1.15,
        "Maturity / Harvest": 0.50,
    },
    "Cotton": {
        "Sowing": 0.45,
        "Vegetative": 0.75,
        "Flowering": 1.20,
        "Maturity / Harvest": 0.65,
    },
    "Onion": {
        "Sowing": 0.50,
        "Vegetative": 0.70,
        "Flowering": 1.05,
        "Maturity / Harvest": 0.75,
    },
    "Wheat": {
        "Sowing": 0.40,
        "Vegetative": 0.75,
        "Flowering": 1.15,
        "Maturity / Harvest": 0.40,
    },
    "Sugarcane": {
        "Sowing": 0.50,
        "Vegetative": 1.00,
        "Flowering": 1.25,
        "Maturity / Harvest": 0.75,
    },
    "Maize": {
        "Sowing": 0.40,
        "Vegetative": 0.85,
        "Flowering": 1.20,
        "Maturity / Harvest": 0.55,
    },
    "Tomato": {
        "Sowing": 0.45,
        "Vegetative": 0.80,
        "Flowering": 1.15,
        "Maturity / Harvest": 0.70,
    },
    "Groundnut": {
        "Sowing": 0.40,
        "Vegetative": 0.75,
        "Flowering": 1.10,
        "Maturity / Harvest": 0.55,
    },
    "Tur / Pigeon Pea": {
        "Sowing": 0.40,
        "Vegetative": 0.75,
        "Flowering": 1.15,
        "Maturity / Harvest": 0.50,
    },
    "Rice": {
        "Sowing": 1.10,
        "Vegetative": 1.15,
        "Flowering": 1.25,
        "Maturity / Harvest": 0.90,
    },
}

DEFAULT_STAGE_KC: dict[str, float] = {
    "Sowing": 0.40,
    "Vegetative": 0.75,
    "Flowering": 1.15,
    "Maturity / Harvest": 0.50,
}


def haversine_distance_km(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
    """Calculate great-circle distance between two (lat, lon) coordinates in kilometers."""
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def estimate_road_distance_km(
    origin_district: str,
    origin_coords: tuple[float, float] | None,
    destination_district: str,
) -> float:
    """Estimate road distance in km from farm origin to destination APMC market.

    Applies a 1.25 winding factor on Haversine distance.
    Defaults to 25.0 km for intra-district markets or when coordinates are unavailable.
    """
    clean_orig = (origin_district or "").strip().lower()
    clean_dest = (destination_district or "").strip().lower()

    if clean_orig and clean_dest and clean_orig == clean_dest:
        return 25.0

    orig_pt = origin_coords
    if not orig_pt and clean_orig in MAHARASHTRA_DISTRICT_COORDS:
        orig_pt = MAHARASHTRA_DISTRICT_COORDS[clean_orig]

    dest_pt = MAHARASHTRA_DISTRICT_COORDS.get(clean_dest)

    if orig_pt and dest_pt:
        crow_km = haversine_distance_km(orig_pt, dest_pt)
        road_km = max(25.0, round(crow_km * ROAD_TORTUOSITY_FACTOR, 1))
        return road_km

    return 25.0


def evaluate_mandi_arbitrage_and_hold_risk(
    mandi_data: dict[str, Any] | None,
    origin_district: str,
    origin_coords: tuple[float, float] | None,
    crop: str,
    stage: str,
    weather_risk_score: int,
    forecast_rain_mm: float,
    forecast_max_rain_prob: float,
    lot_quintals: float = 20.0,
    language: str = "en",
) -> dict[str, Any]:
    """Evaluate spatial mandi arbitrage across APMCs and weather spoilage Value-at-Risk (₹).

    Guarantees:
    - Ranks markets by Net Take-Home Revenue (₹) after road transport freight.
    - Estimates crop spoilage / quality discount VaR (₹) based on growth stage & weather.
    - Yields localized recommendations (SELL_NOW, PROTECT_HARVEST, SAFE_TO_HOLD).
    """
    lot = max(1.0, float(lot_quintals))
    lang = language if language in ("en", "hi", "mr") else "en"
    records = mandi_data.get("records", []) if mandi_data and mandi_data.get("connected") else []

    market_rankings: list[dict[str, Any]] = []

    for item in records:
        market_name = str(item.get("Market") or "APMC")
        district_name = str(item.get("District") or origin_district or "")
        raw_modal_str = str(item.get("Modal price (₹/quintal)") or "0").replace(",", "")
        try:
            raw_modal = float(raw_modal_str)
        except ValueError:
            raw_modal = 0.0

        if raw_modal <= 0:
            continue

        dist_km = estimate_road_distance_km(origin_district, origin_coords, district_name)
        trans_cost_per_q = round(dist_km * DEFAULT_TRANSPORT_RATE_PER_Q_KM, 1)
        net_price_per_q = max(0.0, round(raw_modal - trans_cost_per_q, 1))
        gross_rev = round(raw_modal * lot, 2)
        total_trans_cost = round(trans_cost_per_q * lot, 2)
        net_rev = round(net_price_per_q * lot, 2)

        market_rankings.append({
            "market": market_name,
            "district": district_name,
            "raw_modal_price": raw_modal,
            "distance_km": dist_km,
            "transport_cost_per_q": trans_cost_per_q,
            "total_transport_cost_inr": total_trans_cost,
            "net_price_per_q": net_price_per_q,
            "gross_revenue_inr": gross_rev,
            "net_take_home_inr": net_rev,
            "arrival_date": str(item.get("Date") or item.get("arrival_date") or ""),
            "variety": str(item.get("Variety") or "Standard"),
        })

    # Sort descending by Net Take-Home Revenue
    market_rankings.sort(key=lambda m: m["net_take_home_inr"], reverse=True)

    has_market_data = len(market_rankings) > 0
    best_market = market_rankings[0] if has_market_data else None

    # Weather Spoilage Value-at-Risk (VaR in ₹)
    spoilage_risk_pct = 0.0
    rec_code = "SAFE_TO_HOLD"

    is_harvest_stage = any(s in stage.lower() for s in ("maturity", "harvest", "कटाई", "कापणी"))
    is_flowering = any(s in stage.lower() for s in ("flowering", "फुलोरा", "फूल"))

    if is_harvest_stage:
        if forecast_rain_mm >= 15.0 or (forecast_rain_mm >= 8.0 and forecast_max_rain_prob >= 75.0):
            spoilage_risk_pct = 12.0
            rec_code = "SELL_NOW"
        elif forecast_rain_mm >= 4.0 or forecast_max_rain_prob >= 65.0:
            spoilage_risk_pct = 7.0
            rec_code = "SELL_NOW"
        elif forecast_rain_mm >= 1.5:
            spoilage_risk_pct = 3.5
            rec_code = "PROTECT_HARVEST"
        else:
            spoilage_risk_pct = 0.0
            rec_code = "SAFE_TO_HOLD"
    elif is_flowering:
        if forecast_rain_mm >= 12.0 or (forecast_rain_mm >= 6.0 and forecast_max_rain_prob >= 75.0):
            spoilage_risk_pct = 6.5
            rec_code = "PROTECT_HARVEST"
        elif forecast_rain_mm >= 3.0:
            spoilage_risk_pct = 3.0
            rec_code = "PROTECT_HARVEST"
        else:
            spoilage_risk_pct = 0.0
            rec_code = "SAFE_TO_HOLD"
    else:
        if weather_risk_score >= 50 or forecast_rain_mm >= 40.0:
            spoilage_risk_pct = 4.0
            rec_code = "PROTECT_HARVEST"
        else:
            spoilage_risk_pct = 0.0
            rec_code = "SAFE_TO_HOLD"

    best_gross = best_market["gross_revenue_inr"] if best_market else 0.0
    spoilage_var_inr = round(best_gross * (spoilage_risk_pct / 100.0), 2)

    # Localized recommendations
    rec_messages = {
        "SELL_NOW": {
            "en": "⚡ SELL IMMEDIATELY BEFORE RAIN: Upcoming unseasonal rainfall threatens produce quality and mandi grade deductions. Dispatch lots to the top-net APMC before the wet spell.",
            "hi": "⚡ बारिश से पहले तत्काल बेचें: आगामी बेमौसम बारिश से फसल की गुणवत्ता खराब होने और मंडी में कम दाम मिलने का खतरा है। बारिश से पहले उपज उच्चतम शुद्ध लाभ वाली APMC में भेजें।",
            "mr": "⚡ पावसापूर्वी तात्काळ विक्री करा: आगामी अवकाळी पावसामुळे शेतीमालाची प्रत घसरून बाजारभाव कमी होण्याचा गंभीर धोका आहे. पाऊस सुरू होण्यापूर्वी सर्वाधिक निव्वळ नफा देणाऱ्या APMC मध्ये माल पाठवा.",
        },
        "PROTECT_HARVEST": {
            "en": "🛡️ PROTECT HARVEST & MONITOR: Moderate wet/stress conditions forecast. Ensure tarpaulin protection for drying lots, check warehouse ventilation, and hold transport until roads clear.",
            "hi": "🛡️ उपज सुरक्षित रखें व निगरानी करें: मध्यम बारिश/हवा का अनुमान है। खलिहान में उपज को तिरपाल से ढकें, गोदाम में नमी से बचाव रखें और मौसम साफ होने पर ही परिवहन करें।",
            "mr": "🛡️ शेतीमाल सुरक्षित ठेवा व लक्ष ठेवा: मध्यम पाऊस/हवेचा अंदाज आहे. खळ्यातील किंवा वाळवणारा माल ताडपत्रीने झाकून ठेवा, गोदामातील ओलावा तपासा आणि हवामान कोरडे झाल्यावरच वाहतूक करा.",
        },
        "SAFE_TO_HOLD": {
            "en": "✅ SAFE TO HOLD / TRANSPORT: Calm and dry weather prevailing. Minimal weather discount risk; you can safely store produce or time mandi dispatch for higher modal rates.",
            "hi": "✅ सुरक्षित भंडारण व सामान्य परिवहन: मौसम शांत और अनुकूल है। मौसम से फसल को नुकसान का कोई खतरा नहीं है; बेहतर दरों के लिए माल रोककर उपयुक्त समय पर बेच सकते हैं।",
            "mr": "✅ साठवणुकीसाठी व वाहतुकीसाठी सुरक्षित: हवामान कोरडे व शांत आहे. पावसामुळे गुणवत्तेला कोणताही धोका नाही; अधिक दराची वाट पाहून सोयीनुसार शेतीमाल बाजारात पाठवू शकता.",
        },
    }

    return {
        "lot_quintals": lot,
        "has_market_data": has_market_data,
        "best_market_name": best_market["market"] if best_market else "N/A",
        "best_market_raw_price": best_market["raw_modal_price"] if best_market else 0.0,
        "best_market_distance_km": best_market["distance_km"] if best_market else 0.0,
        "best_market_transport_cost_inr": best_market["total_transport_cost_inr"] if best_market else 0.0,
        "best_market_net_price": best_market["net_price_per_q"] if best_market else 0.0,
        "best_market_gross_revenue": best_gross,
        "best_market_net_revenue": best_market["net_take_home_inr"] if best_market else 0.0,
        "market_rankings": market_rankings,
        "spoilage_risk_pct": spoilage_risk_pct,
        "spoilage_var_inr": spoilage_var_inr,
        "recommendation_code": rec_code,
        "localized_recommendation": rec_messages.get(rec_code, rec_messages["SAFE_TO_HOLD"])[lang],
    }


def compute_crop_water_balance(
    daily_dates: list[str],
    daily_et0: list[float | None],
    daily_rain: list[float | None],
    crop: str,
    stage: str,
    language: str = "en",
) -> dict[str, Any]:
    """Compute FAO-56 Crop Evapotranspiration (ETc), Effective Rainfall, and Irrigation Deficit.

    Formulas:
    - ETc = ET0 * Kc (Crop evapotranspiration)
    - Effective Rainfall = Rain * 0.80 (empirical FAO effective fraction)
    - Net Irrigation Deficit = max(0, ETc - Effective Rain)
    - Drip Pump Hours/Acre = (Deficit mm * 4046.86 L/acre) / 16,000 L/hr
    """
    lang = language if language in ("en", "hi", "mr") else "en"

    # Select Kc (Crop Coefficient)
    crop_kc_map = FAO_CROP_COEFFICIENTS.get(crop, DEFAULT_STAGE_KC)
    kc = crop_kc_map.get(stage, DEFAULT_STAGE_KC.get(stage, 0.75))

    daily_balance: list[dict[str, Any]] = []
    total_etc = 0.0
    total_eff_rain = 0.0

    for i, date_str in enumerate(daily_dates):
        et0_val = daily_et0[i] if (i < len(daily_et0) and daily_et0[i] is not None) else 4.2
        rain_val = daily_rain[i] if (i < len(daily_rain) and daily_rain[i] is not None) else 0.0

        etc_day = round(et0_val * kc, 2)
        eff_rain_day = round(rain_val * 0.80, 2)
        deficit_day = max(0.0, round(etc_day - eff_rain_day, 2))

        total_etc += etc_day
        total_eff_rain += eff_rain_day

        daily_balance.append({
            "date": date_str,
            "et0_mm": et0_val,
            "kc": kc,
            "etc_mm": etc_day,
            "rain_mm": rain_val,
            "effective_rain_mm": eff_rain_day,
            "deficit_mm": deficit_day,
        })

    total_etc = round(total_etc, 2)
    total_eff_rain = round(total_eff_rain, 2)
    net_deficit = max(0.0, round(total_etc - total_eff_rain, 2))

    liters_needed = round(net_deficit * LITERS_PER_MM_ACRE, 0)
    drip_hours = round(liters_needed / DRIP_FLOW_RATE_L_PER_HOUR_ACRE, 1)

    # Localized verdict
    if net_deficit <= 0.5:
        verdict = {
            "en": f"Zero irrigation needed — 7-day effective rainfall ({total_eff_rain:.1f} mm) fully covers crop water demand (ETc: {total_etc:.1f} mm). Avoid waterlogging.",
            "hi": f"सिंचाई की आवश्यकता नहीं है — 7 दिनों की प्रभावी बारिश ({total_eff_rain:.1f} मिमी) फसल की जल आवश्यकता (ETc: {total_etc:.1f} मिमी) को पूरी तरह कवर करती है। जलभराव से बचें।",
            "mr": f"पाणी देण्याची गरज नाही — ७ दिवसांचा प्रभावी पाऊस ({total_eff_rain:.1f} मिमी) पिकाची पाण्याची गरज (ETc: {total_etc:.1f} मिमी) पूर्णपणे भागवतो. शेतात पाणी साचू देऊ नका.",
        }[lang]
    else:
        verdict = {
            "en": f"Net crop moisture deficit of {net_deficit:.1f} mm (ETc: {total_etc:.1f} mm vs Effective Rain: {total_eff_rain:.1f} mm). Apply ~{drip_hours:.1f} hours of drip irrigation per acre on dry window dates.",
            "hi": f"फसल में {net_deficit:.1f} मिमी नमी की कमी (ETc: {total_etc:.1f} मिमी बनाम प्रभावी बारिश: {total_eff_rain:.1f} मिमी)। अनुकूल सूखे दिनों में प्रति एकड़ लगभग {drip_hours:.1f} घंटे ड्रिप चलाएं।",
            "mr": f"पिकात {net_deficit:.1f} मिमी ओलाव्याची तूट (ETc: {total_etc:.1f} मिमी विरूद्ध प्रभावी पाऊस: {total_eff_rain:.1f} मिमी). कोरड्या अनुकूल दिवशी प्रति एकर सुमारे {drip_hours:.1f} तास ठिबक सिंचन सुरू ठेवावे.",
        }[lang]

    return {
        "crop": crop,
        "stage": stage,
        "kc": kc,
        "total_etc_mm": total_etc,
        "effective_rain_mm": total_eff_rain,
        "net_irrigation_deficit_mm": net_deficit,
        "liters_per_acre_needed": liters_needed,
        "drip_hours_per_acre": drip_hours,
        "daily_balance": daily_balance,
        "localized_verdict": verdict,
    }


def apply_weather_stress_deltas(
    weather: dict[str, Any],
    rain_delta_mm: float = 0.0,
    temp_delta_c: float = 0.0,
    wind_delta_kmh: float = 0.0,
) -> dict[str, Any]:
    """Apply counterfactual judge stress-test deltas on top of live baseline forecast.

    Creates an isolated deep copy so the original live/cached baseline payload is never mutated.
    - rain_delta_mm: adds rainfall surge primarily to Days 1-3.
    - temp_delta_c: shifts maximum temperatures up across the week (heatwave simulation).
    - wind_delta_kmh: increases wind speeds across the week (cyclone/gust simulation).
    """
    stresstested = copy.deepcopy(weather)
    daily = stresstested.get("daily", {})

    rain_list = list(daily.get("precipitation_sum", []))
    temp_list = list(daily.get("temperature_2m_max", []))
    wind_list = list(daily.get("wind_speed_10m_max", []))
    prob_list = list(daily.get("precipitation_probability_max", []))

    if rain_delta_mm > 0:
        for idx in range(len(rain_list)):
            if rain_list[idx] is not None:
                # Distribute rain surge primarily across Days 1, 2, and 3
                factor = 0.6 if idx in (1, 2) else 0.2
                rain_list[idx] = round(rain_list[idx] + (rain_delta_mm * factor), 1)
        if prob_list:
            for idx in range(len(prob_list)):
                if prob_list[idx] is not None:
                    prob_list[idx] = min(100, int(prob_list[idx] + min(40, rain_delta_mm * 1.5)))

    if temp_delta_c > 0:
        for idx in range(len(temp_list)):
            if temp_list[idx] is not None:
                temp_list[idx] = round(temp_list[idx] + temp_delta_c, 1)

    if wind_delta_kmh > 0:
        for idx in range(len(wind_list)):
            if wind_list[idx] is not None:
                wind_list[idx] = round(wind_list[idx] + wind_delta_kmh, 1)

    daily["precipitation_sum"] = rain_list
    daily["temperature_2m_max"] = temp_list
    daily["wind_speed_10m_max"] = wind_list
    if prob_list:
        daily["precipitation_probability_max"] = prob_list
    stresstested["daily"] = daily
    return stresstested
