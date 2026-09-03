"""
AgentShield — Final System Evaluation

Compares:
1. Static Authorization Baseline
2. AgentShield (Policy + Behavioral ML)

Evaluation is performed on completely unseen users.

Important:
- ALLOW = no protective intervention
- STEP_UP = protective verification
- BLOCK = hard protective intervention

For binary evaluation, both STEP_UP and BLOCK are counted
as protective interventions.
"""

import pandas as pd
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from src.feature_engineering import (
    add_features,
    MODEL_FEATURES,
)

from src.policy_engine import (
    check_authorization,
    make_decision,
)


DATA_PATH = "data/raw/synthetic_transactions_v3.csv"


def main():

    # ========================================================
    # 1. Load + engineer features
    # ========================================================

    df = pd.read_csv(DATA_PATH)
    df = add_features(df)

    # ========================================================
    # 2. User-level train/test split
    # ========================================================

    X = df[MODEL_FEATURES]
    y = df["label"]
    groups = df["user_id"]

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(
            X,
            y,
            groups=groups,
        )
    )

    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()

    train_users = set(train_df["user_id"])
    test_users = set(test_df["user_id"])

    print("=" * 72)
    print("AgentShield — Final Held-Out Evaluation")
    print("=" * 72)

    print(f"\nTrain users : {len(train_users)}")
    print(f"Test users  : {len(test_users)}")

    print(
        "User overlap: "
        f"{len(train_users.intersection(test_users))}"
    )

    print(f"\nTrain rows: {len(train_df):,}")
    print(f"Test rows : {len(test_df):,}")

    # ========================================================
    # 3. Train behavioral model
    #
    # Only technically-authorized behavioral cases belong here.
    # Budget/category violations remain deterministic policy.
    # ========================================================

    behavioral_train = train_df[
        train_df["scenario"].isin(
            [
                "legitimate",
                "behavioral_anomaly",
                "velocity_abuse",
            ]
        )
    ].copy()

    X_train = behavioral_train[MODEL_FEATURES]
    y_train = behavioral_train["label"]

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(
        X_train
    )

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )

    model.fit(
        X_train_scaled,
        y_train,
    )

    # ========================================================
    # 4. Evaluate every transaction in held-out test set
    # ========================================================

    baseline_predictions = []
    agentshield_predictions = []

    decisions = []
    decision_sources = []
    strong_signal_counts = []
    risk_scores = []

    for _, row in test_df.iterrows():

        transaction = row.to_dict()

        # ----------------------------------------------------
        # Static authorization baseline
        # ----------------------------------------------------

        authorized, _ = check_authorization(
            transaction
        )

        baseline_prediction = (
            0 if authorized else 1
        )

        baseline_predictions.append(
            baseline_prediction
        )

        # ----------------------------------------------------
        # Behavioral ML probability
        # ----------------------------------------------------

        transaction_features = pd.DataFrame(
            [
                {
                    feature: row[feature]
                    for feature in MODEL_FEATURES
                }
            ]
        )

        scaled_features = scaler.transform(
            transaction_features
        )

        risk_score = model.predict_proba(
            scaled_features
        )[0, 1]

        risk_scores.append(
            float(risk_score)
        )

        # ----------------------------------------------------
        # AgentShield final decision
        # ----------------------------------------------------

        result = make_decision(
            transaction,
            risk_score,
        )

        decision = result["decision"]

        decisions.append(decision)

        decision_sources.append(
            result.get(
                "decision_source",
                "UNKNOWN",
            )
        )

        strong_signal_counts.append(
            result.get(
                "strong_signal_count",
                0,
            )
        )

        # ----------------------------------------------------
        # Binary protective-intervention evaluation
        #
        # ALLOW   = predicted legitimate
        # STEP_UP = protective intervention
        # BLOCK   = protective intervention
        # ----------------------------------------------------

        agentshield_prediction = (
            0
            if decision == "ALLOW"
            else 1
        )

        agentshield_predictions.append(
            agentshield_prediction
        )

    # ========================================================
    # 5. Store evaluation outputs
    # ========================================================

    y_test = test_df["label"].to_numpy()

    baseline_predictions = np.array(
        baseline_predictions
    )

    agentshield_predictions = np.array(
        agentshield_predictions
    )

    test_df["risk_score"] = risk_scores
    test_df["decision"] = decisions
    test_df["decision_source"] = decision_sources
    test_df["strong_signal_count"] = strong_signal_counts
    test_df[
        "agentshield_prediction"
    ] = agentshield_predictions

    # ========================================================
    # 6. Metric helper
    # ========================================================

    def print_metrics(name, predictions):

        precision = precision_score(
            y_test,
            predictions,
            zero_division=0,
        )

        recall = recall_score(
            y_test,
            predictions,
            zero_division=0,
        )

        f1 = f1_score(
            y_test,
            predictions,
            zero_division=0,
        )

        matrix = confusion_matrix(
            y_test,
            predictions,
        )

        tn, fp, fn, tp = matrix.ravel()

        print("\n" + "=" * 72)
        print(name)
        print("=" * 72)

        print("\nConfusion Matrix:")
        print(matrix)

        print(
            f"\nPrecision : {precision:.3f}"
        )

        print(
            f"Recall    : {recall:.3f}"
        )

        print(
            f"F1 Score  : {f1:.3f}"
        )

        print(
            f"\nTrue Positives : {tp}"
        )

        print(
            f"False Positives: {fp}"
        )

        print(
            f"False Negatives: {fn}"
        )

        print(
            f"True Negatives : {tn}"
        )

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }

    # ========================================================
    # 7. Baseline vs AgentShield
    # ========================================================

    baseline_metrics = print_metrics(
        "STATIC AUTHORIZATION BASELINE",
        baseline_predictions,
    )

    agentshield_metrics = print_metrics(
        "AGENTSHIELD",
        agentshield_predictions,
    )

    # ========================================================
    # 8. Scenario-level performance
    # ========================================================

    print("\n" + "=" * 72)
    print("SCENARIO-LEVEL DETECTION")
    print("=" * 72)

    for scenario in sorted(
        test_df["scenario"].unique()
    ):

        scenario_df = test_df[
            test_df["scenario"] == scenario
        ]

        if scenario == "legitimate":

            false_positive_rate = (
                scenario_df[
                    "agentshield_prediction"
                ].mean()
            )

            print(
                f"{scenario:25s} "
                f"False-positive rate: "
                f"{false_positive_rate:.3f}"
            )

        else:

            detection_rate = (
                scenario_df[
                    "agentshield_prediction"
                ].mean()
            )

            print(
                f"{scenario:25s} "
                f"Detection rate: "
                f"{detection_rate:.3f}"
            )

    # ========================================================
    # 9. Decision distribution
    # ========================================================

    print("\n" + "=" * 72)
    print("DECISION DISTRIBUTION")
    print("=" * 72)

    decision_counts = (
        test_df["decision"]
        .value_counts()
        .reindex(
            [
                "ALLOW",
                "STEP_UP",
                "BLOCK",
            ],
            fill_value=0,
        )
    )

    for decision, count in (
        decision_counts.items()
    ):
        print(
            f"{decision:10s}: {count}"
        )

    # ========================================================
    # 10. False-positive friction analysis
    # ========================================================

    print("\n" + "=" * 72)
    print("FALSE-POSITIVE FRICTION ANALYSIS")
    print("=" * 72)

    legitimate_df = test_df[
        test_df["label"] == 0
    ].copy()

    legitimate_count = len(
        legitimate_df
    )

    false_positive_df = legitimate_df[
        legitimate_df["decision"]
        != "ALLOW"
    ].copy()

    fp_total = len(
        false_positive_df
    )

    fp_step_up = int(
        (
            false_positive_df["decision"]
            == "STEP_UP"
        ).sum()
    )

    fp_block = int(
        (
            false_positive_df["decision"]
            == "BLOCK"
        ).sum()
    )

    friction_rate = (
        fp_total / legitimate_count
        if legitimate_count > 0
        else 0.0
    )

    step_up_friction_rate = (
        fp_step_up / legitimate_count
        if legitimate_count > 0
        else 0.0
    )

    false_block_rate = (
        fp_block / legitimate_count
        if legitimate_count > 0
        else 0.0
    )

    print(
        f"\nLegitimate transactions : "
        f"{legitimate_count}"
    )

    print(
        f"Protective interventions: "
        f"{fp_total}"
    )

    print(
        f"False STEP_UP events    : "
        f"{fp_step_up}"
    )

    print(
        f"False BLOCK events      : "
        f"{fp_block}"
    )

    print(
        f"\nOverall friction rate   : "
        f"{friction_rate:.3%}"
    )

    print(
        f"STEP_UP friction rate   : "
        f"{step_up_friction_rate:.3%}"
    )

    print(
        f"False hard-block rate   : "
        f"{false_block_rate:.3%}"
    )

    # ========================================================
    # 11. Intervention breakdown for risky transactions
    # ========================================================

    print("\n" + "=" * 72)
    print("RISKY TRANSACTION INTERVENTION BREAKDOWN")
    print("=" * 72)

    risky_df = test_df[
        test_df["label"] == 1
    ].copy()

    risky_total = len(
        risky_df
    )

    risky_allow = int(
        (
            risky_df["decision"]
            == "ALLOW"
        ).sum()
    )

    risky_step_up = int(
        (
            risky_df["decision"]
            == "STEP_UP"
        ).sum()
    )

    risky_block = int(
        (
            risky_df["decision"]
            == "BLOCK"
        ).sum()
    )

    print(
        f"\nRisky transactions : "
        f"{risky_total}"
    )

    print(
        f"Allowed             : "
        f"{risky_allow}"
    )

    print(
        f"STEP_UP             : "
        f"{risky_step_up}"
    )

    print(
        f"BLOCK               : "
        f"{risky_block}"
    )

    protective_rate = (
        (
            risky_step_up
            + risky_block
        )
        / risky_total
        if risky_total > 0
        else 0.0
    )

    print(
        f"\nProtective-intervention recall: "
        f"{protective_rate:.3%}"
    )

    # ========================================================
    # 12. Decision-source breakdown
    # ========================================================

    print("\n" + "=" * 72)
    print("DECISION SOURCE BREAKDOWN")
    print("=" * 72)

    source_counts = (
        test_df["decision_source"]
        .value_counts()
    )

    print(
        source_counts.to_string()
    )

    # ========================================================
    # 13. Strong-signal distribution
    # ========================================================

    print("\n" + "=" * 72)
    print("STRONG-SIGNAL DISTRIBUTION")
    print("=" * 72)

    signal_counts = (
        test_df[
            "strong_signal_count"
        ]
        .value_counts()
        .sort_index()
    )

    for signal_count, count in (
        signal_counts.items()
    ):
        print(
            f"{int(signal_count)} "
            f"strong signal(s): "
            f"{count}"
        )

    # ========================================================
    # 14. Improvement over baseline
    # ========================================================

    print("\n" + "=" * 72)
    print("BASELINE → AGENTSHIELD IMPROVEMENT")
    print("=" * 72)

    print(
        f"\nRecall: "
        f"{baseline_metrics['recall']:.3f}"
        f" → "
        f"{agentshield_metrics['recall']:.3f}"
    )

    print(
        f"F1: "
        f"{baseline_metrics['f1']:.3f}"
        f" → "
        f"{agentshield_metrics['f1']:.3f}"
    )

    print(
        f"False negatives: "
        f"{baseline_metrics['fn']}"
        f" → "
        f"{agentshield_metrics['fn']}"
    )

    print(
        f"False positives: "
        f"{baseline_metrics['fp']}"
        f" → "
        f"{agentshield_metrics['fp']}"
    )

    # ========================================================
    # 15. Final summary
    # ========================================================

    print("\n" + "=" * 72)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 72)

    print(
        "\nAgentShield evaluates explicit authorization "
        "separately from behavioral risk."
    )

    print(
        "STEP_UP represents additional user verification, "
        "while BLOCK represents a hard intervention."
    )

    print(
        "\nOn this synthetic held-out benchmark:"
    )

    print(
        f"- Protective-intervention precision: "
        f"{agentshield_metrics['precision']:.3%}"
    )

    print(
        f"- Protective-intervention recall: "
        f"{agentshield_metrics['recall']:.3%}"
    )

    print(
        f"- F1 score: "
        f"{agentshield_metrics['f1']:.3f}"
    )

    print(
        f"- Legitimate-user friction rate: "
        f"{friction_rate:.3%}"
    )

    print(
        f"- False hard-block rate: "
        f"{false_block_rate:.3%}"
    )

    print(
        "\nThese results are measured on a synthetic "
        "controlled benchmark and should not be interpreted "
        "as production Razorpay performance."
    )


if __name__ == "__main__":
    main()