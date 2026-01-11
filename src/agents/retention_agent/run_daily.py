from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from src.agents.retention_agent.output_formatter import OutputFormatter
from src.agents.retention_agent.action_router import ActionRouter
from src.agents.retention_agent.churn_model import ChurnModel
from src.agents.retention_agent.signal_extractor import RetentionSignalExtractor, RetentionSignals
from src.shared.kill_switch import KillSwitch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_telemetry_path() -> Path:
    return _repo_root() / "mock-data" / "telemetry" / "usage.csv"


def _output_dir() -> Path:
    return _repo_root() / "mock-data" / "outputs" / "retention_agent"


def _parse_week_index(week_value: str) -> int:
    """
    Accepts values like: 'Week_1', 'Week_04', 'week_3'
    Returns numeric index for sorting. Unknown formats sort last.
    """
    if not week_value:
        return 10**9
    s = str(week_value).strip().lower()
    if "week" not in s:
        return 10**9
    # extract digits
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return 10**9
    try:
        return int(digits)
    except Exception:
        return 10**9


def _drop_pct(early: float | None, late: float | None) -> float | None:
    if early is None or late is None:
        return None
    if early <= 0:
        return None
    raw = (early - late) / early
    if raw <= 0:
        return 0.0
    if raw >= 1:
        return 1.0
    return raw


def _avg(nums: List[float]) -> float | None:
    if not nums:
        return None
    return sum(nums) / float(len(nums))


def _compute_numeric_drop(sorted_rows: List[Dict[str, Any]], key: str) -> Tuple[float | None, float | None, float | None]:
    """
    Computes early_avg, late_avg, drop_pct for a numeric column using half-window split.
    """
    n = len(sorted_rows)
    if n == 0:
        return None, None, None
    mid = n // 2
    early = sorted_rows[:mid] if mid > 0 else sorted_rows
    late = sorted_rows[mid:] if mid > 0 else sorted_rows

    def num_seq(rows: List[Dict[str, Any]]) -> List[float]:
        out: List[float] = []
        for r in rows:
            v = r.get(key)
            if v is None or v == "":
                continue
            try:
                out.append(float(v))
            except Exception:
                continue
        return out

    early_avg = _avg(num_seq(early))
    late_avg = _avg(num_seq(late))
    drop = _drop_pct(early_avg, late_avg)
    return early_avg, late_avg, drop


def load_usage_csv(path: Path) -> List[Dict[str, Any]]:
    """
    Loads telemetry CSV into list[dict]. Expected columns (your dataset):
      customer_id, week, logins, leads_created, features_used
    """
    if not path.exists():
        raise FileNotFoundError(f"Telemetry file not found: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r or all((v is None or str(v).strip() == "") for v in r.values()):
                continue
            rows.append({k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
    return rows


def group_by_customer(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        cid = (r.get("customer_id") or "").strip()
        if not cid:
            continue
        grouped.setdefault(cid, []).append(r)
    return grouped


def run_daily_batch(
    telemetry_path: Path | None = None,
    out_path: Path | None = None,
) -> Dict[str, Any]:
    """
    Runs the Retention Agent daily batch and writes an output JSON.

    Returns the output dict for convenience/testing.
    """
    telemetry_path = telemetry_path or _default_telemetry_path()
    out_dir = _output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (out_dir / "daily_output.json")

    # Kill switch gating (global + per-agent)
    ks = KillSwitch()
    if ks.is_disabled("global") or ks.is_disabled("retention_agent"):
        payload = {
            "status": "disabled",
            "reason": "Kill switch is ON (global or retention_agent).",
            "telemetry_path": str(telemetry_path),
            "output_path": str(out_path),
            "customers_processed": 0,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    rows = load_usage_csv(telemetry_path)
    grouped = group_by_customer(rows)

    extractor = RetentionSignalExtractor(
        date_key="__no_date__",
        logins_key="logins",
        minutes_key="leads_created",   
        feature_key="__unused__",     
        low_usage_login_threshold=1.0,
    )
    model = ChurnModel()
    router = ActionRouter()
    formatter = OutputFormatter()
    customer_cards: List[Dict[str, Any]] = []

    for customer_id, cust_rows in grouped.items():
        cust_rows_sorted = sorted(
            cust_rows,
            key=lambda r: _parse_week_index(str(r.get("week", ""))),
        )
        signals = extractor.extract(cust_rows_sorted)
        feat_early, feat_late, feat_drop = _compute_numeric_drop(cust_rows_sorted, key="features_used")

        signals = RetentionSignals(
            window_days=signals.window_days,
            login_drop_pct=signals.login_drop_pct,
            active_minutes_drop_pct=signals.active_minutes_drop_pct,
            feature_usage_drop_pct=feat_drop,
            inactive_streak_days=signals.inactive_streak_days,
            low_usage_days=signals.low_usage_days,
            avg_logins_early=signals.avg_logins_early,
            avg_logins_late=signals.avg_logins_late,
            avg_minutes_early=signals.avg_minutes_early,
            avg_minutes_late=signals.avg_minutes_late,
            feature_rate_early=feat_early,
            feature_rate_late=feat_late,
        )

        assessment = model.score(signals)
        action_decision = router.route(assessment.churn_score, assessment.confidence)

        card = formatter.format_card(
            customer_id=customer_id,
            latest_period=cust_rows_sorted[-1].get("week") if cust_rows_sorted else None,
            signals=signals,
            assessment=assessment,
            action=action_decision,
        )

        customer_cards.append(card.to_dict())

        # Optional (manual, not automatic):
        # feedback_logger.log(
        #     FeedbackEvent(
        #         timestamp_utc=FeedbackLogger.now_utc_iso(),
        #         customer_id=customer_id,
        #         recommended_action=card.recommended_action,
        #         action_taken="accepted",  # example only
        #         churn_score=assessment.churn_score,
        #         confidence=assessment.confidence,
        #     )
        # )


    # Sort output by churn_score desc (highest risk on top)
    customer_cards.sort(key=lambda c: float(c["churn_score"]), reverse=True)

    payload = {
        "status": "ok",
        "telemetry_path": str(telemetry_path),
        "output_path": str(out_path),
        "customers_processed": len(customer_cards),
        "customers": customer_cards,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run_daily_batch()
    print(f"[OK] Retention daily batch complete. Customers: {result.get('customers_processed')}")
    print(f"Output: {result.get('output_path')}")
