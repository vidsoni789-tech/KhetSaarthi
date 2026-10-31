"""Live Smoke Test for Phase 2: Live APIs & Agent Execution Telemetry.

Location: Nashik, Maharashtra | Soybean | Flowering | Marathi (mr)
Also tests: Lasalgaon, Nashik (smart geocoding fallback)
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from core.agent import run_advisory
from core.sources import geocode_location, get_mandi_prices

DIVIDER = "=" * 76


def run_phase2_smoke_test():
    print(f"\n{DIVIDER}")
    print("🌱 KHETSAARTHI PHASE 2 LIVE SMOKE TEST")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(DIVIDER)

    # 1. Test Smart Geocoding Fallback for 'Lasalgaon, Nashik'
    print("\n[1/3] SMART GEOCODING TEST: 'Lasalgaon, Nashik'")
    t0 = time.perf_counter()
    place_lasalgaon = geocode_location("Lasalgaon, Nashik")
    geo_time = int((time.perf_counter() - t0) * 1000)
    print(f"  ✅ Resolved in: {geo_time}ms")
    print(f"  ✅ Name: {place_lasalgaon['name']}, State: {place_lasalgaon['admin1']}, District: {place_lasalgaon['admin2']}")
    print(f"  ✅ Coords: {place_lasalgaon['latitude']:.4f}, {place_lasalgaon['longitude']:.4f}")
    assert place_lasalgaon["admin2"] == "Nashik" or "Nashik" in str(place_lasalgaon["candidates"])

    # 2. Test Mandi Explicit Bypass (api_key="")
    print("\n[2/3] MANDI EXPLICIT BYPASS TEST: api_key=''")
    t0 = time.perf_counter()
    mandi_bypass = get_mandi_prices("Maharashtra", "Soybean", api_key="")
    mandi_time = int((time.perf_counter() - t0) * 1000)
    print(f"  ✅ Response in: {mandi_time}ms")
    print(f"  ✅ Connected: {mandi_bypass['connected']}")
    print(f"  ✅ Status: {mandi_bypass['status']}")
    print(f"  ✅ Message: {mandi_bypass['message']}")
    assert mandi_bypass["connected"] is False
    assert mandi_bypass["status"] == "unconfigured"

    # 3. Live Full Agent Run for: Nashik, Maharashtra | Soybean | Flowering | Marathi
    print("\n[3/3] FULL LIVE AGENT RUN: Nashik, Maharashtra | Soybean | Flowering | Marathi")
    live_key = os.getenv("DATA_GOV_API_KEY", "").strip()
    print(f"  Configured Key in .env: {live_key[:8]}...{live_key[-4:]}" if live_key else "  No key configured")

    t_agent_0 = time.perf_counter()
    report = run_advisory(
        location_text="Nashik, Maharashtra",
        crop="Soybean",
        stage="Flowering",
        language="mr",
        mandi_commodity="Soybean",
        mandi_api_key=live_key,
    )
    total_wall_ms = int((time.perf_counter() - t_agent_0) * 1000)

    print(f"\n{DIVIDER}")
    print("AGENT EXECUTION TRACE & TELEMETRY")
    print(DIVIDER)
    print(f"⚡ Pipeline Latency (Internal): {report.get('total_latency_ms', 'N/A')} ms")
    print(f"⏱️ Total Wall Clock Latency : {total_wall_ms} ms")
    print(f"📍 Location                : {report['location']['name']}, {report['location']['admin1']} ({report['location']['latitude']:.4f}, {report['location']['longitude']:.4f})")
    print(f"🌾 Crop & Stage            : {report['risk']['crop']} ({report['risk']['stage']})")
    print(f"⚠️ Risk Index              : {report['risk']['score']}/100 [{report['risk']['label']} / {report['risk']['localized_label']}]")
    print(f"🛒 Mandi Status            : {report['mandi'].get('status')} (records: {len(report['mandi'].get('records', []))})")
    print("\nDetailed Step Log:")
    for event in report["agent_log"]:
        icon = {
            "completed": "✅",
            "partial_fallback": "⚠️",
            "failed": "❌",
            "skipped": "⏭️",
            "running": "⏳",
        }.get(event["status"], "•")
        print(f"  {icon} [{event['status'].upper():16s}] {event['step']:12s} ({event.get('latency_ms', 0):>4}ms) : {event['detail']}")
        if event.get("evidence"):
            print(f"     ↳ Evidence: {event['evidence']}")

    print(f"\n{DIVIDER}")
    print("ACTIONS LOCALIZED (MARATHI):")
    for i, action in enumerate(report["risk"]["actions"], 1):
        print(f"  {i}. {action}")
    print(DIVIDER)

    # Validation assertions
    assert report["location"]["name"] == "Nashik"
    assert len(report["risk"]["forecast_rows"]) == 7
    assert any(step["step"] == "geocode" and step["status"] == "completed" for step in report["agent_log"])
    assert any(step["step"] == "weather" and step["status"] == "completed" for step in report["agent_log"])
    assert any(step["step"] == "mandi" for step in report["agent_log"])
    assert any(step["step"] == "risk_engine" and step["status"] == "completed" for step in report["agent_log"])
    assert any(step["step"] == "validation" and step["status"] == "completed" for step in report["agent_log"])
    print("\n✅ ALL PHASE 2 VERIFICATIONS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_phase2_smoke_test()

