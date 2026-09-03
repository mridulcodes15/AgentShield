"""
AgentShield — Threshold Analysis

Finds defensible risk thresholds for:
ALLOW / STEP-UP / BLOCK

Uses a user-group split so test users are unseen.
"""

import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score

from src.feature_engineering import add_features, MODEL_FEATURES


DATA_PATH = "data/raw/synthetic_transactions_v3.csv"


def main():
    df = pd.read_csv(DATA_PATH)
    df = add_features(df)

    behavioral_df = df[
        df["scenario"].isin(
            [
                "legitimate",
                "velocity_abuse",
                "behavioral_anomaly",
            ]
        )
    ].copy()

    X = behavioral_df[MODEL_FEATURES]
    y = behavioral_df["label"]
    groups = behavioral_df["user_id"]

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(X, y, groups=groups)
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )

    model.fit(
        X_train_scaled,
        y_train,
    )

    probabilities = model.predict_proba(
        X_test_scaled
    )[:, 1]

    print("=" * 70)
    print("AgentShield — Behavioral Risk Threshold Analysis")
    print("=" * 70)

    print(
        "\nThreshold | Precision | Recall | F1 | FP | FN"
    )

    print("-" * 70)

    for threshold in [
        0.10,
        0.20,
        0.30,
        0.40,
        0.50,
        0.60,
        0.70,
        0.80,
        0.90,
    ]:

        predictions = (
            probabilities >= threshold
        ).astype(int)

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

        false_positives = (
            (predictions == 1)
            & (y_test.to_numpy() == 0)
        ).sum()

        false_negatives = (
            (predictions == 0)
            & (y_test.to_numpy() == 1)
        ).sum()

        print(
            f"{threshold:>9.2f} | "
            f"{precision:>9.3f} | "
            f"{recall:>6.3f} | "
            f"{f1:>4.3f} | "
            f"{false_positives:>2} | "
            f"{false_negatives:>2}"
        )


if __name__ == "__main__":
    main()