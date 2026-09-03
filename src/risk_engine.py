"""
AgentShield — Behavioral Risk Engine

The ML model focuses only on behavioral risk.

Explicit authorization violations are handled separately
by the policy layer.
"""

import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from src.feature_engineering import (
    add_features,
    MODEL_FEATURES,
)


DATA_PATH = "data/raw/synthetic_transactions_v3.csv"


def train_behavioral_model():
    """
    Train a Logistic Regression model using only behavioral features.

    Users in the test set are completely unseen during training.
    """

    df = pd.read_csv(DATA_PATH)
    df = add_features(df)

    # --------------------------------------------------------
    # Train behavioral ML only on:
    # - legitimate
    # - velocity abuse
    # - behavioral anomaly
    #
    # Budget/category abuse are handled by policy rules.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Group-based split
    #
    # A user can exist either in train OR test — never both.
    # --------------------------------------------------------

    group_split = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_idx, test_idx = next(
        group_split.split(
            X,
            y,
            groups=groups,
        )
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    train_users = set(groups.iloc[train_idx])
    test_users = set(groups.iloc[test_idx])

    # --------------------------------------------------------
    # Scaling
    # --------------------------------------------------------

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # --------------------------------------------------------
    # Logistic Regression
    # --------------------------------------------------------

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )

    model.fit(
        X_train_scaled,
        y_train,
    )

    # --------------------------------------------------------
    # Predictions
    # --------------------------------------------------------

    predictions = model.predict(
        X_test_scaled
    )

    probabilities = model.predict_proba(
        X_test_scaled
    )[:, 1]

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    print("=" * 60)
    print("AgentShield — Behavioral Risk Model")
    print("=" * 60)

    print(f"\nTrain users : {len(train_users)}")
    print(f"Test users  : {len(test_users)}")

    print(
        "User overlap: "
        f"{len(train_users.intersection(test_users))}"
    )

    print(f"\nTraining rows: {len(X_train):,}")
    print(f"Test rows    : {len(X_test):,}")

    print("\n=== CONFUSION MATRIX ===")

    print(
        confusion_matrix(
            y_test,
            predictions,
        )
    )

    print("\n=== METRICS ===")

    print(
        f"Precision : "
        f"{precision_score(y_test, predictions):.3f}"
    )

    print(
        f"Recall    : "
        f"{recall_score(y_test, predictions):.3f}"
    )

    print(
        f"F1 Score  : "
        f"{f1_score(y_test, predictions):.3f}"
    )

    print("\n=== CLASSIFICATION REPORT ===")

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "Legitimate",
                "Behavioral Abuse",
            ],
        )
    )

    # --------------------------------------------------------
    # Feature coefficients
    # --------------------------------------------------------

    coefficients = pd.DataFrame(
        {
            "feature": MODEL_FEATURES,
            "coefficient": model.coef_[0],
        }
    )

    coefficients["abs_coefficient"] = (
        coefficients["coefficient"].abs()
    )

    coefficients = coefficients.sort_values(
        "abs_coefficient",
        ascending=False,
    )

    print("\n=== FEATURE IMPORTANCE ===")

    print(
        coefficients[
            ["feature", "coefficient"]
        ].to_string(index=False)
    )

    return model, scaler
def predict_risk(transaction, model, scaler):
    """
    Compute behavioral risk probability for one transaction.
    """

    transaction_df = pd.DataFrame([transaction])

    transaction_df = add_features(transaction_df)

    X = transaction_df[MODEL_FEATURES]

    X_scaled = scaler.transform(X)

    risk_score = model.predict_proba(
        X_scaled
    )[0, 1]

    return float(risk_score)

if __name__ == "__main__":
    train_behavioral_model()