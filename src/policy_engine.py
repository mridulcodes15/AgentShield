"""
AgentShield — Policy & Decision Engine

Decision semantics:

ALLOW
    Explicit authorization is satisfied and behavioral risk is low.

STEP_UP
    Fresh user authorization or additional user confirmation is required.

BLOCK
    Reserved for high behavioral risk supported by multiple strong
    behavioral warning signals.

Core principle:

Authorization and behavioral risk are separate concepts.

An authorization violation is NOT automatically fraud.
The AI agent simply does not currently have permission to proceed.

Likewise, one unusual behavioral signal is NOT automatically fraud.
A rare but legitimate purchase should normally receive STEP_UP
confirmation rather than an irreversible BLOCK.
"""


# ============================================================
# DECISION THRESHOLDS
# ============================================================

ALLOW_THRESHOLD = 0.70
BLOCK_THRESHOLD = 0.90


# ============================================================
# BEHAVIORAL SIGNAL THRESHOLDS
# ============================================================

# These are prototype policy thresholds used to interpret
# the behavioral model's risk score.
#
# They are NOT claimed to be universal production thresholds.

STRONG_AMOUNT_DEVIATION = 3.0
STRONG_VELOCITY_DEVIATION = 3.0

MIN_STRONG_SIGNALS_FOR_BLOCK = 3


# ============================================================
# CATEGORY NORMALIZATION
# ============================================================

def _normalize_categories(value):
    """
    Normalize allowed categories into a lowercase list.

    Supports:

    ["groceries", "food"]

    and

    "groceries|food"
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


# ============================================================
# AUTHORIZATION CHECK
# ============================================================

def check_authorization(transaction):
    """
    Check whether the proposed transaction is covered by the
    user's CURRENT explicit authorization.

    Returns:
        passed: bool
        reasons: list
    """

    reasons = []

    amount = float(
        transaction["amount"]
    )

    authorized_limit = float(
        transaction["authorized_limit"]
    )

    merchant_category = str(
        transaction["merchant_category"]
    ).strip().lower()

    allowed_categories = _normalize_categories(
        transaction["allowed_categories"]
    )

    # --------------------------------------------------------
    # Amount authorization
    # --------------------------------------------------------

    if amount > authorized_limit:

        reasons.append(
            f"Proposed amount ₹{amount:.2f} exceeds "
            f"the currently authorized limit of "
            f"₹{authorized_limit:.2f}."
        )

    # --------------------------------------------------------
    # Category authorization
    # --------------------------------------------------------

    if merchant_category not in allowed_categories:

        reasons.append(
            f"Category '{merchant_category}' is not covered "
            f"by the current authorization."
        )

    return len(reasons) == 0, reasons


# ============================================================
# BEHAVIORAL SIGNAL ANALYSIS
# ============================================================

def analyze_behavioral_signals(transaction):
    """
    Inspect interpretable behavioral warning signals.

    Important:

    These signals do NOT independently label a transaction
    as fraud.

    They are used by the decision policy to distinguish:

        one unusual but plausible event
            -> STEP_UP

        multiple strong anomalies
            -> BLOCK

    Returns a dictionary containing:

        signals
        strong_signals
        strong_signal_count
    """

    signals = []
    strong_signals = []

    # --------------------------------------------------------
    # 1. Amount deviation
    # --------------------------------------------------------

    avg_order_value = transaction.get(
        "avg_order_value"
    )

    if (
        avg_order_value is not None
        and float(avg_order_value) > 0
    ):

        amount_ratio = (
            float(transaction["amount"])
            / float(avg_order_value)
        )

        if amount_ratio >= STRONG_AMOUNT_DEVIATION:

            message = (
                f"Transaction amount is "
                f"{amount_ratio:.1f}× the user's "
                f"historical average."
            )

            signals.append(message)
            strong_signals.append(
                "AMOUNT_DEVIATION"
            )

        elif amount_ratio >= 2.0:

            signals.append(
                f"Transaction amount is "
                f"{amount_ratio:.1f}× the user's "
                f"historical average."
            )

    # --------------------------------------------------------
    # 2. Velocity deviation
    # --------------------------------------------------------

    normal_velocity = transaction.get(
        "normal_velocity"
    )

    current_velocity = transaction.get(
        "txns_in_last_10min"
    )

    if (
        normal_velocity is not None
        and current_velocity is not None
        and float(normal_velocity) > 0
    ):

        velocity_ratio = (
            float(current_velocity)
            / float(normal_velocity)
        )

        if (
            velocity_ratio
            >= STRONG_VELOCITY_DEVIATION
        ):

            signals.append(
                f"Recent transaction velocity is "
                f"{velocity_ratio:.1f}× the user's "
                f"normal level."
            )

            strong_signals.append(
                "VELOCITY_DEVIATION"
            )

        elif velocity_ratio >= 2.0:

            signals.append(
                f"Recent transaction velocity is "
                f"{velocity_ratio:.1f}× the user's "
                f"normal level."
            )

    # --------------------------------------------------------
    # 3. Merchant familiarity
    # --------------------------------------------------------

    merchant_seen_before = transaction.get(
        "merchant_seen_before"
    )

    if merchant_seen_before is not None:

        if not bool(
            merchant_seen_before
        ):

            signals.append(
                "The merchant has not appeared in the "
                "user's confirmed transaction history."
            )

            strong_signals.append(
                "NEW_MERCHANT"
            )

    # --------------------------------------------------------
    # 4. Usual-category deviation
    # --------------------------------------------------------

    usual_category = transaction.get(
        "usual_category"
    )

    merchant_category = transaction.get(
        "merchant_category"
    )

    if (
        usual_category is not None
        and merchant_category is not None
    ):

        usual = str(
            usual_category
        ).strip().lower()

        current = str(
            merchant_category
        ).strip().lower()

        if usual != current:

            # Category deviation is useful evidence,
            # but it is intentionally NOT counted as
            # a strong blocking signal by itself.
            signals.append(
                f"Category '{current}' differs from the "
                f"user's usual category '{usual}'."
            )

    return {
        "signals": signals,
        "strong_signals": strong_signals,
        "strong_signal_count":
            len(strong_signals),
    }


# ============================================================
# MAIN DECISION POLICY
# ============================================================

def make_decision(
    transaction,
    risk_score,
):
    """
    Combine explicit authorization and behavioral risk.

    Priority:

    1. Authorization violation
       -> STEP_UP for fresh user authorization.

    2. Authorization valid + very high model risk +
       multiple strong behavioral signals
       -> BLOCK.

    3. Authorization valid + high model risk but only
       one strong behavioral signal
       -> STEP_UP for confirmation.

    4. Authorization valid + elevated behavioral risk
       -> STEP_UP.

    5. Authorization valid + low behavioral risk
       -> ALLOW.

    This prevents a single rare-but-legitimate purchase
    from automatically becoming a hard block.
    """

    risk_score = float(
        risk_score
    )

    authorization_passed, authorization_reasons = (
        check_authorization(
            transaction
        )
    )

    # ========================================================
    # 1. AUTHORIZATION VIOLATION
    # ========================================================

    if not authorization_passed:

        return {
            "decision":
                "STEP_UP",

            "decision_source":
                "AUTHORIZATION",

            "risk_score":
                risk_score,

            "reasons":
                authorization_reasons,

            "requires_reauthorization":
                True,

            "behavioral_signals":
                [],

            "strong_signal_count":
                0,
        }

    # ========================================================
    # Behavioral evidence
    # ========================================================

    behavioral_analysis = (
        analyze_behavioral_signals(
            transaction
        )
    )

    behavioral_signals = (
        behavioral_analysis[
            "signals"
        ]
    )

    strong_signals = (
        behavioral_analysis[
            "strong_signals"
        ]
    )

    strong_signal_count = (
        behavioral_analysis[
            "strong_signal_count"
        ]
    )

    # ========================================================
    # 2. VERY HIGH RISK
    # ========================================================

    if risk_score >= BLOCK_THRESHOLD:

        # ----------------------------------------------------
        # Multiple strong anomalies
        # ----------------------------------------------------

        if (
            strong_signal_count
            >= MIN_STRONG_SIGNALS_FOR_BLOCK
        ):

            reasons = [
                (
                    "High behavioral risk is supported "
                    "by multiple strong anomaly signals."
                )
            ]

            reasons.extend(
                behavioral_signals
            )

            return {
                "decision":
                    "BLOCK",

                "decision_source":
                    "BEHAVIORAL_RISK",

                "risk_score":
                    risk_score,

                "reasons":
                    reasons,

                "requires_reauthorization":
                    False,

                "behavioral_signals":
                    strong_signals,

                "strong_signal_count":
                    strong_signal_count,
            }

        # ----------------------------------------------------
        # Only one strong anomaly
        # ----------------------------------------------------

        reasons = [
            (
                "Behavioral risk is very high, but the "
                "evidence does not contain enough independent "
                "strong signals for an automatic block. "
                "User confirmation is required."
            )
        ]

        reasons.extend(
            behavioral_signals
        )

        return {
            "decision":
                "STEP_UP",

            "decision_source":
                "BEHAVIORAL_RISK",

            "risk_score":
                risk_score,

            "reasons":
                reasons,

            "requires_reauthorization":
                False,

            "behavioral_signals":
                strong_signals,

            "strong_signal_count":
                strong_signal_count,
        }

    # ========================================================
    # 3. ELEVATED RISK
    # ========================================================

    if risk_score >= ALLOW_THRESHOLD:

        reasons = [
            (
                "Behavioral risk requires additional "
                "user confirmation."
            )
        ]

        reasons.extend(
            behavioral_signals
        )

        return {
            "decision":
                "STEP_UP",

            "decision_source":
                "BEHAVIORAL_RISK",

            "risk_score":
                risk_score,

            "reasons":
                reasons,

            "requires_reauthorization":
                False,

            "behavioral_signals":
                strong_signals,

            "strong_signal_count":
                strong_signal_count,
        }

    # ========================================================
    # 4. LOW RISK
    # ========================================================

    return {
        "decision":
            "ALLOW",

        "decision_source":
            "BEHAVIORAL_RISK",

        "risk_score":
            risk_score,

        "reasons":
            [],

        "requires_reauthorization":
            False,

        "behavioral_signals":
            strong_signals,

        "strong_signal_count":
            strong_signal_count,
    }