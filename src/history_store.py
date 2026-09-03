import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

DB_PATH = Path("data/processed/agentshield_history.db")

MIN_HISTORY_TRANSACTIONS = 5


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    """
    Open the local AgentShield SQLite database.
    """

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sqlite3.connect(DB_PATH)


def initialize_database():
    """
    Create the transaction-history table if it does not exist.
    """

    with get_connection() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                merchant_name TEXT NOT NULL,
                merchant_category TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )

        conn.commit()


# ============================================================
# SAVE CONFIRMED TRANSACTION
# ============================================================

def save_transaction(
    user_id,
    amount,
    merchant_name,
    merchant_category,
    timestamp=None,
):
    """
    Save a successfully confirmed/executed transaction.

    Only transactions that actually pass AgentShield and reach
    successful test-order creation should be stored here.
    """

    initialize_database()

    if timestamp is None:
        timestamp = datetime.now().isoformat()

    with get_connection() as conn:

        cursor = conn.execute(
            """
            INSERT INTO transaction_history (
                user_id,
                amount,
                merchant_name,
                merchant_category,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(user_id),
                float(amount),
                str(merchant_name),
                str(merchant_category),
                str(timestamp),
            ),
        )

        conn.commit()

        return cursor.lastrowid


# ============================================================
# READ USER HISTORY
# ============================================================

def get_user_history(user_id):
    """
    Return confirmed historical transactions for one user.
    """

    initialize_database()

    with get_connection() as conn:

        cursor = conn.execute(
            """
            SELECT
                id,
                user_id,
                amount,
                merchant_name,
                merchant_category,
                timestamp
            FROM transaction_history
            WHERE user_id = ?
            ORDER BY timestamp ASC
            """,
            (str(user_id),),
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "amount": row[2],
            "merchant_name": row[3],
            "merchant_category": row[4],
            "timestamp": row[5],
        }
        for row in rows
    ]


# ============================================================
# PROFILE BUILDER
# ============================================================

def build_user_profile(user_id):
    """
    Derive the behavioral profile from confirmed history.

    Cold-start users do not receive fabricated behavioral
    features.
    """

    history = get_user_history(user_id)

    transaction_count = len(history)

    if transaction_count < MIN_HISTORY_TRANSACTIONS:

        return {
            "user_id": str(user_id),
            "has_history": False,
            "transaction_count": transaction_count,
            "minimum_required": MIN_HISTORY_TRANSACTIONS,
        }

    amounts = [
        transaction["amount"]
        for transaction in history
    ]

    categories = [
        transaction["merchant_category"]
        for transaction in history
    ]

    avg_order_value = sum(amounts) / len(amounts)

    category_counts = Counter(categories)

    usual_category = category_counts.most_common(1)[0][0]

    # Prototype baseline.
    #
    # Once sufficient history exists, we use a conservative
    # default normal velocity of 2 transactions / 10 minutes.
    #
    # A production implementation would derive this from richer
    # timestamp/session history.
    normal_velocity = 2

    return {
        "user_id": str(user_id),
        "has_history": True,
        "transaction_count": transaction_count,
        "avg_order_value": float(avg_order_value),
        "normal_velocity": normal_velocity,
        "usual_category": usual_category,
    }


# ============================================================
# MERCHANT FAMILIARITY
# ============================================================

def has_seen_merchant(user_id, merchant_name):
    """
    Check whether this user has previously transacted with
    the proposed merchant.
    """

    history = get_user_history(user_id)

    target = str(merchant_name).strip().lower()

    return any(
        transaction["merchant_name"].strip().lower()
        == target
        for transaction in history
    )


# ============================================================
# UTILITY
# ============================================================

def get_transaction_count(user_id):
    """
    Return number of confirmed historical transactions.
    """

    return len(
        get_user_history(user_id)
    )


def clear_user_history(user_id):
    """
    Development/demo helper.

    Deletes one user's stored history so the cold-start flow
    can be demonstrated repeatedly.
    """

    initialize_database()

    with get_connection() as conn:

        conn.execute(
            """
            DELETE FROM transaction_history
            WHERE user_id = ?
            """,
            (str(user_id),),
        )

        conn.commit()


# ============================================================
# MANUAL TEST
# ============================================================

if __name__ == "__main__":

    test_user = "demo_user_001"

    clear_user_history(test_user)

    print("\nInitial profile:")
    print(build_user_profile(test_user))

    sample_transactions = [
        (560, "DailyMart", "groceries"),
        (900, "FreshMart", "groceries"),
        (1200, "DailyMart", "groceries"),
        (740, "FoodHub", "food"),
        (1050, "DailyMart", "groceries"),
    ]

    for amount, merchant, category in sample_transactions:

        save_transaction(
            user_id=test_user,
            amount=amount,
            merchant_name=merchant,
            merchant_category=category,
        )

        print(
            f"\nSaved ₹{amount} at {merchant}"
        )

        print(
            build_user_profile(test_user)
        )

    print("\nKnown merchant tests:")

    print(
        "DailyMart:",
        has_seen_merchant(
            test_user,
            "DailyMart",
        ),
    )

    print(
        "UnknownStore:",
        has_seen_merchant(
            test_user,
            "UnknownStore",
        ),
    )