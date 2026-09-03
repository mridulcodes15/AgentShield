"""
AgentShield — End-to-End Integration Tests

Tests:

1. ALLOW
2. STEP_UP — behavioral risk
3. STEP_UP — authorization exceeded / re-authorization
4. BLOCK
5. CLARIFICATION_REQUIRED
"""

from src.risk_engine import train_behavioral_model
from src.decision_engine import (
    evaluate_agent_action,
    print_result,
)


def run_test(
    name,
    instruction,
    transaction,
    profile,
    model,
    scaler,
):
    print("\n\n")
    print("#" * 70)
    print(f"TEST: {name}")
    print("#" * 70)

    result = evaluate_agent_action(
        instruction=instruction,
        proposed_transaction=transaction,
        user_profile=profile,
        model=model,
        scaler=scaler,
    )

    print_result(result)

    return result


if __name__ == "__main__":

    # --------------------------------------------------------
    # Train behavioral model once
    # --------------------------------------------------------

    model, scaler = train_behavioral_model()

    # --------------------------------------------------------
    # Shared historical user profile
    # --------------------------------------------------------

    profile = {
        "avg_order_value": 450.0,
        "normal_velocity": 2,
        "usual_category": "groceries",
    }

    # ========================================================
    # TEST 1 — NORMAL TRANSACTION
    #
    # Expected:
    # ALLOW
    # Razorpay order CREATED
    # ========================================================

    run_test(
        name="NORMAL / ALLOW",
        instruction=(
            "Buy groceries but do not spend "
            "more than ₹2,000."
        ),
        transaction={
            "merchant_name": "DailyMart",
            "merchant_category": "groceries",
            "amount": 500.0,
            "txns_in_last_10min": 1,
            "merchant_seen_before": 1,
        },
        profile=profile,
        model=model,
        scaler=scaler,
    )

    # ========================================================
    # TEST 2 — VELOCITY ANOMALY
    #
    # This scenario was found using the trained model.
    #
    # Expected:
    # Risk ≈ 0.817
    # STEP_UP
    # Source: BEHAVIORAL_RISK
    # Razorpay order NOT created
    # ========================================================

    run_test(
        name="VELOCITY ANOMALY / STEP_UP",
        instruction=(
            "Buy groceries but do not spend "
            "more than ₹2,000."
        ),
        transaction={
            "merchant_name": "DailyMart",
            "merchant_category": "groceries",
            "amount": 500.0,
            "txns_in_last_10min": 5,
            "merchant_seen_before": 1,
        },
        profile=profile,
        model=model,
        scaler=scaler,
    )

    # ========================================================
    # TEST 3 — AUTHORIZATION EXCEEDED
    #
    # The user originally approved up to ₹2,000.
    # The final grocery bill becomes ₹2,500.
    #
    # This is NOT automatically fraud.
    #
    # Expected:
    # STEP_UP
    # Source: AUTHORIZATION
    # Fresh user authorization required
    # Razorpay order NOT created
    # ========================================================

    reauthorization_profile = {
        "avg_order_value": 2200.0,
        "normal_velocity": 2,
        "usual_category": "groceries",
    }

    run_test(
        name="AUTHORIZATION EXCEEDED / RE-AUTHORIZE",
        instruction=(
            "Buy groceries but do not spend "
            "more than ₹2,000."
        ),
        transaction={
            "merchant_name": "DailyMart",
            "merchant_category": "groceries",
            "amount": 2500.0,
            "txns_in_last_10min": 1,
            "merchant_seen_before": 1,
        },
        profile=reauthorization_profile,
        model=model,
        scaler=scaler,
    )

    # ========================================================
    # TEST 4 — STRONG BEHAVIORAL ANOMALY
    #
    # Expected:
    # BLOCK
    # Source: BEHAVIORAL_RISK
    # Razorpay order NOT created
    # ========================================================

    run_test(
        name="BEHAVIORAL ANOMALY / BLOCK",
        instruction=(
            "Buy groceries but do not spend "
            "more than ₹2,000."
        ),
        transaction={
            "merchant_name": "FreshMart",
            "merchant_category": "groceries",
            "amount": 1850.0,
            "txns_in_last_10min": 2,
            "merchant_seen_before": 0,
        },
        profile=profile,
        model=model,
        scaler=scaler,
    )

    # ========================================================
    # TEST 5 — INCOMPLETE AUTHORIZATION
    #
    # No spending limit was supplied by the user.
    #
    # Expected:
    # CLARIFICATION_REQUIRED
    # Risk evaluation stopped
    # Razorpay execution stopped
    # ========================================================

    run_test(
        name="INCOMPLETE AUTHORIZATION",
        instruction="Buy some groceries for me.",
        transaction={
            "merchant_name": "DailyMart",
            "merchant_category": "groceries",
            "amount": 500.0,
            "txns_in_last_10min": 1,
            "merchant_seen_before": 1,
        },
        profile=profile,
        model=model,
        scaler=scaler,
    )