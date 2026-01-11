from pathlib import Path
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "mock-data" / "ml" / "coach_training.csv"
MODEL_PATH = REPO_ROOT / "artifacts" / "models" / "coach_model.joblib"


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    X = df[[
        "empathy_hits",
        "objection_count",
        "closing_attempted",
        "long_monologue_lines",
        "total_lines",
    ]].copy()

    X["closing_attempted"] = X["closing_attempted"].astype(int)
    y = df["good_call"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = LogisticRegression(max_iter=500)
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print(f"[OK] Saved model: {MODEL_PATH}")
    print(f"[INFO] Quick accuracy (mock): {acc:.2f}")


if __name__ == "__main__":
    main()
