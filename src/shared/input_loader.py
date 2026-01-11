#src/shared/input_loader.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class CallTranscript:
    call_id: str
    text: str
    path: str


class InputLoader:
    """
    Loads mock call transcripts from:
      repo_root/mock-data/calls/*.txt
    """

    def __init__(self, calls_dir: Optional[str] = None) -> None:
        self._calls_dir = Path(calls_dir) if calls_dir else self._default_calls_dir()

    def list_call_paths(self) -> List[Path]:
        if not self._calls_dir.exists():
            return []
        return sorted(self._calls_dir.glob("*.txt"))

    def load_all_calls(self) -> List[CallTranscript]:
        calls: List[CallTranscript] = []
        for p in self.list_call_paths():
            call_id = p.stem 
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            calls.append(CallTranscript(call_id=call_id, text=text, path=str(p)))
        return calls

    def load_call(self, call_id: str) -> Optional[CallTranscript]:
        """
        Load one call by id.
        """
        p = self._calls_dir / f"{call_id}.txt"
        if not p.exists():
            return None
        text = p.read_text(encoding="utf-8", errors="replace").strip()
        return CallTranscript(call_id=call_id, text=text, path=str(p))

    def _default_calls_dir(self) -> Path:
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / "mock-data" / "calls"
