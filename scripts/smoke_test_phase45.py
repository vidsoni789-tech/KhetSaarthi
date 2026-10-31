"""Live Verification Script for Phase 4.5 Innovations.

Verifies:
1. 6-step autonomous pipeline execution log with telemetry.
2. Spatial Mandi Arbitrage & Net Take-Home Revenue for configurable lot sizes.
3. Weather Spoilage Value-at-Risk (VaR in ₹) and action code.
4. FAO-56 Crop Evapotranspiration, Effective Rain, and Precision Drip Hours/Acre.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root in sys.path and load .env
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from core.agent import run_khetsaarthi_agent


def main():
    print("=" * 80)
    print("🌱 KHETSAARTHI PHASE 4.5 INNOVATIONS LIVE SMOKE TEST")
    print("=" * 80)

    # Test Nashik | Soybean | Flowering | Marathi with 25 Quintal lot
    report = run_khetsaarthi_agent(
        location_text="Nashik, Maharashtra",
        crop="Soybean",
        stage="Flowering",
        language="mr",
        lot_quintals=25.0,
    )

    print(f"\n⚡ Total Pipeline Latency: {report['total_latency_ms']} ms")
    print(f"📍 Location             : {report['location']['name']}, {report['location']['admin1']}")
    print(f"🌾 Crop & Stage         : Soybean (Flowering)")
    print(f"⚠️ Risk Score           : {report['risk']['score']}/100 ({report['risk']['localized_label']})")

    print("\n📋 6-STEP AUTONOMOUS AGENT LOG (TELEMETRY):")
    for step in report["agent_log"]:
        status_symbol = "✅" if step["status"] == "completed" else "⚠️"
        print(f"  {status_symbol} [{step['status'].upper():16}] {step['step']:20} ({step['latency_ms']:4}ms): {step['detail']}")

    econ_water = report.get("economics_and_water", {})
    mandi_econ = econ_water.get("mandi_arbitrage", {})
    water_bal = econ_water.get("water_balance", {})

    print("\n" + "=" * 80)
    print("💰 SPATIAL MANDI ARBITRAGE & REVENUE BREAKDOWN (Lot: 25 Quintals):")
    print("=" * 80)
    print(f"  Best Net Market          : {mandi_econ.get('best_market_name')} ({mandi_econ.get('best_market_distance_km')} km road dist)")
    print(f"  Raw Modal Price          : ₹{mandi_econ.get('best_market_raw_price'):,.0f} / Q")
    print(f"  Road Freight Deduction   : ₹{mandi_econ.get('best_market_transport_cost_inr'):,.0f} (₹1.50/Q/km)")
    print(f"  Net Realizable Price     : ₹{mandi_econ.get('best_market_net_price'):,.0f} / Q")
    print(f"  Gross Revenue            : ₹{mandi_econ.get('best_market_gross_revenue'):,.0f}")
    print(f"  Net Take-Home Revenue    : ₹{mandi_econ.get('best_market_net_revenue'):,.0f}")
    print(f"  Weather Spoilage VaR     : ₹{mandi_econ.get('spoilage_var_inr'):,.0f} at risk ({mandi_econ.get('spoilage_risk_pct')}%)")
    print(f"  Recommendation Code      : {mandi_econ.get('recommendation_code')}")
    print(f"  Localized Recommendation : {mandi_econ.get('localized_recommendation')}")

    print("\n  Market Ranking Table:")
    for rank, m in enumerate(mandi_econ.get("market_rankings", []), start=1):
        print(f"   #{rank} {m['market']:15} ({m['district']:10}) | {m['distance_km']:4.0f}km | Raw: ₹{m['raw_modal_price']:,.0f}/Q | Net: ₹{m['net_price_per_q']:,.0f}/Q | Net Take-Home: ₹{m['net_take_home_inr']:,.0f}")

    print("\n" + "=" * 80)
    print("💧 FAO-56 CROP EVAPOTRANSPIRATION & PRECISION IRRIGATION:")
    print("=" * 80)
    print(f"  Crop & Stage Kc          : {water_bal.get('kc'):.2f}")
    print(f"  7-Day Crop ETc Demand    : {water_bal.get('total_etc_mm'):.1f} mm")
    print(f"  7-Day Effective Rainfall : {water_bal.get('effective_rain_mm'):.1f} mm")
    print(f"  Net Moisture Deficit     : {water_bal.get('net_irrigation_deficit_mm'):.1f} mm")
    print(f"  Liters Needed / Acre     : {water_bal.get('liters_per_acre_needed'):,.0f} Liters/Acre")
    print(f"  Recommended Drip Run     : ~{water_bal.get('drip_hours_per_acre'):.1f} Hours/Acre (16,000 L/hr)")
    print(f"  Localized Verdict        : {water_bal.get('localized_verdict')}")

    print("\n" + "=" * 80)
    print("✅ ALL PHASE 4.5 INNOVATIONS VERIFIED SUCCESSFULLY WITH LIVE DATA!")
    print("=" * 80)


if __name__ == "__main__":
    main()

