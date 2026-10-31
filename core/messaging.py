"""Real Outbound WhatsApp & Phone Push Notification Engine for KhetSaarthi.

Supports real outbound message delivery to real mobile phones via:
1. Twilio WhatsApp REST API (Twilio Sandbox / Approved Business Sender)
2. CallMeBot Personal WhatsApp Webhook API
3. Meta WhatsApp Cloud API (Graph API)
4. Direct WhatsApp Deep-Link Launcher (api.whatsapp.com/send?phone=...&text=...)
"""
from __future__ import annotations

import os
import re
import time
import urllib.parse
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


def clean_phone_number(phone_raw: str) -> str:
    """Normalize phone number to international E.164 format (+91 for India by default)."""
    if not phone_raw:
        return ""
    # Strip spaces, dashes, brackets
    cleaned = re.sub(r"[^\d+]", "", phone_raw.strip())
    if not cleaned:
        return ""

    # If 10-digit Indian mobile number without country code
    if len(cleaned) == 10 and cleaned[0] in "6789":
        return f"+91{cleaned}"
    # If 11 digits starting with 0
    if len(cleaned) == 11 and cleaned.startswith("0"):
        return f"+91{cleaned[1:]}"
    # If lacks leading '+'
    if not cleaned.startswith("+"):
        return f"+{cleaned}"
    return cleaned


def format_whatsapp_advisory_message(report: dict[str, Any], language: str = "en") -> str:
    """Format a crisp, farmer-friendly localized WhatsApp advisory message."""
    place = report.get("location", {})
    place_name = place.get("name", "Farm")
    district = place.get("admin2") or place.get("admin1") or "Maharashtra"
    crop = report.get("risk", {}).get("crop") or "Crop"
    stage = report.get("risk", {}).get("stage") or "Growth"

    risk = report.get("risk", {})
    score = risk.get("score", 0)
    label = risk.get("localized_label") or risk.get("label", "Low")
    best_spray = risk.get("best_spray_window") or "Check daily update"

    # Spray schedule highlights
    schedule = risk.get("spray_schedule", [])
    safe_dates = [d["date"] for d in schedule if d.get("status") == "SAFE"][:2]
    avoid_dates = [d["date"] for d in schedule if d.get("status") == "AVOID"][:2]

    safe_str = ", ".join(safe_dates) if safe_dates else ("None" if language == "en" else "काही नाही")
    avoid_str = ", ".join(avoid_dates) if avoid_dates else ("None" if language == "en" else "काही नाही")

    # Mandi price & 50kg bag price
    mandi = report.get("mandi", {})
    mandi_records = mandi.get("records", [])
    top_rec = mandi_records[0] if mandi_records else {}
    mkt = top_rec.get("Market", "APMC")
    modal_str = str(top_rec.get("Modal price (₹/quintal)") or "0").replace(",", "")
    try:
        modal_val = float(modal_str)
    except ValueError:
        modal_val = 0.0

    bag_price_str = f"₹{modal_val / 2:,.0f}" if modal_val > 0 else "N/A"
    modal_disp = f"₹{modal_val:,.0f}/Q" if modal_val > 0 else "Govt API busy"

    # Irrigation deficit
    water_bal = report.get("economics_and_water", {}).get("water_balance", {})
    def_mm = water_bal.get("net_irrigation_deficit_mm", 0.0)
    drip_hrs = water_bal.get("drip_hours_per_acre", 0.0)

    # Top action
    top_action = risk.get("actions", [""])[0] if risk.get("actions") else ""

    if language == "mr":
        msg = (
            f"🌱 *खेतसारथी कृषी सल्ला (KhetSaarthi)*\n"
            f"📍 *ठिकाण:* {place_name}, {district}\n"
            f"🌾 *पीक व अवस्था:* {crop} ({stage})\n"
            f"⚠️ *हवामान जोखीम:* {score}/100 ({label})\n\n"
            f"🚜 *७ दिवसांचे फवारणी वेळापत्रक:*\n"
            f"  ✅ अनुकूल दिवस: {safe_str}\n"
            f"  ❌ टाळावयाचे दिवस: {avoid_str}\n"
            f"  🗓️ सर्वोत्तम खिडकी: {best_spray}\n\n"
            f"💧 *सिंचन गरज (FAO-56):* {def_mm:.1f} मिमी तूट (~{drip_hrs:.1f} तास ठिबक/एकर)\n"
            f"💰 *बाजारभाव:* {mkt} — {modal_disp} ({bag_price_str} प्रति ५० किलो पोते)\n\n"
            f"👉 *महत्त्वाची कृती:* {top_action}\n\n"
            f"📢 _पडताळणी: Open-Meteo & data.gov.in AGMARKNET._"
        )
    elif language == "hi":
        msg = (
            f"🌱 *खेतसारथी कृषि परामर्श (KhetSaarthi)*\n"
            f"📍 *स्थान:* {place_name}, {district}\n"
            f"🌾 *फसल व अवस्था:* {crop} ({stage})\n"
            f"⚠️ *मौसम जोखिम:* {score}/100 ({label})\n\n"
            f"🚜 *७-दिवसीय छिड़काव कैलेंडर:*\n"
            f"  ✅ सुरक्षित दिन: {safe_str}\n"
            f"  ❌ छिड़काव टालें: {avoid_str}\n"
            f"  🗓️ सर्वोत्तम समय: {best_spray}\n\n"
            f"💧 *सिंचाई आवश्यकता:* {def_mm:.1f} मिमी कमी (~{drip_hrs:.1f} घंटे ड्रिप/एकड़)\n"
            f"💰 *मंडी भाव:* {mkt} — {modal_disp} ({bag_price_str} प्रति ५० किग्रा बोरी)\n\n"
            f"👉 *मुख्य सलाह:* {top_action}\n\n"
            f"📢 _सत्यापित स्रोत: Open-Meteo व data.gov.in AGMARKNET._"
        )
    else:
        msg = (
            f"🌱 *KhetSaarthi Farm Risk Advisory*\n"
            f"📍 *Location:* {place_name}, {district}\n"
            f"🌾 *Crop & Stage:* {crop} ({stage})\n"
            f"⚠️ *Weather Risk:* {score}/100 ({label})\n\n"
            f"🚜 *7-Day Spray Calendar:*\n"
            f"  ✅ Safe Spray Dates: {safe_str}\n"
            f"  ❌ Avoid Spray Dates: {avoid_str}\n"
            f"  🗓️ Optimal Window: {best_spray}\n\n"
            f"💧 *FAO-56 Irrigation:* {def_mm:.1f} mm deficit (~{drip_hrs:.1f} hrs drip/acre)\n"
            f"💰 *Mandi Modal Rate:* {mkt} — {modal_disp} ({bag_price_str} per 50kg bag)\n\n"
            f"👉 *Priority Action:* {top_action}\n\n"
            f"📢 _Verified via Open-Meteo & data.gov.in AGMARKNET._"
        )
    return msg


def format_whatsapp_deep_link(phone_number: str, message: str) -> str:
    """Generate direct WhatsApp click-to-chat deep link for mobile/desktop."""
    clean = clean_phone_number(phone_number).replace("+", "")
    encoded_text = urllib.parse.quote(message)
    if clean:
        return f"https://api.whatsapp.com/send?phone={clean}&text={encoded_text}"
    return f"https://api.whatsapp.com/send?text={encoded_text}"


def send_real_whatsapp_message(
    phone_number: str,
    message: str,
    twilio_sid: str | None = None,
    twilio_token: str | None = None,
    twilio_from: str | None = None,
    callmebot_api_key: str | None = None,
    meta_token: str | None = None,
    meta_phone_id: str | None = None,
) -> dict[str, Any]:
    """Execute real outbound HTTP API request to deliver a live WhatsApp message.

    Supports:
    1. Twilio WhatsApp API (POST /2010-04-01/Accounts/{SID}/Messages.json)
    2. CallMeBot Personal WhatsApp Webhook (GET /whatsapp.php)
    3. Meta WhatsApp Cloud Graph API (POST /v21.0/{PHONE_ID}/messages)
    4. Fallback to direct WhatsApp deep-link when credentials are not configured.
    """
    t0 = time.perf_counter()
    clean_phone = clean_phone_number(phone_number)
    deep_link = format_whatsapp_deep_link(clean_phone, message)

    if not clean_phone:
        return {
            "sent": False,
            "provider": "none",
            "message_sid": None,
            "latency_ms": 1,
            "status_detail": "Phone number is empty or invalid.",
            "deep_link": deep_link,
        }

    # Helper to resolve credentials from args, env, or st.secrets
    def _res(val: str | None, *env_keys: str) -> str:
        if val is not None and str(val).strip():
            return str(val).strip()
        for k in env_keys:
            ev = os.getenv(k, "").strip()
            if ev:
                return ev
        try:
            import streamlit as st
            for k in env_keys:
                sv = str(st.secrets.get(k, "")).strip()
                if sv:
                    return sv
        except Exception:
            pass
        return ""

    sid = _res(twilio_sid, "TWILIO_ACCOUNT_SID", "TWILIO_SID")
    token = _res(twilio_token, "TWILIO_AUTH_TOKEN", "TWILIO_TOKEN")
    from_num = _res(twilio_from, "TWILIO_WHATSAPP_FROM", "TWILIO_FROM") or "+14155238886"
    callme_key = _res(callmebot_api_key, "CALLMEBOT_API_KEY", "CALLMEBOT_KEY")
    m_token = _res(meta_token, "META_WHATSAPP_TOKEN", "WHATSAPP_TOKEN")
    m_phone_id = _res(meta_phone_id, "META_PHONE_NUMBER_ID", "WHATSAPP_PHONE_ID")

    # 1. ATTEMPT TWILIO WHATSAPP API
    if sid and token:
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        from_formatted = f"whatsapp:{from_num}" if not from_num.startswith("whatsapp:") else from_num
        to_formatted = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone

        payload = {
            "From": from_formatted,
            "To": to_formatted,
            "Body": message,
        }
        try:
            resp = requests.post(
                twilio_url,
                data=payload,
                auth=HTTPBasicAuth(sid, token),
                timeout=5.0,
            )
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
            data = resp.json() if resp.text else {}
            if resp.ok and data.get("sid"):
                return {
                    "sent": True,
                    "provider": "Twilio WhatsApp API",
                    "message_sid": data["sid"],
                    "latency_ms": elapsed_ms,
                    "status_detail": f"Queued/Sent via Twilio (SID: {data['sid'][:10]}..., Status: {data.get('status', 'sent')})",
                    "deep_link": deep_link,
                }
            err_msg = data.get("message") or f"Twilio HTTP {resp.status_code}"
            if "contentsid" in str(err_msg).lower():
                detail = "Twilio WhatsApp requires an approved Template (ContentSid) or active Sandbox join session. Click the 1-Click WhatsApp button below to deliver immediately!"
            else:
                detail = f"Twilio error: {err_msg}"
            return {
                "sent": False,
                "provider": "Twilio WhatsApp API",
                "message_sid": None,
                "latency_ms": elapsed_ms,
                "status_detail": detail,
                "deep_link": deep_link,
            }
        except Exception as exc:
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
            return {
                "sent": False,
                "provider": "Twilio WhatsApp API",
                "message_sid": None,
                "latency_ms": elapsed_ms,
                "status_detail": f"Twilio connection error: {str(exc)[:120]}",
                "deep_link": deep_link,
            }

    # 2. ATTEMPT CALLMEBOT PERSONAL WHATSAPP WEBHOOK
    if callme_key:
        encoded_msg = urllib.parse.quote(message)
        phone_no_plus = clean_phone.replace("+", "")
        callme_url = f"https://api.callmebot.com/whatsapp.php?phone={phone_no_plus}&text={encoded_msg}&apikey={callme_key}"
        try:
            resp = requests.get(callme_url, timeout=5.0)
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
            if resp.ok and ("success" in resp.text.lower() or "queued" in resp.text.lower() or "message" in resp.text.lower()):
                return {
                    "sent": True,
                    "provider": "CallMeBot WhatsApp Webhook",
                    "message_sid": f"cmb-{phone_no_plus[-6:]}-{int(time.time())}",
                    "latency_ms": elapsed_ms,
                    "status_detail": "Dispatched via CallMeBot live WhatsApp gateway.",
                    "deep_link": deep_link,
                }
            return {
                "sent": False,
                "provider": "CallMeBot WhatsApp Webhook",
                "message_sid": None,
                "latency_ms": elapsed_ms,
                "status_detail": f"CallMeBot response: {resp.text[:120]}",
                "deep_link": deep_link,
            }
        except Exception as exc:
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
            return {
                "sent": False,
                "provider": "CallMeBot WhatsApp Webhook",
                "message_sid": None,
                "latency_ms": elapsed_ms,
                "status_detail": f"CallMeBot error: {str(exc)[:120]}",
                "deep_link": deep_link,
            }

    # 3. ATTEMPT META WHATSAPP CLOUD API
    if m_token and m_phone_id:
        meta_url = f"https://graph.facebook.com/v21.0/{m_phone_id}/messages"
        headers = {"Authorization": f"Bearer {m_token}", "Content-Type": "application/json"}
        phone_no_plus = clean_phone.replace("+", "")
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_no_plus,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        try:
            resp = requests.post(meta_url, json=payload, headers=headers, timeout=5.0)
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
            data = resp.json() if resp.text else {}
            if resp.ok and data.get("messages"):
                msg_id = data["messages"][0].get("id", "meta_msg")
                return {
                    "sent": True,
                    "provider": "Meta WhatsApp Cloud API",
                    "message_sid": msg_id,
                    "latency_ms": elapsed_ms,
                    "status_detail": f"Delivered via Meta Cloud API (ID: {msg_id})",
                    "deep_link": deep_link,
                }
            err_msg = data.get("error", {}).get("message") or f"Meta HTTP {resp.status_code}"
            return {
                "sent": False,
                "provider": "Meta WhatsApp Cloud API",
                "message_sid": None,
                "latency_ms": elapsed_ms,
                "status_detail": f"Meta Graph API error: {err_msg}",
                "deep_link": deep_link,
            }
        except Exception as exc:
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
            return {
                "sent": False,
                "provider": "Meta WhatsApp Cloud API",
                "message_sid": None,
                "latency_ms": elapsed_ms,
                "status_detail": f"Meta Graph API error: {str(exc)[:120]}",
                "deep_link": deep_link,
            }

    # 4. UNCONFIGURED FALLBACK: PROVIDE DIRECT DEEP-LINK
    elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))
    return {
        "sent": False,
        "provider": "Direct WhatsApp Launcher",
        "message_sid": None,
        "latency_ms": elapsed_ms,
        "status_detail": "No backend WhatsApp API key configured (Twilio, CallMeBot, or Meta). Direct WhatsApp Launcher ready.",
        "deep_link": deep_link,
    }

