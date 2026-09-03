"""
AgentShield — Feature Engineering

Transforms raw synthetic transactions into model-ready behavioural
and authorization-related features.

Important:
- Ground-truth columns such as `label` and `scenario` are never used
  as model inputs.
- Raw IDs are not used as predictive features.
"""

import pandas as pd
import numpy as np


def _normalize_categories(value):
    """
    Accept both dataset-style categories:
        "groceries|food"

    and LLM-style categories:
        ["groceries", "food"]
    """

    if isinstance(value, list):
        return [
            str(category).strip()
            for category in value
            if str(category).strip()
        ]

    if isinstance(value, str):
        return [
            category.strip()
            for category in value.split("|")
            if category.strip()
        ]

    return []


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived AgentShield features.

    Returns a copy of the dataframe with engineered columns.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Amount-based features
    # --------------------------------------------------------

    df["amount_to_limit_ratio"] = (
        df["amount"] / df["authorized_limit"]
    )

    df["amount_to_history_ratio"] = (
        df["amount"] / df["avg_order_value"]
    )

    # Avoid divide-by-zero.
    df["velocity_ratio"] = (
        df["txns_in_last_10min"]
        / df["normal_velocity"].replace(0, np.nan)
    ).fillna(0)

    # --------------------------------------------------------
    # Authorization features
    # --------------------------------------------------------

    df["category_authorized"] = df.apply(
        lambda row: (
            row["merchant_category"]
            in _normalize_categories(
                row["allowed_categories"]
            )
        ),
        axis=1,
    ).astype(int)

    df["within_amount_limit"] = (
        df["amount"] <= df["authorized_limit"]
    ).astype(int)

    # --------------------------------------------------------
    # Historical-behaviour features
    # --------------------------------------------------------

    df["usual_category_match"] = (
        df["merchant_category"]
        == df["usual_category"]
    ).astype(int)

    df["merchant_seen_before"] = (
        df["merchant_seen_before"].astype(int)
    )

    # --------------------------------------------------------
    # Optional time-derived features
    # --------------------------------------------------------
    # Dataset rows contain timestamps, but a live transaction
    # does not require one because these fields are not part
    # of the behavioural model.
    # --------------------------------------------------------

    if "timestamp" in df.columns:

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

        df["hour_of_day"] = (
            df["timestamp"].dt.hour
        )

        df["day_of_week"] = (
            df["timestamp"].dt.dayofweek
        )

    return df


BEHAVIORAL_FEATURES = [
    "amount_to_history_ratio",
    "velocity_ratio",
    "usual_category_match",
    "merchant_seen_before",
]


POLICY_FEATURES = [
    "amount_to_limit_ratio",
    "category_authorized",
    "within_amount_limit",
]


MODEL_FEATURES = BEHAVIORAL_FEATURES


def get_model_matrix(df: pd.DataFrame):
    """
    Return behavioural-model features and labels.
    """

    enriched = add_features(df)

    X = enriched[MODEL_FEATURES].copy()
    y = enriched["label"].copy()

    return X, y