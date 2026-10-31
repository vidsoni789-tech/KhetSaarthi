"""Live Smoke Test for Phase 3: Risk Engine Upgrades & Multilingual Grounded Q&A.

Runs real live query for:
Nashik, Maharashtra | Soybean | Flowering | Marathi (mr)
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from core.agent import run_advisory
from core.chat import answer_farmer_query, get_suggested_questions

DIVIDER = "=" * 78


def run_phase3_live_test():
    print(f"\n{DIVIDER}")
    print("🌱 KHETSAARTHI PHASE 3 LIVE VERIFICATION TEST")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(DIVIDER)

    # 1. Run live advisory
    print("\n[1/4] Running Live Advisory for Nashik, Maharashtra | Soybean | Flowering | Marathi...")
    t0 = time.perf_counter()
    report = run_advisory(
        location_text="Nashik, Maharashtra",
        crop="Soybean",
        stage="Flowering",
        language="mr",
        mandi_commodity="Soybean",
        mandi_api_key=os.getenv("DATA_GOV_API_KEY", "").strip(),
    )
    wall_ms = int((time.perf_counter() - t0) * 1000)

    risk = report["risk"]
    print(f"  ⚡ Pipeline Latency : {report.get('total_latency_ms', 'N/A')} ms (Wall: {wall_ms} ms)")
    print(f"  📍 Location         : {report['location']['name']}, {report['location']['admin1']}")
    print(f"  🌾 Crop & Stage     : {risk['crop']} ({risk['stage']})")
    print(f"  ⚠️ Risk Score       : {risk['score']}/100 [{risk['label']} / {risk['localized_label']}]")
    print(f"  🚨 Active Alerts    : {len(risk['alerts'])}")
    for a in risk["alerts"]:
        print(f"     • [{a['severity'].upper()}] {a['type']}: {a['fact']}")

    # 2. 7-Day Spray Suitability Schedule
    print(f"\n[2/4] 7-Day Spray & Field-Work Suitability Schedule:")
    print(f"  Best upcoming safe window: {risk.get('best_spray_window', 'None')}")
    print(f"  {'Date':12s} | {'Status':20s} | {'Rain (mm)':10s} | {'Rain Prob':10s} | {'Wind':10s} | {'Reason'}")
    print("  " + "-" * 74)
    for day in risk.get("spray_schedule", []):
        icon = {"SAFE": "✅", "CAUTION": "⚠️", "AVOID": "❌"}.get(day["status"], "•")
        print(f"  {day['date']:12s} | {icon} {day['localized_status']:18s} | {day['rain_mm']:>7.1f} mm | {day['rain_prob']:>8.0f}% | {day['wind_kmh']:>6.1f}km/h | {day['reason']}")

    # 3. Prioritized Actions
    print(f"\n[3/4] Date-Anchored, Prioritized Actions (Marathi):")
    for i, act in enumerate(risk["actions"], 1):
        print(f"  {i}. {act}")

    # 4. Multilingual Grounded Q&A Verification
    print(f"\n[4/4] Grounded Multilingual Q&A (Testing 3 Languages):")

    # Q1: Marathi - Spray Timing
    q1_mr = "फवारणी कधी करावी?"
    ans1_mr = answer_farmer_query(q1_mr, report, "mr")
    print(f"\n  ❓ [Marathi] Farmer: '{q1_mr}'")
    print(f"  💬 Answer:\n{ans1_mr}")

    # Q2: Hindi - Rain Forecast
    q2_hi = "बारिश कब और कितनी होने की संभावना है?"
    ans2_hi = answer_farmer_query(q2_hi, report, "hi")
    print(f"\n  ❓ [Hindi] Farmer: '{q2_hi}'")
    print(f"  💬 Answer:\n{ans2_hi}")

    # Q3: English - Risk Explanation
    q3_en = "Why is the risk score at this level?"
    ans3_en = answer_farmer_query(q3_en, report, "en")
    print(f"\n  ❓ [English] Farmer: '{q3_en}'")
    print(f"  💬 Answer:\n{ans3_en}")

    # Suggested Questions check
    print(f"\n[Bonus] Suggested Quick-Ask Prompts:")
    for l in ["en", "hi", "mr"]:
        sqs = get_suggested_questions(l)
        print(f"  {l.upper()}: {sqs[0]}")

    print(f"\n{DIVIDER}")
    print("✅ PHASE 3 LIVE VERIFICATION COMPLETE")
    print(DIVIDER)


if __name__ == "__main__":
    run_phase3_live_test()

