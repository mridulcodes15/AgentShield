"""
AgentShield — Evidence-Based Explanation Engine

The explainer reports observable signals behind the decision.

Important:
- Exceeding authorization does not automatically mean fraud.
- Authorization violations require fresh user consent.
- Behavioral evidence is descriptive, not a claim of exact
  per-transaction model causality.
"""


def _normalize_categories(value):
    """
    Normalize allowed categories into a list.
    """

    if isinstance(value, list):
        return [
            str(item).strip().lower()
            for item in value
        ]

    if isinstance(value, str):
        return [
            item.strip().lower()
            for item in value.split("|")
            if item.strip()
        ]

    return []


def generate_explanation(
    transaction,
    decision_result,
):
    """
    Generate a human-readable explanation for one decision.
    """

    evidence = []

    decision = decision_result["decision"]
    source = decision_result["decision_source"]
    risk_score = decision_result["risk_score"]

    amount = float(transaction["amount"])
    authorized_limit = float(
        transaction["authorized_limit"]
    )

    avg_order_value = float(
        transaction["avg_order_value"]
    )

    normal_velocity = float(
        transaction["normal_velocity"]
    )

    current_velocity = float(
        transaction["txns_in_last_10min"]
    )

    merchant_category = str(
        transaction["merchant_category"]
    ).strip().lower()

    usual_category = str(
        transaction["usual_category"]
    ).strip().lower()

    allowed_categories = _normalize_categories(
        transaction["allowed_categories"]
    )

    merchant_seen_before = bool(
        transaction["merchant_seen_before"]
    )

    # --------------------------------------------------------
    # Authorization evidence
    # --------------------------------------------------------

    if amount > authorized_limit:

        excess = amount - authorized_limit

        evidence.append(
            f"The proposed amount is ₹{excess:.2f} above "
            f"the user's current authorized limit of "
            f"₹{authorized_limit:.2f}."
        )

    if merchant_category not in allowed_categories:

        evidence.append(
            f"The category '{merchant_category}' is outside "
            f"the categories currently authorized by the user."
        )

    # --------------------------------------------------------
    # Behavioral evidence
    # --------------------------------------------------------

    if avg_order_value > 0:

        amount_ratio = (
            amount / avg_order_value
        )

        if amount_ratio >= 2.0:

            evidence.append(
                f"Transaction amount is "
                f"{amount_ratio:.1f}× the user's "
                f"historical average."
            )

    if normal_velocity > 0:

        velocity_ratio = (
            current_velocity /
            normal_velocity
        )

        if velocity_ratio >= 2.0:

            evidence.append(
                f"Transaction velocity is "
                f"{velocity_ratio:.1f}× the user's "
                f"normal rate."
            )

    if not merchant_seen_before:

        evidence.append(
            "Merchant has not been seen in the user's "
            "previous transaction history."
        )

    if (
        merchant_category != usual_category
        and merchant_category in allowed_categories
    ):

        evidence.append(
            f"The current category differs from the user's "
            f"usual category '{usual_category}'."
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    if (
        decision == "STEP_UP"
        and source == "AUTHORIZATION"
    ):

        summary = (
            "Fresh user authorization is required because "
            "the proposed action exceeds the agent's current "
            "permission. This does not by itself indicate fraud."
        )

    elif (
        decision == "STEP_UP"
        and source == "BEHAVIORAL_RISK"
    ):

        summary = (
            "Additional user confirmation is required due "
            "to elevated behavioral risk."
        )

    elif decision == "BLOCK":

        summary = (
            "Transaction blocked due to high behavioral risk."
        )

    elif decision == "ALLOW":

        summary = (
            "Transaction allowed: authorization checks passed "
            "and behavioral risk is low."
        )

    else:

        summary = (
            "AgentShield evaluated the transaction."
        )

    return {
        "decision": decision,
        "risk_score": float(risk_score),
        "summary": summary,
        "evidence": evidence,
    }