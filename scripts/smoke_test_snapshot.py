import sys
import io
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path and load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from core.agent import run_advisory
from core.chat import answer_farmer_query

def main():
    report = run_advisory(
        location_text="Nashik, Maharashtra",
        crop="Soybean",
        stage="Flowering",
        language="mr",
    )

    print("=== ORCHESTRATION REPORT ===")
    print("Total latency:", report["total_latency_ms"], "ms")
    print("Location:", report["location"]["name"], report["location"]["latitude"], report["location"]["longitude"])
    print("Mandi status:", report["mandi"]["status"])
    print("Mandi is_snapshot:", report["mandi"].get("is_snapshot"))
    print("Mandi query level:", report["mandi"].get("query_level"))
    print("Mandi records found:", len(report["mandi"].get("records", [])))
    if report["mandi"].get("records"):
        print("First record:", report["mandi"]["records"][0])

    print("\n=== EXECUTION LOG (AGENT TRACE) ===")
    for step in report["agent_log"]:
        print(f"[{step['step']}] status={step['status']} ({step['latency_ms']}ms): {step['detail']}")

    print("\n=== RISK ENGINE ACTIONS ===")
    for a in report["risk"]["actions"]:
        print("-", a)

    print("\n=== CHAT Q&A (MARATHI MARKET QUERY) ===")
    q_mr = "माझ्या पिकाचा आजचा बाजारभाव काय आहे?"
    ans_mr = answer_farmer_query(q_mr, report, "mr")
    print(ans_mr)


if __name__ == "__main__":
    main()

