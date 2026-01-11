from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.shared.kill_switch import KillSwitch

# Import your engine modules (we'll implement/verify each next)
from src.agents.negotiator_agent.sentiment_engine import SentimentEngine
from src.agents.negotiator_agent.objection_detector import ObjectionDetector
from src.agents.negotiator_agent.decision_engine import DecisionEngine
from src.agents.negotiator_agent.llm_whisper_generator import LLMWhisperGenerator
from src.agents.negotiator_agent.fallback_templates import FallbackTemplateGenerator
from src.agents.negotiator_agent.output_formatter import OutputFormatter


@dataclass
class ChunkEvent:
    call_id: str
    chunk_id: int
    chunk_text: str
    ts_epoch: float


def _repo_root() -> Path:
    # src/agents/negotiator_agent/run_stream.py -> repo root
    return Path(__file__).resolve().parents[3]


def _calls_dir() -> Path:
    return _repo_root() / "mock-data" / "calls"


def _output_dir() -> Path:
    out = _repo_root() / "mock-data" / "outputs" / "negotiator_agent"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk_transcript_lines(transcript_text: str, lines_per_chunk: int = 3) -> List[str]:
    """
    Streaming simulation: chunk by N lines (utterances).
    Each line is expected to look like: 'Customer: ...' / 'Rep: ...'
    """
    lines = [ln.strip() for ln in transcript_text.splitlines() if ln.strip()]
    if not lines:
        return []

    chunks: List[str] = []
    for i in range(0, len(lines), lines_per_chunk):
        chunk_lines = lines[i : i + lines_per_chunk]
        chunks.append("\n".join(chunk_lines))
    return chunks


def list_negotiator_call_paths() -> List[Path]:
    """
    Prefer files named like neg_call_01.txt etc.
    If none exist, falls back to any call_*.txt to keep demo moving.
    """
    calls_dir = _calls_dir()
    preferred = sorted(calls_dir.glob("neg_call_*.txt"))
    if preferred:
        return preferred
    return sorted(calls_dir.glob("call_*.txt"))


def run_stream_for_call(
    call_path: Path,
    *,
    lines_per_chunk: int = 3,
    simulate_latency_s: float = 0.15,
    context_window_n: int = 4,
) -> Dict[str, Any]:
    """
    Runs a simulated streaming session for one call and returns a session output dict.
    """
    kill = KillSwitch()  # uses default kill_switch.json
    if kill.is_disabled("negotiator_agent"):
        return {
            "call_id": call_path.stem,
            "status": "skipped",
            "reason": "kill_switch_enabled",
        }

    transcript = _read_text(call_path)
    chunks = chunk_transcript_lines(transcript, lines_per_chunk=lines_per_chunk)

    sentiment_engine = SentimentEngine()
    objection_detector = ObjectionDetector()
    llm = LLMWhisperGenerator()
    fallback = FallbackTemplateGenerator()
    decision_engine = DecisionEngine(
        llm_generator=llm,
        fallback_generator=fallback,
        min_soft_confidence=0.60,
        min_strong_confidence=0.80,
        context_window_n=context_window_n,
    )
    formatter = OutputFormatter()

    session_out: Dict[str, Any] = {
        "call_id": call_path.stem,
        "input_file": str(call_path),
        "mode": "simulated_stream",
        "lines_per_chunk": lines_per_chunk,
        "context_window_n": context_window_n,
        "whispers": [],
    }

    rolling_context: List[str] = []

    for idx, chunk_text in enumerate(chunks, start=1):
        # Runtime kill-switch check (can stop mid-call)
        if kill.is_disabled("negotiator_agent"):
            session_out["status"] = "stopped"
            session_out["reason"] = "kill_switch_enabled_midstream"
            break

        event = ChunkEvent(
            call_id=call_path.stem,
            chunk_id=idx,
            chunk_text=chunk_text,
            ts_epoch=time.time(),
        )

        # Maintain rolling context (last N chunks)
        rolling_context.append(event.chunk_text)
        if len(rolling_context) > context_window_n:
            rolling_context = rolling_context[-context_window_n:]

        # Understand signals
        sentiment = sentiment_engine.analyze(event.chunk_text, context=rolling_context)
        objections = objection_detector.detect(event.chunk_text)

        # Decide + generate whisper (LLM-first with fallback inside decision_engine)
        decision = decision_engine.decide(
            call_id=event.call_id,
            chunk_id=event.chunk_id,
            chunk_text=event.chunk_text,
            context_window=rolling_context,
            sentiment=sentiment,
            objections=objections,
        )

        # Format human-facing output (even if "no whisper", formatter can choose to omit)
        whisper_card = formatter.format(decision)

        if whisper_card is not None:
            session_out["whispers"].append(whisper_card)

        # Simulated low latency (Phase 4)
        if simulate_latency_s and simulate_latency_s > 0:
            time.sleep(simulate_latency_s)

    if "status" not in session_out:
        session_out["status"] = "ok"

    return session_out


def main() -> None:
    out_dir = _output_dir()
    call_paths = list_negotiator_call_paths()

    if not call_paths:
        print("[WARN] No call transcripts found in mock-data/calls/.")
        return

    print(f"[START] Negotiator stream demo for {len(call_paths)} calls...")

    for call_path in call_paths:
        result = run_stream_for_call(call_path)

        status = result.get("status", "unknown")
        out_path = out_dir / f"{call_path.stem}_whispers.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        if status == "skipped":
            print(f"[SKIPPED] {call_path.name} (kill switch) -> {out_path}")
        elif status == "stopped":
            print(f"[STOPPED] {call_path.name} (midstream kill switch) -> {out_path}")
        else:
            print(f"[OK] {call_path.name} -> {out_path}")

    print("[DONE] Negotiator Agent streaming demo complete.")


if __name__ == "__main__":
    main()
