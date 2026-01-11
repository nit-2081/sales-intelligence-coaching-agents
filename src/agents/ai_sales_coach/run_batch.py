#src/agents/ai_sales_coach/run_batch.py
from __future__ import annotations

import json
from pathlib import Path

from src.shared.kill_switch import KillSwitch
from src.shared.input_loader import InputLoader
from src.agents.ai_sales_coach.signal_extractor import SignalExtractor
from src.agents.ai_sales_coach.scoring_engine import ScoringEngine
from src.agents.ai_sales_coach.tip_generator import generate_tips
from src.agents.ai_sales_coach.feedback_logger import FeedbackLogger, FeedbackEvent


AGENT_NAME = "ai_sales_coach"


def run_daily_batch() -> None:
    # 1. Kill switch check
    kill_switch = KillSwitch()
    if kill_switch.is_disabled(AGENT_NAME):
        print(f"[SKIP] {AGENT_NAME} is disabled by kill switch.")
        return

    # 2. Load inputs
    loader = InputLoader()
    calls = loader.load_all_calls()

    if not calls:
        print("[INFO] No calls found. Nothing to process.")
        return

    extractor = SignalExtractor()
    scorer = ScoringEngine()
    feedback_logger = FeedbackLogger()

    output_dir = _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[START] Processing {len(calls)} calls...\n")

    for call in calls:
        # 3. Intelligence pipeline
        signals = extractor.extract(call.text)
        assessment = scorer.score(signals)

        performance_summary = {
            "call_id": call.call_id,
            "rep_id": "rep_01",
            "signals": signals.to_dict(),
            "scores": assessment.scores.to_dict(),
            "top_gaps": assessment.top_gaps,
            "confidence": assessment.confidence,
        }

        tips = generate_tips(performance_summary=performance_summary, top_gaps=assessment.top_gaps)

        # 4. Build final output
        output = {
            "agent": AGENT_NAME,
            "call_id": call.call_id,
            "rep_id": "rep_01",
            "scores": assessment.scores.to_dict(),
            "top_gaps": assessment.top_gaps,
            "micro_tips": tips,
            "confidence": assessment.confidence,
            "reasons": assessment.reasons,
        }

        # 5. Save output JSON
        out_path = output_dir / f"{call.call_id}_output.json"
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

        # 6. Mock feedback logging (simulate human-in-loop)
        feedback_logger.log(
            FeedbackEvent(
                agent_name=AGENT_NAME,
                rep_id="rep_01",
                call_id=call.call_id,
                tips_shown=tips,
                action="helpful"
            )
        )

        print(f"[OK] Processed {call.call_id}")
        print(f"     Top gaps: {assessment.top_gaps}")
        print(f"     Tips: {tips[0]}")

    print("\n[DONE] AI Sales Coach batch completed.")


def _output_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "mock-data" / "outputs" / "ai_sales_coach"


if __name__ == "__main__":
    run_daily_batch()
