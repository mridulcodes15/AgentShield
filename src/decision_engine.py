"""
AgentShield — End-to-End Decision Engine

Operating modes:

1. COLD_START
   New user with insufficient confirmed transaction history.
   Explicit authorization is enforced, but behavioral ML is not used.

2. BEHAVIORAL_MODEL
   Established user with sufficient confirmed transaction history.
   Explicit authorization + behavioral ML are both evaluated.

Core principle:
Authorization and behavioral risk are separate concepts.

History principle:
When a user_id is supplied, AgentShield automatically loads the user's
persistent profile from SQLite and stores only transactions that were
allowed and successfully created as Razorpay test orders.
"""

from src.intent_parser import parse_intent
from src.risk_engine import train_behavioral_model, predict_risk
from src.policy_engine import make_decision, check_authorization
from src.explainer import generate_explanation
from src.razorpay_client import execute_if_allowed
from src.history_store import (
    build_user_profile,
    has_seen_merchant,
    save_transaction,
    get_transaction_count,
    clear_user_history,
)


# ============================================================
# HISTORY HELPERS
# ============================================================

def resolve_user_profile(user_id=None, user_profile=None):
    """
    Resolve the behavioral profile used for evaluation.

    Preferred path:
        user_id -> persistent SQLite history -> automatic profile.

    Backward-compatible path:
        user_profile -> caller-supplied profile.
    """

    if user_id is not None:
        return build_user_profile(user_id)

    if user_profile is None:
        raise ValueError(
            "Provide either user_id for automatic history or "
            "user_profile for the legacy/manual evaluation path."
        )

    return user_profile.copy()


def persist_confirmed_transaction(transaction, razorpay_result):
    """
    Persist a transaction only when:

    1. a persistent user_id exists, and
    2. Razorpay successfully created a test order.

    STEP_UP, BLOCK, clarification and cancelled transactions
    are not added to behavioral history.
    """

    user_id = transaction.get("user_id")

    if user_id is None:
        return {
            "saved": False,
            "reason": "No persistent user_id was supplied.",
        }

    if not razorpay_result.get("executed", False):
        return {
            "saved": False,
            "reason": "Transaction was not executed.",
        }

    row_id = save_transaction(
        user_id=user_id,
        amount=transaction["amount"],
        merchant_name=transaction["merchant_name"],
        merchant_category=transaction["merchant_category"],
    )

    updated_profile = build_user_profile(user_id)

    return {
        "saved": True,
        "row_id": row_id,
        "transaction_count": updated_profile["transaction_count"],
        "profile_after_transaction": updated_profile,
    }


# ============================================================
# COLD-START DECISION
# ============================================================

def make_cold_start_decision(transaction):
    """
    Decide an agent action when reliable behavioral history
    does not yet exist.

    Authorization violation -> STEP_UP
    Authorization passes    -> ALLOW

    No behavioral risk score is fabricated.
    """

    authorization_passed, reasons = check_authorization(transaction)

    if not authorization_passed:
        return {
            "decision": "STEP_UP",
            "decision_source": "AUTHORIZATION",
            "risk_score": None,
            "risk_mode": "COLD_START",
            "reasons": reasons,
            "requires_reauthorization": True,
        }

    return {
        "decision": "ALLOW",
        "decision_source": "AUTHORIZATION",
        "risk_score": None,
        "risk_mode": "COLD_START",
        "reasons": [
            (
                "Explicit authorization passed. Behavioral scoring was "
                "not performed because the user does not yet have "
                "sufficient confirmed transaction history."
            )
        ],
        "requires_reauthorization": False,
    }


# ============================================================
# COLD-START EXPLANATION
# ============================================================

def generate_cold_start_explanation(transaction, decision):
    """Explain a cold-start decision without fabricating risk."""

    if decision["decision"] == "STEP_UP":
        summary = (
            "Fresh user authorization is required because the proposed "
            "action exceeds the agent's current permission. No behavioral "
            "risk score was produced because this user does not yet have "
            "sufficient confirmed transaction history."
        )
    else:
        summary = (
            "The proposed action is within the user's explicit authorization. "
            "Because this user does not yet have sufficient confirmed "
            "transaction history, AgentShield used cold-start authorization "
            "mode instead of inventing a behavioral baseline."
        )

    return {
        "decision": decision["decision"],
        "risk_score": None,
        "risk_mode": "COLD_START",
        "summary": summary,
        "evidence": list(decision.get("reasons", [])),
    }


# ============================================================
# MAIN EVALUATION
# ============================================================

def evaluate_agent_action(
    instruction,
    proposed_transaction,
    user_profile=None,
    model=None,
    scaler=None,
    user_id=None,
):
    """
    Evaluate one financial action proposed by an AI agent.

    Preferred usage:
        evaluate_agent_action(..., user_id="user_001")

    AgentShield automatically:
    - parses authorization,
    - loads persistent history,
    - determines cold-start vs behavioral mode,
    - derives merchant familiarity,
    - evaluates behavioral risk when history exists,
    - gates Razorpay execution,
    - persists successfully executed test-order events.
    """

    if model is None or scaler is None:
        raise ValueError(
            "model and scaler are required for evaluation."
        )

    # --------------------------------------------------------
    # 1. Parse explicit authorization
    # --------------------------------------------------------

    intent = parse_intent(instruction)

    if intent["requires_clarification"]:
        return {
            "status": "CLARIFICATION_REQUIRED",
            "intent": intent,
            "user_id": (
                str(user_id)
                if user_id is not None
                else None
            ),
            "message": (
                "The user's authorization is incomplete. "
                "Payment evaluation has been stopped."
            ),
        }

    # --------------------------------------------------------
    # 2. Load persistent profile
    # --------------------------------------------------------

    resolved_profile = resolve_user_profile(
        user_id=user_id,
        user_profile=user_profile,
    )

    has_history = resolved_profile.get(
        "has_history",
        True,
    )

    # --------------------------------------------------------
    # 3. Merchant familiarity
    # --------------------------------------------------------

    if user_id is not None:
        merchant_seen_before = int(
            has_seen_merchant(
                user_id,
                proposed_transaction["merchant_name"],
            )
        )
    else:
        merchant_seen_before = int(
            proposed_transaction.get(
                "merchant_seen_before",
                0,
            )
        )

    # --------------------------------------------------------
    # 4. Build transaction
    # --------------------------------------------------------

    transaction = {
        "user_id": (
            str(user_id)
            if user_id is not None
            else None
        ),
        "amount": float(
            proposed_transaction["amount"]
        ),
        "merchant_category":
            proposed_transaction["merchant_category"],
        "merchant_name":
            proposed_transaction["merchant_name"],
        "authorized_limit":
            intent["authorized_limit"],
        "allowed_categories":
            intent["allowed_categories"],
        "txns_in_last_10min":
            proposed_transaction.get(
                "txns_in_last_10min",
                1,
            ),
        "merchant_seen_before":
            merchant_seen_before,
        "has_history":
            bool(has_history),
        "history_transaction_count":
            resolved_profile.get(
                "transaction_count"
            ),
    }

    # ========================================================
    # COLD START
    # ========================================================

    if not has_history:

        transaction["avg_order_value"] = None
        transaction["normal_velocity"] = None
        transaction["usual_category"] = None

        decision = make_cold_start_decision(
            transaction
        )

        explanation = (
            generate_cold_start_explanation(
                transaction,
                decision,
            )
        )

        razorpay_result = execute_if_allowed(
            transaction,
            decision,
        )

        history_result = (
            persist_confirmed_transaction(
                transaction,
                razorpay_result,
            )
        )

        return {
            "status": "EVALUATED",
            "intent": intent,
            "user_id": transaction["user_id"],
            "profile_before_transaction":
                resolved_profile,
            "transaction": transaction,
            "decision": decision,
            "explanation": explanation,
            "razorpay": razorpay_result,
            "history": history_result,
            "risk_mode": "COLD_START",
        }

    # ========================================================
    # ESTABLISHED USER
    # ========================================================

    required_history_fields = [
        "avg_order_value",
        "normal_velocity",
        "usual_category",
    ]

    missing_fields = [
        field
        for field in required_history_fields
        if resolved_profile.get(field) is None
    ]

    if missing_fields:
        raise ValueError(
            "Behavioral history was marked as available, but "
            "the following profile fields are missing: "
            + ", ".join(missing_fields)
        )

    transaction["avg_order_value"] = (
        resolved_profile["avg_order_value"]
    )

    transaction["normal_velocity"] = (
        resolved_profile["normal_velocity"]
    )

    transaction["usual_category"] = (
        resolved_profile["usual_category"]
    )

    # --------------------------------------------------------
    # Behavioral ML
    # --------------------------------------------------------

    risk_score = predict_risk(
        transaction,
        model,
        scaler,
    )

    # --------------------------------------------------------
    # Authorization + behavioral policy
    # --------------------------------------------------------

    decision = make_decision(
        transaction,
        risk_score,
    )

    decision["risk_mode"] = (
        "BEHAVIORAL_MODEL"
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    explanation = generate_explanation(
        transaction,
        decision,
    )

    explanation["risk_mode"] = (
        "BEHAVIORAL_MODEL"
    )

    # --------------------------------------------------------
    # Razorpay gate
    # --------------------------------------------------------

    razorpay_result = execute_if_allowed(
        transaction,
        decision,
    )

    history_result = (
        persist_confirmed_transaction(
            transaction,
            razorpay_result,
        )
    )

    return {
        "status": "EVALUATED",
        "intent": intent,
        "user_id": transaction["user_id"],
        "profile_before_transaction":
            resolved_profile,
        "transaction": transaction,
        "decision": decision,
        "explanation": explanation,
        "razorpay": razorpay_result,
        "history": history_result,
        "risk_mode": "BEHAVIORAL_MODEL",
    }


# ============================================================
# RE-AUTHORIZATION
# ============================================================

def reevaluate_after_reauthorization(
    transaction,
    revised_limit,
    model,
    scaler,
):
    """
    Re-evaluate after the user explicitly approves a revised
    spending limit.

    Re-authorization changes permission only.
    It does NOT bypass behavioral risk.
    """

    updated_transaction = (
        transaction.copy()
    )

    updated_transaction[
        "authorized_limit"
    ] = float(revised_limit)

    has_history = updated_transaction.get(
        "has_history",
        True,
    )

    # --------------------------------------------------------
    # COLD START
    # --------------------------------------------------------

    if not has_history:

        decision = make_cold_start_decision(
            updated_transaction
        )

        explanation = (
            generate_cold_start_explanation(
                updated_transaction,
                decision,
            )
        )

        razorpay_result = execute_if_allowed(
            updated_transaction,
            decision,
        )

        history_result = (
            persist_confirmed_transaction(
                updated_transaction,
                razorpay_result,
            )
        )

        return {
            "status": "EVALUATED",
            "transaction":
                updated_transaction,
            "decision":
                decision,
            "explanation":
                explanation,
            "razorpay":
                razorpay_result,
            "history":
                history_result,
            "reauthorized":
                True,
            "risk_mode":
                "COLD_START",
        }

    # --------------------------------------------------------
    # ESTABLISHED USER
    # --------------------------------------------------------

    risk_score = predict_risk(
        updated_transaction,
        model,
        scaler,
    )

    decision = make_decision(
        updated_transaction,
        risk_score,
    )

    decision["risk_mode"] = (
        "BEHAVIORAL_MODEL"
    )

    explanation = generate_explanation(
        updated_transaction,
        decision,
    )

    explanation["risk_mode"] = (
        "BEHAVIORAL_MODEL"
    )

    razorpay_result = execute_if_allowed(
        updated_transaction,
        decision,
    )

    history_result = (
        persist_confirmed_transaction(
            updated_transaction,
            razorpay_result,
        )
    )

    return {
        "status": "EVALUATED",
        "transaction":
            updated_transaction,
        "decision":
            decision,
        "explanation":
            explanation,
        "razorpay":
            razorpay_result,
        "history":
            history_result,
        "reauthorized":
            True,
        "risk_mode":
            "BEHAVIORAL_MODEL",
    }


# ============================================================
# BEHAVIORAL STEP-UP CONFIRMATION
# ============================================================

def confirm_behavioral_step_up(
    transaction,
    original_decision,
):
    """
    Execute a transaction after the user explicitly confirms
    a BEHAVIORAL_RISK STEP_UP.

    This is intentionally different from re-authorization.

    AUTHORIZATION STEP_UP:
        Permission was insufficient.
        User expands permission.
        Behavioral risk is evaluated again.

    BEHAVIORAL STEP_UP:
        Permission already exists.
        AgentShield detected unusual behavior.
        The user confirms this exact transaction.

    Confirmation does not erase or lower the original risk
    score. It records explicit human confirmation of the
    already-evaluated anomaly.
    """

    if (
        original_decision.get("decision")
        != "STEP_UP"
    ):
        raise ValueError(
            "Behavioral confirmation is only "
            "valid for a STEP_UP decision."
        )

    if (
        original_decision.get(
            "decision_source"
        )
        != "BEHAVIORAL_RISK"
    ):
        raise ValueError(
            "Behavioral confirmation is only "
            "valid for BEHAVIORAL_RISK STEP_UP."
        )

    risk_score = original_decision.get(
        "risk_score"
    )

    # --------------------------------------------------------
    # Explicit confirmation authorizes this exact action
    # --------------------------------------------------------

    confirmed_decision = {
        "decision": "ALLOW",
        "decision_source":
            "USER_CONFIRMATION",
        "risk_score":
            risk_score,
        "risk_mode":
            "BEHAVIORAL_MODEL",
        "reasons": [
            (
                "The user explicitly confirmed "
                "the exact transaction after "
                "AgentShield displayed the "
                "behavioral warning."
            )
        ],
        "requires_reauthorization":
            False,
        "user_confirmed_behavioral_warning":
            True,
    }

    # --------------------------------------------------------
    # Razorpay test execution
    # --------------------------------------------------------

    razorpay_result = execute_if_allowed(
        transaction,
        confirmed_decision,
    )

    # --------------------------------------------------------
    # Persist only after successful order creation
    # --------------------------------------------------------

    history_result = (
        persist_confirmed_transaction(
            transaction,
            razorpay_result,
        )
    )

    explanation = {
        "decision":
            "ALLOW",
        "risk_score":
            risk_score,
        "risk_mode":
            "BEHAVIORAL_MODEL",
        "summary": (
            "AgentShield detected unusual behavioral "
            "activity and paused the transaction. "
            "The user explicitly confirmed the exact "
            "transaction, so it was released to the "
            "Razorpay test execution gate."
        ),
        "evidence": [
            (
                "Behavioral risk was evaluated "
                "before execution."
            ),
            (
                "The behavioral warning was "
                "presented to the user."
            ),
            (
                "The user explicitly confirmed "
                "this exact transaction."
            ),
        ],
    }

    return {
        "status":
            "EVALUATED",
        "user_id":
            transaction.get("user_id"),
        "transaction":
            transaction,
        "decision":
            confirmed_decision,
        "explanation":
            explanation,
        "razorpay":
            razorpay_result,
        "history":
            history_result,
        "behavioral_confirmation":
            True,
        "risk_mode":
            "BEHAVIORAL_MODEL",
    }


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def print_result(result):
    """Pretty-print one AgentShield evaluation."""

    print("\n" + "=" * 65)
    print(
        "AGENTSHIELD — AGENT PAYMENT EVALUATION"
    )
    print("=" * 65)

    if "intent" in result:
        print("\nParsed Authorization:")
        print(result["intent"])

    if (
        result["status"]
        == "CLARIFICATION_REQUIRED"
    ):
        print("\nDecision:")
        print("CLARIFICATION_REQUIRED")

        print("\nReason:")
        print(result["message"])

        print(
            "\nPayment execution: STOPPED"
        )
        return

    transaction = result["transaction"]
    decision = result["decision"]
    explanation = result["explanation"]
    razorpay_result = result["razorpay"]

    print("\nAgent-Proposed Transaction:")

    if transaction.get("user_id") is not None:
        print(
            f"User: {transaction['user_id']}"
        )

    print(
        f"Merchant: "
        f"{transaction['merchant_name']}"
    )

    print(
        f"Category: "
        f"{transaction['merchant_category']}"
    )

    print(
        f"Amount: "
        f"₹{transaction['amount']:.2f}"
    )

    risk_mode = result.get(
        "risk_mode",
        decision.get(
            "risk_mode",
            "BEHAVIORAL_MODEL",
        ),
    )

    print(
        f"\nRisk mode: {risk_mode}"
    )

    if risk_mode == "COLD_START":

        count = transaction.get(
            "history_transaction_count"
        )

        print("\nBehavioral Context:")
        print(
            "No sufficient historical behavioral "
            "profile available."
        )

        if count is not None:
            print(
                "Confirmed history before "
                f"transaction: {count}"
            )

        print(
            "Behavioral ML was not run."
        )

    else:

        print("\nBehavioral Context:")

        print(
            "Historical average: "
            f"₹{transaction['avg_order_value']:.2f}"
        )

        print(
            "Recent velocity: "
            f"{transaction['txns_in_last_10min']}"
        )

        print(
            "Normal velocity: "
            f"{transaction['normal_velocity']}"
        )

        print(
            "Merchant seen before: "
            f"{bool(transaction['merchant_seen_before'])}"
        )

        print(
            "Usual category: "
            f"{transaction['usual_category']}"
        )

    print("\nAgentShield Decision:")

    risk_score = decision.get(
        "risk_score"
    )

    if risk_score is None:
        print(
            "Risk score: N/A (cold start)"
        )
    else:
        print(
            f"Risk score: {risk_score:.3f}"
        )

    print(
        f"Decision: "
        f"{decision['decision']}"
    )

    print(
        f"Source: "
        f"{decision['decision_source']}"
    )

    print("\nExplanation:")
    print(
        explanation["summary"]
    )

    if explanation["evidence"]:

        print("\nEvidence:")

        for item in explanation["evidence"]:
            print(
                f"- {item}"
            )

    print("\nRazorpay Execution:")

    print(
        f"Status: "
        f"{razorpay_result['status']}"
    )

    if razorpay_result["executed"]:

        order = razorpay_result["order"]

        print(
            f"Order ID: "
            f"{order['order_id']}"
        )

        print(
            "Amount: "
            f"₹{order['amount_rupees']:.2f}"
        )

        print(
            f"Currency: "
            f"{order['currency']}"
        )

    else:

        print(
            razorpay_result["message"]
        )

    history_result = result.get(
        "history"
    )

    if history_result is not None:

        print("\nPersistent History:")

        if history_result.get("saved"):

            print(
                "Confirmed transaction saved: YES"
            )

            print(
                "Confirmed transaction count: "
                f"{history_result['transaction_count']}"
            )

            profile_after = (
                history_result.get(
                    "profile_after_transaction",
                    {},
                )
            )

            print(
                "Profile ready for behavioral ML: "
                f"{profile_after.get('has_history', False)}"
            )

        else:

            print(
                "Confirmed transaction saved: NO"
            )

            print(
                "Reason: "
                f"{history_result.get('reason', 'Unknown')}"
            )

    print("\n" + "=" * 65)


# ============================================================
# MANUAL DEMO
# ============================================================

if __name__ == "__main__":

    model, scaler = (
        train_behavioral_model()
    )

    demo_user = (
        "history_demo_user_001"
    )

    clear_user_history(
        demo_user
    )

    print("\n" + "#" * 65)
    print(
        "AUTOMATIC HISTORY INTEGRATION TEST"
    )
    print("#" * 65)

    seed_history = [
        (
            560,
            "DailyMart",
            "groceries",
        ),
        (
            900,
            "FreshMart",
            "groceries",
        ),
        (
            1200,
            "DailyMart",
            "groceries",
        ),
        (
            740,
            "FoodHub",
            "food",
        ),
    ]

    for (
        amount,
        merchant,
        category,
    ) in seed_history:

        save_transaction(
            user_id=demo_user,
            amount=amount,
            merchant_name=merchant,
            merchant_category=category,
        )

    print(
        "\nProfile before transaction #5:"
    )

    print(
        build_user_profile(
            demo_user
        )
    )

    instruction = (
        "Buy groceries but do not spend "
        "more than ₹2,000."
    )

    fifth_transaction = {
        "merchant_name":
            "DailyMart",
        "merchant_category":
            "groceries",
        "amount":
            1050.0,
        "txns_in_last_10min":
            1,
    }

    result_5 = evaluate_agent_action(
        instruction=instruction,
        proposed_transaction=
            fifth_transaction,
        user_id=demo_user,
        model=model,
        scaler=scaler,
    )

    print(
        "\n\nTRANSACTION #5 — "
        "SHOULD BE COLD_START"
    )

    print_result(
        result_5
    )

    print(
        "\nProfile after transaction #5:"
    )

    print(
        build_user_profile(
            demo_user
        )
    )

    sixth_transaction = {
        "merchant_name":
            "DailyMart",
        "merchant_category":
            "groceries",
        "amount":
            800.0,
        "txns_in_last_10min":
            1,
    }

    result_6 = evaluate_agent_action(
        instruction=instruction,
        proposed_transaction=
            sixth_transaction,
        user_id=demo_user,
        model=model,
        scaler=scaler,
    )

    print(
        "\n\nTRANSACTION #6 — "
        "SHOULD USE BEHAVIORAL_MODEL"
    )

    print_result(
        result_6
    )

    print(
        "\nFinal confirmed history count:"
    )

    print(
        get_transaction_count(
            demo_user
        )
    )