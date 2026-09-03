"""
AgentShield — Baseline Risk Evaluation

Baseline system:
- Block if amount exceeds authorized limit
- Block if merchant category is not authorized
- Otherwise allow

This represents a simple static authorization system.
"""

import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)


DATA_PATH = "data/raw/synthetic_transactions_v3.csv"


def baseline_decision(row):
    """
    Static authorization baseline.

    Returns:
        1 = BLOCK
        0 = ALLOW
    """

    # Rule 1: spending limit
    if row["amount"] > row["authorized_limit"]:
        return 1

    # Rule 2: category authorization
    allowed_categories = str(
        row["allowed_categories"]
    ).split("|")

    if row["merchant_category"] not in allowed_categories:
        return 1

    # Otherwise allow
    return 0


def main():

    print("=" * 60)
    print("AgentShield — Baseline Evaluation")
    print("=" * 60)

    # --------------------------------------------------------
    # Load frozen dataset
    # --------------------------------------------------------

    df = pd.read_csv(DATA_PATH)

    print(f"\nLoaded {len(df):,} transactions")

    # --------------------------------------------------------
    # Generate baseline decisions
    # --------------------------------------------------------

    df["baseline_prediction"] = df.apply(
        baseline_decision,
        axis=1
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    y_true = df["label"]
    y_pred = df["baseline_prediction"]

    print("\n=== CONFUSION MATRIX ===")

    print(
        confusion_matrix(
            y_true,
            y_pred
        )
    )

    print("\n=== METRICS ===")

    print(
        f"Precision : {precision_score(y_true, y_pred):.3f}"
    )

    print(
        f"Recall    : {recall_score(y_true, y_pred):.3f}"
    )

    print(
        f"F1 Score  : {f1_score(y_true, y_pred):.3f}"
    )

    print("\n=== CLASSIFICATION REPORT ===")

    print(
        classification_report(
            y_true,
            y_pred,
            target_names=[
                "Legitimate",
                "Abuse"
            ]
        )
    )

    # --------------------------------------------------------
    # Scenario-level detection
    # --------------------------------------------------------

    print("\n=== DETECTION BY SCENARIO ===")

    scenario_detection = (
        df.groupby("scenario")[
            "baseline_prediction"
        ]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    print(
        (scenario_detection * 100)
        .round(1)
        .astype(str)
        .add("%")
        .to_string()
    )


if __name__ == "__main__":
    main()