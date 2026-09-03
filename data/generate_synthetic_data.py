"""
AgentShield — Synthetic Transaction Generator v2

Generates synthetic agent-initiated payment transactions with
ground-truth labels across 5 scenarios:

0 = legitimate
1 = budget_abuse
2 = category_abuse
3 = velocity_abuse
4 = behavioral_anomaly

Important design choices:
- Authorization is separate from historical behaviour.
- Legitimate transactions can occur in multiple authorized categories.
- Legitimate transaction velocity varies naturally.
- Velocity abuse is abnormal relative to a user's normal velocity.
- Behavioral anomalies remain within authorization limits.
- Ground-truth labels are NOT used as model features.
- Synthetic data only.
- Reproducible using a fixed random seed.

Output:
    data/raw/synthetic_transactions_v2.csv

Usage:
    python data/generate_synthetic_data.py

    python data/generate_synthetic_data.py --n_users 500 --n_transactions 10000
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta

import pandas as pd


# ============================================================
# REPRODUCIBILITY
# ============================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)


# ============================================================
# CONSTANTS
# ============================================================

CATEGORIES = [
    "grocery",
    "food_delivery",
    "electronics",
    "gift_cards",
    "travel",
    "fuel",
    "utilities",
    "entertainment",
    "fashion",
    "pharmacy",
]

MERCHANT_PREFIXES = [
    "Bharat",
    "Nova",
    "Urban",
    "Swift",
    "Prime",
    "Metro",
    "Trust",
    "Aster",
    "Kavya",
    "Zenith",
    "Nimbus",
    "Orion",
    "Vega",
    "Sapphire",
    "Coral",
]

MERCHANT_SUFFIXES = [
    "Mart",
    "Stores",
    "Traders",
    "Retail",
    "Hub",
    "Bazaar",
    "Express",
    "Ventures",
    "Solutions",
    "Enterprises",
]


# ============================================================
# MERCHANT GENERATION
# ============================================================

def fake_company():
    """Generate a synthetic merchant name."""
    return (
        f"{random.choice(MERCHANT_PREFIXES)} "
        f"{random.choice(MERCHANT_SUFFIXES)}"
    )


# ============================================================
# USER PROFILE
# ============================================================

def make_user_profile(user_id):
    """
    Create a synthetic user/agent authorization profile.

    Authorization and historical behaviour are intentionally
    represented separately.
    """

    # --------------------------------------------------------
    # Authorization
    # --------------------------------------------------------

    authorized_limit = random.choice([
        2000,
        5000,
        10000,
        15000,
    ])

    daily_limit = authorized_limit * random.choice([
        1.5,
        2.0,
        3.0,
    ])

    # User is authorized for 2–4 categories.
    allowed_categories = random.sample(
        CATEGORIES,
        random.randint(2, 4)
    )

    # --------------------------------------------------------
    # Historical behaviour
    # --------------------------------------------------------

    usual_category = random.choice(allowed_categories)

    avg_order_value = round(
        random.uniform(
            150,
            min(
                2500,
                authorized_limit * 0.40
            )
        ),
        2
    )

    normal_velocity = random.randint(1, 3)

    # A small set of merchants that the user has historically
    # interacted with.
    usual_merchants = [
        fake_company()
        for _ in range(random.randint(2, 5))
    ]

    return {
        "user_id": user_id,

        # Agentic identity
        "agent_id": f"AG-{random.randint(10000, 99999)}",
        "authorization_id": f"AUTH-{random.randint(10000, 99999)}",

        # Authorization
        "authorized_limit": authorized_limit,
        "daily_limit": round(daily_limit, 2),
        "allowed_categories": "|".join(allowed_categories),

        # Historical behaviour
        "usual_category": usual_category,
        "usual_merchants": "|".join(usual_merchants),
        "avg_order_value": avg_order_value,
        "normal_velocity": normal_velocity,

        # Account context
        "account_age_days": random.randint(30, 900),
    }


# ============================================================
# BASE TRANSACTION
# ============================================================

def base_transaction(user, timestamp):
    """
    Fields shared by every transaction.
    """

    return {
        "transaction_id": str(uuid.uuid4())[:8],

        "user_id": user["user_id"],

        # Agent identity
        "agent_id": user["agent_id"],
        "authorization_id": user["authorization_id"],

        # Time
        "timestamp": timestamp.isoformat(),

        # Authorization
        "authorized_limit": user["authorized_limit"],
        "daily_limit": user["daily_limit"],
        "allowed_categories": user["allowed_categories"],

        # Historical behaviour
        "usual_category": user["usual_category"],
        "avg_order_value": user["avg_order_value"],
        "normal_velocity": user["normal_velocity"],
        "account_age_days": user["account_age_days"],
    }


# ============================================================
# SCENARIO 0 — LEGITIMATE
# ============================================================

def gen_legitimate(user, timestamp):
    """
    Normal transaction.

    Important:
    A legitimate transaction can belong to ANY category that
    the user is authorized to use.

    It does not have to equal the user's usual category.
    """

    txn = base_transaction(user, timestamp)

    allowed_categories = user["allowed_categories"].split("|")

    # Sometimes use usual category, sometimes another
    # authorized category.
    if random.random() < 0.70:
        category = user["usual_category"]
    else:
        category = random.choice(allowed_categories)

    # Normal transaction amount.
    amount = user["avg_order_value"] * random.uniform(
        0.6,
        1.5
    )

    amount = min(
        amount,
        user["authorized_limit"] * 0.80
    )

    amount = max(amount, 50)

    # Legitimate velocity varies.
    velocity = max(
        1,
        int(
            random.gauss(
                user["normal_velocity"],
                0.8
            )
        )
    )

    # Pick a historical merchant sometimes.
    if random.random() < 0.75:
        merchant = random.choice(
            user["usual_merchants"].split("|")
        )
    else:
        merchant = fake_company()

    txn.update({
        "amount": round(amount, 2),

        "merchant_category": category,

        "merchant_name": merchant,

        "txns_in_last_10min": velocity,

        "merchant_seen_before": (
            merchant in user["usual_merchants"].split("|")
        ),

        "label": 0,

        "scenario": "legitimate",
    })

    return txn


# ============================================================
# SCENARIO 1 — BUDGET ABUSE
# ============================================================

def gen_budget_abuse(user, timestamp):
    """
    Transaction exceeds the explicit authorization limit.

    Other behaviour remains relatively normal.

    This should primarily be caught by deterministic
    authorization rules.
    """

    txn = base_transaction(user, timestamp)

    amount = user["authorized_limit"] * random.uniform(
        1.10,
        2.20
    )

    merchant = random.choice(
        user["usual_merchants"].split("|")
    )

    txn.update({
        "amount": round(amount, 2),

        "merchant_category": user["usual_category"],

        "merchant_name": merchant,

        "txns_in_last_10min": max(
            1,
            user["normal_velocity"]
        ),

        "merchant_seen_before": True,

        "label": 1,

        "scenario": "budget_abuse",
    })

    return txn


# ============================================================
# SCENARIO 2 — CATEGORY ABUSE
# ============================================================

def gen_category_abuse(user, timestamp):
    """
    Transaction is within the spending limit but uses a
    category that is NOT authorized.

    The amount itself should look reasonable.
    """

    txn = base_transaction(user, timestamp)

    unauthorized_categories = [
        category
        for category in CATEGORIES
        if category not in user["allowed_categories"].split("|")
    ]

    category = random.choice(
        unauthorized_categories
    )

    amount = user["avg_order_value"] * random.uniform(
        0.8,
        1.8
    )

    amount = min(
        amount,
        user["authorized_limit"] * 0.90
    )

    amount = max(amount, 50)

    merchant = fake_company()

    txn.update({
        "amount": round(amount, 2),

        "merchant_category": category,

        "merchant_name": merchant,

        "txns_in_last_10min": max(
            1,
            user["normal_velocity"]
        ),

        "merchant_seen_before": False,

        "label": 1,

        "scenario": "category_abuse",
    })

    return txn


# ============================================================
# SCENARIO 3 — VELOCITY ABUSE
# ============================================================

def gen_velocity_abuse(user, timestamp):
    """
    Generate a burst of individually reasonable transactions.

    The key difference from v1:

    Legitimate users can naturally have velocity > 1.

    Velocity abuse is instead several times higher than the
    user's normal velocity.
    """

    burst_size = random.randint(
        max(5, user["normal_velocity"] * 3),
        max(8, user["normal_velocity"] * 6)
    )

    transactions = []

    amount = user["avg_order_value"] * random.uniform(
        0.3,
        0.8
    )

    amount = min(
        amount,
        user["authorized_limit"] * 0.20
    )

    amount = max(amount, 30)

    for _ in range(burst_size):

        burst_time = timestamp + timedelta(
            seconds=random.randint(0, 590)
        )

        txn = base_transaction(
            user,
            burst_time
        )

        merchant = random.choice(
            user["usual_merchants"].split("|")
        )

        txn.update({
            "amount": round(amount, 2),

            "merchant_category": user["usual_category"],

            "merchant_name": merchant,

            "txns_in_last_10min": burst_size,

            "merchant_seen_before": True,

            "label": 1,

            "scenario": "velocity_abuse",
        })

        transactions.append(txn)

    return transactions


# ============================================================
# SCENARIO 4 — BEHAVIOURAL ANOMALY
# ============================================================

def gen_behavioral_anomaly(user, timestamp):
    """
    Transaction is authorized but behaviourally unusual.

    Characteristics:
    - within spending limit
    - authorized category
    - unusually large relative to history
    - new merchant
    - normal velocity

    This is the key scenario for AgentShield's behavioural
    intelligence.
    """

    txn = base_transaction(
        user,
        timestamp
    )

    allowed_categories = user["allowed_categories"].split("|")

    # Keep category authorized.
    category = random.choice(
        allowed_categories
    )

    # Create significant deviation from historical amount.
    amount = user["avg_order_value"] * random.uniform(
        2.5,
        5.0
    )

    # Must remain below authorization limit.
    amount = min(
        amount,
        user["authorized_limit"] * random.uniform(
            0.60,
            0.90
        )
    )

    # Ensure amount is still meaningfully above history.
    amount = max(
        amount,
        user["avg_order_value"] * 2.5
    )

    amount = min(
        amount,
        user["authorized_limit"] * 0.95
    )

    merchant = fake_company()

    txn.update({
        "amount": round(amount, 2),

        "merchant_category": category,

        "merchant_name": merchant,

        "txns_in_last_10min": max(
            1,
            user["normal_velocity"]
        ),

        "merchant_seen_before": False,

        "label": 1,

        "scenario": "behavioral_anomaly",
    })

    return txn


# ============================================================
# SCENARIO WEIGHTS
# ============================================================

SCENARIO_TARGETS = {
    "legitimate": 8500,
    "budget_abuse": 400,
    "category_abuse": 400,
    "velocity_abuse": 350,
    "behavioral_anomaly": 350,
}


# ============================================================
# DATASET GENERATION
# ============================================================

def generate(
    n_users,
    n_transactions,
    start_date
):
    """
    Generate a controlled synthetic transaction dataset.

    Scenario counts are controlled at the final ROW level,
    including velocity-abuse transactions.
    """

    users = {}

    for i in range(n_users):
        user_id = f"U{100 + i}"

        users[user_id] = make_user_profile(
            user_id
        )

    user_list = list(users.values())

    rows = []

    current_timestamp = start_date

    # --------------------------------------------------------
    # Generate each scenario until its target row count
    # --------------------------------------------------------

    for scenario, target_count in SCENARIO_TARGETS.items():

        scenario_rows = []

        while len(scenario_rows) < target_count:

            user = random.choice(user_list)

            current_timestamp += timedelta(
                minutes=random.randint(1, 30)
            )

            if scenario == "legitimate":

                txn = gen_legitimate(
                    user,
                    current_timestamp
                )

                scenario_rows.append(txn)

            elif scenario == "budget_abuse":

                txn = gen_budget_abuse(
                    user,
                    current_timestamp
                )

                scenario_rows.append(txn)

            elif scenario == "category_abuse":

                txn = gen_category_abuse(
                    user,
                    current_timestamp
                )

                scenario_rows.append(txn)

            elif scenario == "velocity_abuse":

                burst = gen_velocity_abuse(
                    user,
                    current_timestamp
                )

                # Add only the number of rows we still need.
                remaining = (
                    target_count
                    - len(scenario_rows)
                )

                scenario_rows.extend(
                    burst[:remaining]
                )

            elif scenario == "behavioral_anomaly":

                txn = gen_behavioral_anomaly(
                    user,
                    current_timestamp
                )

                scenario_rows.append(txn)

        rows.extend(
            scenario_rows[:target_count]
        )

    # --------------------------------------------------------
    # Create dataframe
    # --------------------------------------------------------

    df = pd.DataFrame(rows)

    # Shuffle rows so scenarios are not grouped together.
    df = (
        df.sample(
            frac=1,
            random_state=RANDOM_SEED
        )
        .reset_index(drop=True)
    )

    return df


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Generate AgentShield synthetic "
            "transaction data v2."
        )
    )

    parser.add_argument(
        "--n_users",
        type=int,
        default=500,
        help="Number of synthetic users."
    )

    parser.add_argument(
        "--n_transactions",
        type=int,
        default=10000,
        help="Number of transactions."
    )

    parser.add_argument(
        "--out",
        type=str,
        default=(
    "data/raw/"
    "synthetic_transactions_v3.csv"
),
    )

    args = parser.parse_args()

    df = generate(
        n_users=args.n_users,
        n_transactions=args.n_transactions,
        start_date=datetime(2026, 8, 1)
    )

    df.to_csv(
        args.out,
        index=False
    )

    print("=" * 60)
    print("AgentShield Synthetic Data Generator v3")
    print("=" * 60)

    print(
        f"\nGenerated: {len(df):,} transactions"
    )

    print(
        f"Saved to: {args.out}"
    )

    print("\nScenario distribution:")

    print(
        df["scenario"]
        .value_counts()
        .to_string()
    )

    print("\nLabel distribution:")

    print(
        df["label"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        f"\nOverall abuse rate: "
        f"{(df['label'] == 1).mean():.1%}"
    )

    print("\nDataset shape:")

    print(df.shape)

    print("\nColumns:")

    print(
        ", ".join(df.columns)
    )

    print("\nFirst 5 rows:")

    print(
        df.head()
        .to_string(index=False)
    )

    print("\nGeneration complete.")