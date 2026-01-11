#src/shared/ml/coach_quality_model.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib


class CoachQualityModel:
    """
    Loads a trained sklearn model and predicts probability that a call is 'good'.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        default_path = repo_root / "artifacts" / "models" / "coach_model.joblib"
        self.model_path = Path(model_path) if model_path else default_path
        self.model = joblib.load(self.model_path)

    def predict_good_call_prob(self, features: dict) -> float:
        X = [[
            int(features["empathy_hits"]),
            int(features["objection_count"]),
            int(bool(features["closing_attempted"])),
            int(features["long_monologue_lines"]),
            int(features["total_lines"]),
        ]]
        prob = float(self.model.predict_proba(X)[0][1])
        return max(0.0, min(1.0, prob))
