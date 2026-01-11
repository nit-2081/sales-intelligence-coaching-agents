# src/shared/kill_switch.py
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KillSwitchState:
    global_disabled: bool
    agents: Dict[str, bool]


class KillSwitch:
    """
    Global + per-agent kill switch.

    Reads/writes repo_root/kill_switch.json

    Rules:
    - If global_disabled = True → ALL agents disabled
    - agents[name] = True → that agent disabled
    - Missing file = everything enabled (safe default)
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._config_path = Path(config_path) if config_path else self._default_config_path()
        self._cached_mtime: Optional[float] = None
        self._cached_state: KillSwitchState = KillSwitchState(
            global_disabled=False,
            agents={},
        )

    # ------------------------------------------------------------------
    # PUBLIC API (USED BY AGENTS + UI)
    # ------------------------------------------------------------------

    def is_disabled(self, agent_name: str) -> bool:
        """True if global kill switch OR agent-specific switch is ON."""
        state = self._load_state_if_needed()
        if state.global_disabled:
            return True
        return bool(state.agents.get(agent_name, False))

    def get_state(self) -> KillSwitchState:
        """Return full current kill switch state."""
        return self._load_state_if_needed()

    def set_global_disabled(self, disabled: bool) -> None:
        """Enable/disable ALL agents."""
        with self._lock:
            state = self._load_state_unlocked()
            self._write_state(
                global_disabled=bool(disabled),
                agents=dict(state.agents),
            )

    def set_agent_disabled(self, agent_name: str, disabled: bool) -> None:
        """Enable/disable a single agent."""
        if not agent_name or not isinstance(agent_name, str):
            raise ValueError("agent_name must be a non-empty string")

        with self._lock:
            state = self._load_state_unlocked()
            agents = dict(state.agents)
            agents[agent_name] = bool(disabled)
            self._write_state(
                global_disabled=bool(state.global_disabled),
                agents=agents,
            )

    # ------------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------------

    def _default_config_path(self) -> Path:
        # repo_root/src/shared/kill_switch.py → repo_root/kill_switch.json
        return Path(__file__).resolve().parents[2] / "kill_switch.json"

    def _load_state_if_needed(self) -> KillSwitchState:
        with self._lock:
            return self._load_state_unlocked()

    def _load_state_unlocked(self) -> KillSwitchState:
        try:
            if not self._config_path.exists():
                self._cached_state = KillSwitchState(False, {})
                self._cached_mtime = None
                return self._cached_state

            mtime = self._config_path.stat().st_mtime
            if self._cached_mtime == mtime:
                return self._cached_state

            data = self._read_json(self._config_path)
            state = self._parse_state(data)

            self._cached_state = state
            self._cached_mtime = mtime
            return state

        except Exception:
            # Fail-safe: everything enabled
            self._cached_state = KillSwitchState(False, {})
            self._cached_mtime = None
            return self._cached_state

    def _write_state(self, global_disabled: bool, agents: Dict[str, bool]) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "global_disabled": bool(global_disabled),
            "agents": {k: bool(v) for k, v in (agents or {}).items()},
        }

        tmp = self._config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._config_path)

        # invalidate cache so UI updates immediately
        self._cached_mtime = None

    def _read_json(self, path: Path) -> Dict[str, Any]:
        raw = path.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else {}

    def _parse_state(self, data: Dict[str, Any]) -> KillSwitchState:
        global_disabled = bool(data.get("global_disabled", False))
        agents_raw = data.get("agents", {}) or {}

        agents: Dict[str, bool] = {}
        if isinstance(agents_raw, dict):
            for k, v in agents_raw.items():
                if isinstance(k, str):
                    agents[k] = bool(v)

        return KillSwitchState(global_disabled, agents)
