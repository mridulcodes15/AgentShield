import html
from datetime import datetime

import streamlit as st

from src.risk_engine import train_behavioral_model

from src.decision_engine import (
    evaluate_agent_action,
    reevaluate_after_reauthorization,
    confirm_behavioral_step_up,
)

from src.history_store import (
    build_user_profile,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AgentShield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HELPERS
# ============================================================

def safe(value):
    return html.escape(str(value))


def add_audit_event(
    merchant,
    amount,
    decision,
    risk,
    execution,
    event_type="EVALUATION",
    risk_mode=None,
    user_id=None,
):
    st.session_state.audit_log.insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "user_id": user_id,
            "merchant": merchant,
            "amount": float(amount),
            "decision": decision,
            "risk": risk,
            "execution": execution,
            "event_type": event_type,
            "risk_mode": risk_mode,
        },
    )


def clear_pending():
    st.session_state.current_result = None
    st.session_state.current_instruction = None
    st.session_state.current_proposal = None
    st.session_state.current_profile = None
    st.session_state.current_user_id = None


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background:
        radial-gradient(
            circle at 80% 0%,
            rgba(52, 91, 255, 0.13),
            transparent 32%
        ),
        radial-gradient(
            circle at 10% 30%,
            rgba(87, 57, 251, 0.08),
            transparent 28%
        ),
        #070b14;

    color: #f4f7ff;
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header[data-testid="stHeader"] {
    background: transparent;
}

section[data-testid="stSidebar"] {
    background: #090e1a;
    border-right: 1px solid rgba(255,255,255,0.07);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

h1, h2, h3 {
    letter-spacing: -0.03em;
}


/* BRAND */

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 28px;
}

.brand-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 21px;
    background: linear-gradient(135deg, #326bff, #7657ff);
    box-shadow: 0 8px 28px rgba(67, 92, 255, 0.28);
}

.brand-title {
    font-size: 20px;
    font-weight: 750;
}

.brand-subtitle {
    color: #748096;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}


/* HERO */

.hero {
    padding: 34px 36px;
    border-radius: 24px;
    border: 1px solid rgba(120, 143, 255, 0.18);
    background:
        linear-gradient(
            120deg,
            rgba(29, 45, 91, 0.72),
            rgba(10, 15, 29, 0.80)
        );
    box-shadow: 0 25px 70px rgba(0,0,0,0.22);
    margin-bottom: 24px;
}

.hero-badge {
    display: inline-block;
    padding: 6px 11px;
    border-radius: 999px;
    border: 1px solid rgba(104, 136, 255, 0.28);
    background: rgba(67, 91, 255, 0.10);
    color: #9fb3ff;
    font-size: 12px;
    font-weight: 650;
    margin-bottom: 15px;
}

.hero-title {
    font-size: 42px;
    line-height: 1.05;
    font-weight: 800;
    letter-spacing: -0.045em;
    margin-bottom: 12px;
}

.hero-title span {
    background: linear-gradient(90deg, #77a2ff, #a48aff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    max-width: 800px;
    color: #9ca8bc;
    font-size: 16px;
    line-height: 1.65;
}


/* METRICS */

.metric-card {
    border: 1px solid rgba(255,255,255,0.075);
    background: rgba(12, 18, 32, 0.76);
    border-radius: 18px;
    padding: 20px;
    min-height: 125px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.12);
}

.metric-label {
    color: #77849a;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
}

.metric-value {
    font-size: 28px;
    font-weight: 750;
    letter-spacing: -0.04em;
}

.metric-foot {
    color: #647087;
    font-size: 11px;
    margin-top: 7px;
}


/* SECTION */

.section-kicker {
    color: #65738c;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.12em;
    font-weight: 700;
    margin-bottom: 5px;
}

.section-title {
    font-size: 23px;
    font-weight: 730;
    margin-bottom: 4px;
}

.section-description {
    color: #77849a;
    font-size: 13px;
    margin-bottom: 20px;
}


/* STATUS */

.status {
    padding: 20px 22px;
    border-radius: 17px;
    margin: 16px 0;
}

.status-allow {
    background: rgba(24, 190, 128, 0.08);
    border: 1px solid rgba(24, 190, 128, 0.25);
}

.status-step {
    background: rgba(245, 171, 53, 0.08);
    border: 1px solid rgba(245, 171, 53, 0.27);
}

.status-block {
    background: rgba(241, 72, 91, 0.08);
    border: 1px solid rgba(241, 72, 91, 0.27);
}

.status-title {
    font-size: 20px;
    font-weight: 750;
    margin-bottom: 4px;
}

.status-description {
    color: #9ba6b8;
    font-size: 13px;
    line-height: 1.55;
}


/* RISK */

.risk-track {
    width: 100%;
    height: 9px;
    border-radius: 20px;
    background: #151d2c;
    overflow: hidden;
    margin-top: 8px;
}

.risk-fill {
    height: 100%;
    border-radius: 20px;
    background:
        linear-gradient(
            90deg,
            #27c88a,
            #f5b544,
            #ef4b61
        );
}


/* EVIDENCE */

.evidence-card {
    padding: 14px 16px;
    border-radius: 13px;
    border: 1px solid rgba(255,255,255,0.07);
    background: rgba(255,255,255,0.025);
    margin-bottom: 9px;
    color: #b7c0cf;
    font-size: 13px;
}


/* EXECUTION */

.execution-card {
    padding: 22px;
    border-radius: 17px;
    background: rgba(8, 14, 27, 0.75);
    border: 1px solid rgba(68, 112, 255, 0.18);
    margin-top: 14px;
}

.execution-label {
    color: #718099;
    font-size: 11px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

.execution-value {
    font-size: 19px;
    font-weight: 720;
    margin-top: 6px;
}


/* REAUTH */

.reauth-card {
    padding: 25px;
    border-radius: 19px;
    background:
        linear-gradient(
            135deg,
            rgba(245,171,53,0.09),
            rgba(20,26,42,0.75)
        );
    border: 1px solid rgba(245,171,53,0.25);
    margin-top: 20px;
    margin-bottom: 14px;
}

.reauth-title {
    font-size: 20px;
    font-weight: 760;
    margin-bottom: 7px;
}

.reauth-description {
    color: #aab3c1;
    font-size: 13px;
    line-height: 1.6;
    margin-bottom: 20px;
}

.reauth-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}

.reauth-item {
    padding: 14px;
    border-radius: 12px;
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
}

.reauth-label {
    color: #727f94;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}

.reauth-value {
    font-size: 18px;
    font-weight: 720;
}


/* BEHAVIOR */

.behavior-card {
    padding: 22px;
    border-radius: 17px;
    background: rgba(245, 171, 53, 0.055);
    border: 1px solid rgba(245, 171, 53, 0.18);
    margin-top: 18px;
}


/* PILLS */

.pill {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 650;
    background: rgba(76, 108, 255, 0.10);
    border: 1px solid rgba(76, 108, 255, 0.20);
    color: #9aafff;
    margin-right: 5px;
}


/* COLD START */

.cold-start-card {
    padding: 20px 22px;
    border-radius: 17px;
    background:
        linear-gradient(
            135deg,
            rgba(50, 107, 255, 0.09),
            rgba(18, 25, 43, 0.72)
        );
    border: 1px solid rgba(88, 124, 255, 0.22);
    margin-top: 10px;
    margin-bottom: 16px;
}

.cold-start-title {
    font-size: 18px;
    font-weight: 740;
    margin-bottom: 6px;
}

.cold-start-description {
    color: #9eabc0;
    font-size: 13px;
    line-height: 1.6;
}

.mode-chip {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    background: rgba(50, 107, 255, 0.10);
    border: 1px solid rgba(77, 114, 255, 0.20);
    color: #a9baff;
    margin-bottom: 10px;
}


/* PROFILE */

.profile-card {
    padding: 20px 22px;
    border-radius: 17px;
    background:
        linear-gradient(
            135deg,
            rgba(24,190,128,0.07),
            rgba(18,25,43,0.72)
        );
    border: 1px solid rgba(24,190,128,0.18);
    margin-top: 10px;
    margin-bottom: 16px;
}

.profile-title {
    font-size: 18px;
    font-weight: 740;
    margin-bottom: 6px;
}

.profile-description {
    color: #9eabc0;
    font-size: 13px;
    line-height: 1.6;
}

</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MODEL
# ============================================================

@st.cache_resource
def load_model():
    return train_behavioral_model()


model, scaler = load_model()


# ============================================================
# SESSION STATE
# ============================================================

if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

if "current_result" not in st.session_state:
    st.session_state.current_result = None

if "current_instruction" not in st.session_state:
    st.session_state.current_instruction = None

if "current_proposal" not in st.session_state:
    st.session_state.current_proposal = None

if "current_profile" not in st.session_state:
    st.session_state.current_profile = None

if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = None

if "cancelled_message" not in st.session_state:
    st.session_state.cancelled_message = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
<div class="brand">
<div class="brand-icon">🛡</div>
<div>
<div class="brand-title">AgentShield</div>
<div class="brand-subtitle">AI Payment Security</div>
</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Evaluate Transaction",
            "Audit Trail",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.caption("SYSTEM STATUS")

    st.success(
        "● Risk Engine Online"
    )

    st.info(
        "● Razorpay Test Mode"
    )

    st.divider()

    st.caption(
        "DECISION POLICY"
    )

    st.write(
        "🟢 < 0.70 · LOW RISK"
    )

    st.write(
        "🟡 ≥ 0.70 · STEP_UP"
    )

    st.write(
        "🔴 ≥ 0.90 + 3 strong signals · BLOCK"
    )

    st.caption(
        "A single unusual signal can require confirmation "
        "without automatically blocking the payment."
    )

    st.caption(
        "Authorization overflow → fresh approval"
    )

    st.divider()

    st.caption(
        "AgentShield • Buildathon 2026"
    )


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    st.markdown(
        """
<div class="hero">
<div class="hero-badge">AGENTIC PAYMENT SECURITY</div>
<div class="hero-title">
Authorization is not <span>safety.</span>
</div>
<div class="hero-description">
AgentShield adds an adaptive risk and authorization layer between
AI agents and payment execution. It distinguishes between an agent
exceeding its current permission and genuinely high-risk behavioral
activity before a payment reaches the payment rail.
</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)

    with m1:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">Precision</div>
<div class="metric-value">97.8%</div>
<div class="metric-foot">
Protective intervention
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with m2:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">
Protective Recall
</div>
<div class="metric-value">
100%
</div>
<div class="metric-foot">
Held-out synthetic benchmark
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with m3:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">
Legitimate FP Rate
</div>
<div class="metric-value">
0.5%
</div>
<div class="metric-foot">
Unseen-user evaluation
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with m4:

        st.markdown(
            f"""
<div class="metric-card">
<div class="metric-label">
Audit Events
</div>
<div class="metric-value">
{len(st.session_state.audit_log)}
</div>
<div class="metric-foot">
Current demo session
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="section-kicker">
Architecture
</div>

<div class="section-title">
Adaptive authorization pipeline
</div>

<div class="section-description">
AgentShield separates user consent from behavioral risk.
Exceeding current authorization requests fresh consent;
it does not automatically classify the transaction as fraud.
For new users, it falls back to authorization-first cold-start
mode instead of inventing behavioral history.
</div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c, d = st.columns(4)

    with a:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">
01 · Understand
</div>
<div class="metric-value" style="font-size:19px;">
Intent Parser
</div>
<div class="metric-foot">
Natural language → structured authorization
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with b:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">
02 · Verify
</div>
<div class="metric-value" style="font-size:19px;">
Authorization
</div>
<div class="metric-foot">
Check current amount and category permission
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with c:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">
03 · Detect
</div>
<div class="metric-value" style="font-size:19px;">
Behavioral ML
</div>
<div class="metric-foot">
Amount, velocity and familiarity signals
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    with d:

        st.markdown(
            """
<div class="metric-card">
<div class="metric-label">
04 · Act
</div>
<div class="metric-value" style="font-size:19px;">
Execution Gate
</div>
<div class="metric-foot">
Allow, request consent or block
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(
        "Benchmark figures are from AgentShield's synthetic "
        "held-out evaluation with unseen users. They are not "
        "production Razorpay performance."
    )


# ============================================================
# EVALUATE TRANSACTION
# ============================================================

elif page == "Evaluate Transaction":

    st.markdown(
        """
<div class="section-kicker">
Live Decision Engine
</div>

<div class="section-title">
Evaluate an agent payment
</div>

<div class="section-description">
Simulate a financial action proposed by an AI agent.
AgentShield automatically retrieves persistent user history,
checks authorization, evaluates behavioral risk when sufficient
history exists, and gates Razorpay test-order creation.
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<span class="pill">Groq Intent Parsing</span>
<span class="pill">Persistent SQLite History</span>
<span class="pill">Behavioral ML</span>
<span class="pill">Adaptive Authorization</span>
<span class="pill">Razorpay Test Mode</span>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # INPUTS
    # ========================================================

    left, right = st.columns(
        [1.15, 0.85],
        gap="large",
    )

    with left:

        st.subheader(
            "User Authorization"
        )

        st.caption(
            "This instruction represents the user's delegated "
            "permission to the AI agent."
        )

        instruction = st.text_area(
            "Natural-language instruction",
            value=(
                "Buy my usual groceries but do not spend "
                "more than ₹2,000."
            ),
            height=105,
        )

        st.subheader(
            "Agent Proposal"
        )

        c1, c2 = st.columns(2)

        with c1:

            merchant_name = st.text_input(
                "Merchant",
                value="DailyMart",
            )

            amount = st.number_input(
                "Current checkout amount (₹)",
                min_value=1.0,
                value=500.0,
                step=50.0,
            )

        with c2:

            merchant_category = st.selectbox(
                "Category",
                [
                    "groceries",
                    "food",
                    "travel",
                    "shopping",
                    "utilities",
                ],
            )

            txns_in_last_10min = st.number_input(
                "Current transactions / 10 min",
                min_value=0,
                value=1,
                step=1,
            )

    # ========================================================
    # AUTOMATIC PROFILE
    # ========================================================

    with right:

        st.subheader(
            "Behavioral Profile"
        )

        st.caption(
            "Persistent confirmed transaction history is "
            "loaded automatically."
        )

        user_id = st.text_input(
            "User ID",
            value="demo_user_001",
            help=(
                "Reuse the same User ID across transactions "
                "to build its behavioral profile."
            ),
        ).strip()

        if user_id:

            try:

                live_profile = build_user_profile(
                    user_id
                )

            except Exception as exc:

                st.error(
                    f"History error: {exc}"
                )

                live_profile = {
                    "has_history": False,
                    "transaction_count": 0,
                    "minimum_required": 5,
                }

        else:

            live_profile = {
                "has_history": False,
                "transaction_count": 0,
                "minimum_required": 5,
            }

        has_history = live_profile.get(
            "has_history",
            False,
        )

        transaction_count = live_profile.get(
            "transaction_count",
            0,
        )

        minimum_required = live_profile.get(
            "minimum_required",
            5,
        )

        if not has_history:

            st.markdown(
                f"""
<div class="cold-start-card">

<div class="mode-chip">
COLD START MODE
</div>

<div class="cold-start-title">
Authorization-first protection
</div>

<div class="cold-start-description">

AgentShield found
<b>{transaction_count}</b>
confirmed transaction(s) for
<b>{safe(user_id or "this user")}</b>.

Behavioral ML activates after
<b>{minimum_required}</b>
confirmed transactions.

Until then, explicit amount and category
permissions remain active without inventing
a behavioral baseline.

</div>

</div>
                """,
                unsafe_allow_html=True,
            )

            progress = (
                min(
                    transaction_count,
                    minimum_required,
                )
                / minimum_required
                if minimum_required
                else 0
            )

            st.progress(
                progress
            )

            st.caption(
                f"Profile progress: "
                f"{transaction_count} / "
                f"{minimum_required} confirmed transactions"
            )

            p1, p2 = st.columns(2)

            p1.metric(
                "Confirmed Transactions",
                transaction_count,
            )

            p2.metric(
                "Behavioral ML",
                "Inactive",
            )

            st.write(
                "✓ Amount authorization active"
            )

            st.write(
                "✓ Category authorization active"
            )

            st.write(
                "○ Behavioral model awaiting history"
            )

        else:

            st.markdown(
                f"""
<div class="profile-card">

<div class="mode-chip">
BEHAVIORAL MODEL ACTIVE
</div>

<div class="profile-title">
Persistent profile established
</div>

<div class="profile-description">

AgentShield has enough confirmed activity
for <b>{safe(user_id)}</b> to evaluate
behavioral deviations in addition to
explicit authorization.

</div>

</div>
                """,
                unsafe_allow_html=True,
            )

            p1, p2 = st.columns(2)

            p1.metric(
                "Confirmed Transactions",
                transaction_count,
            )

            p2.metric(
                "Profile Status",
                "Established",
            )

            st.metric(
                "Average Order Value",
                (
                    f"₹"
                    f"{live_profile['avg_order_value']:,.2f}"
                ),
            )

            st.write(
                "**Usual category:** "
                f"{live_profile['usual_category']}"
            )

            st.write(
                "**Normal velocity:** "
                f"{live_profile['normal_velocity']} "
                "transactions / 10 min"
            )

            st.caption(
                "Average order value and usual category are "
                "derived from confirmed stored transactions. "
                "The prototype currently uses a default "
                "normal-velocity baseline."
            )

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    evaluate = st.button(
        "⚡ Evaluate Agent Action",
        type="primary",
        use_container_width=True,
    )

    # ========================================================
    # NEW EVALUATION
    # ========================================================

    if evaluate:

        st.session_state.cancelled_message = None

        if not user_id:

            st.error(
                "Enter a User ID before evaluating the action."
            )

        else:

            proposed_transaction = {
                "merchant_name":
                    merchant_name,

                "merchant_category":
                    merchant_category,

                "amount":
                    amount,

                "txns_in_last_10min":
                    txns_in_last_10min,
            }

            try:

                profile_before = build_user_profile(
                    user_id
                )

                with st.spinner(
                    (
                        "Loading persistent profile and "
                        "evaluating behavioral risk..."
                        if profile_before.get(
                            "has_history",
                            False,
                        )
                        else
                        "Evaluating explicit authorization "
                        "in cold-start mode..."
                    )
                ):

                    result = evaluate_agent_action(
                        instruction=instruction,
                        proposed_transaction=
                            proposed_transaction,
                        user_id=user_id,
                        model=model,
                        scaler=scaler,
                    )

                st.session_state.current_result = (
                    result
                )

                st.session_state.current_instruction = (
                    instruction
                )

                st.session_state.current_proposal = (
                    proposed_transaction
                )

                st.session_state.current_profile = (
                    profile_before
                )

                st.session_state.current_user_id = (
                    user_id
                )

                if (
                    result["status"]
                    == "CLARIFICATION_REQUIRED"
                ):

                    add_audit_event(
                        user_id=user_id,
                        merchant=merchant_name,
                        amount=amount,
                        decision=
                            "CLARIFICATION_REQUIRED",
                        risk=None,
                        execution="STOPPED",
                        event_type="AUTHORIZATION",
                        risk_mode="NOT_EVALUATED",
                    )

                else:

                    decision = result["decision"]
                    transaction = result["transaction"]
                    razorpay = result["razorpay"]

                    add_audit_event(
                        user_id=user_id,
                        merchant=
                            transaction["merchant_name"],
                        amount=
                            transaction["amount"],
                        decision=
                            decision["decision"],
                        risk=(
                            None
                            if decision[
                                "risk_score"
                            ] is None
                            else round(
                                decision[
                                    "risk_score"
                                ],
                                3,
                            )
                        ),
                        execution=
                            razorpay["status"],
                        event_type=
                            "INITIAL_EVALUATION",
                        risk_mode=
                            result.get(
                                "risk_mode",
                                decision.get(
                                    "risk_mode",
                                ),
                            ),
                    )

            except Exception as exc:

                st.error(
                    f"AgentShield error: {exc}"
                )

    # ========================================================
    # CANCEL MESSAGE
    # ========================================================

    if st.session_state.cancelled_message:

        st.markdown(
            """
<div class="status status-block">
<div class="status-title">
✕ Payment Cancelled
</div>
<div class="status-description">
The user rejected the proposed payment.
No Razorpay order was created.
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            st.session_state.cancelled_message
        )

    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    result = st.session_state.current_result

    if result is not None:

        # ====================================================
        # CLARIFICATION
        # ====================================================

        if (
            result["status"]
            == "CLARIFICATION_REQUIRED"
        ):

            st.markdown(
                """
<div class="status status-step">
<div class="status-title">
⚠ Clarification Required
</div>
<div class="status-description">
The user's financial authorization is incomplete.
AgentShield stopped the action before payment execution.
</div>
</div>
                """,
                unsafe_allow_html=True,
            )

            st.warning(
                result["message"]
            )

            st.caption(
                "AgentShield does not invent a spending "
                "limit when the user has not provided one."
            )

        # ====================================================
        # EVALUATED RESULT
        # ====================================================

        else:

            decision = result["decision"]
            explanation = result["explanation"]
            razorpay = result["razorpay"]
            transaction = result["transaction"]

            action = decision["decision"]
            source = decision["decision_source"]
            risk = decision["risk_score"]

            risk_mode = result.get(
                "risk_mode",
                decision.get(
                    "risk_mode",
                    "BEHAVIORAL_MODEL",
                ),
            )

            result_user_id = result.get(
                "user_id",
                st.session_state.current_user_id,
            )

            # ================================================
            # STATUS
            # ================================================

            if action == "ALLOW":

                status_class = "status-allow"
                status_icon = "✓"
                status_text = "Action Approved"

                if (
                    source == "USER_CONFIRMATION"
                ):

                    description = (
                        "The transaction was originally flagged "
                        "for behavioral confirmation. The user "
                        "explicitly confirmed this exact action, "
                        "so AgentShield released it for execution."
                    )

                elif risk_mode == "COLD_START":

                    description = (
                        "The action is within the user's explicit "
                        "authorization. Behavioral ML was not run "
                        "because sufficient confirmed history "
                        "does not yet exist."
                    )

                else:

                    description = (
                        "The action is covered by the user's "
                        "authorization and behavioral risk is low."
                    )

            elif (
                action == "STEP_UP"
                and source == "AUTHORIZATION"
            ):

                status_class = "status-step"
                status_icon = "⚠"
                status_text = (
                    "Re-authorization Required"
                )

                description = (
                    "The agent exceeded its current permission. "
                    "Fresh consent is required; this is not "
                    "automatically classified as fraud."
                )

            elif action == "STEP_UP":

                status_class = "status-step"
                status_icon = "⚠"
                status_text = (
                    "Behavioral Confirmation Required"
                )

                description = (
                    "The action is authorized, but elevated "
                    "behavioral signals require additional "
                    "user confirmation."
                )

            else:

                status_class = "status-block"
                status_icon = "✕"
                status_text = "Action Blocked"

                description = (
                    "Very high behavioral risk is supported by "
                    "multiple strong anomaly signals. Payment "
                    "execution was prevented."
                )

            st.markdown(
                f"""
<div class="status {status_class}">
<div class="status-title">
{status_icon} {safe(action)} · {safe(status_text)}
</div>

<div class="status-description">
{safe(description)}
</div>
</div>
                """,
                unsafe_allow_html=True,
            )

            # ================================================
            # METRICS
            # ================================================

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "Risk Score",
                (
                    "N/A"
                    if risk is None
                    else f"{risk:.3f}"
                ),
            )

            m2.metric(
                "Decision",
                action,
            )

            m3.metric(
                "Authorized Limit",
                (
                    f"₹"
                    f"{transaction['authorized_limit']:,.0f}"
                ),
            )

            m4.metric(
                "Current Checkout",
                (
                    f"₹"
                    f"{transaction['amount']:,.0f}"
                ),
            )

            # ================================================
            # RISK
            # ================================================

            st.markdown(
                "#### Behavioral Risk"
            )

            if risk_mode == "COLD_START":

                st.markdown(
                    """
<div class="cold-start-card">

<div class="mode-chip">
RISK SCORE · N/A
</div>

<div class="cold-start-title">
Behavioral model intentionally skipped
</div>

<div class="cold-start-description">
There is not enough confirmed personal history to
produce a meaningful behavioral score. AgentShield
uses explicit authorization rather than treating
missing history as zero risk.
</div>

</div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                risk_percent = max(
                    0,
                    min(
                        100,
                        risk * 100,
                    ),
                )

                st.markdown(
                    f"""
<div class="risk-track">
<div
class="risk-fill"
style="width:{risk_percent}%;">
</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )

                r1, r2, r3 = st.columns(3)

                r1.caption(
                    "0.00 · Low"
                )

                r2.caption(
                    "0.70 · Step-up"
                )

                r3.caption(
                    "0.90 · High risk"
                )

            # ================================================
            # CONTEXT
            # ================================================

            left_result, right_result = st.columns(
                2,
                gap="large",
            )

            with left_result:

                st.markdown(
                    "### Authorization Context"
                )

                st.write(
                    "✓ Explicit spending limit parsed"
                )

                st.write(
                    "✓ Authorized category parsed"
                )

                st.write(
                    "**Current limit:** "
                    f"₹"
                    f"{transaction['authorized_limit']:,.2f}"
                )

                categories = ", ".join(
                    transaction[
                        "allowed_categories"
                    ]
                )

                st.write(
                    f"**Allowed:** {categories}"
                )

                parser = (
                    result.get(
                        "intent",
                        {},
                    ).get(
                        "parser",
                        "Existing authorization",
                    )
                )

                st.write(
                    "**Authorization source:** "
                    f"{parser}"
                )

            with right_result:

                if risk_mode == "COLD_START":

                    st.markdown(
                        "### Cold-Start Context"
                    )

                    st.write(
                        "✓ **No behavioral baseline assumed**"
                    )

                    st.write(
                        "✓ **Behavioral ML:** Not run"
                    )

                    st.write(
                        "**Current velocity observed:** "
                        f"{transaction['txns_in_last_10min']}"
                    )

                    profile_before = result.get(
                        "profile_before_transaction",
                        {},
                    )

                    count_before = (
                        profile_before.get(
                            "transaction_count",
                            0,
                        )
                    )

                    st.write(
                        "**Confirmed history before action:** "
                        f"{count_before}"
                    )

                else:

                    st.markdown(
                        "### Behavioral Context"
                    )

                    st.write(
                        "**Historical average at evaluation:** "
                        f"₹"
                        f"{transaction['avg_order_value']:,.2f}"
                    )

                    st.write(
                        "**Velocity:** "
                        f"{transaction['txns_in_last_10min']} "
                        "vs normal "
                        f"{transaction['normal_velocity']}"
                    )

                    known = (
                        "Yes"
                        if transaction[
                            "merchant_seen_before"
                        ]
                        else "No"
                    )

                    st.write(
                        f"**Known merchant:** {known}"
                    )

                    st.write(
                        "**Usual category:** "
                        f"{transaction['usual_category']}"
                    )

            # ================================================
            # EVIDENCE
            # ================================================

            st.markdown(
                "### Decision Evidence"
            )

            st.write(
                explanation["summary"]
            )

            if explanation["evidence"]:

                for item in explanation["evidence"]:

                    st.markdown(
                        f"""
<div class="evidence-card">
↳ {safe(item)}
</div>
                        """,
                        unsafe_allow_html=True,
                    )

            else:

                st.markdown(
                    """
<div class="evidence-card">
✓ No elevated behavioral signals were detected.
</div>
                    """,
                    unsafe_allow_html=True,
                )

            # ================================================
            # AUTHORIZATION STEP-UP
            # ================================================

            if (
                action == "STEP_UP"
                and source == "AUTHORIZATION"
            ):

                old_limit = float(
                    transaction[
                        "authorized_limit"
                    ]
                )

                current_amount = float(
                    transaction["amount"]
                )

                difference = max(
                    0.0,
                    current_amount - old_limit,
                )

                st.markdown(
                    f"""
<div class="reauth-card">

<div class="reauth-title">
⚠ Fresh authorization required
</div>

<div class="reauth-description">
The checkout exceeded the amount originally
authorized. AgentShield paused execution and
requests fresh consent instead of classifying
the higher amount as automatic fraud.
</div>

<div class="reauth-grid">

<div class="reauth-item">
<div class="reauth-label">
Original Authorization
</div>
<div class="reauth-value">
₹{old_limit:,.2f}
</div>
</div>

<div class="reauth-item">
<div class="reauth-label">
Current Checkout
</div>
<div class="reauth-value">
₹{current_amount:,.2f}
</div>
</div>

<div class="reauth-item">
<div class="reauth-label">
Additional Approval
</div>
<div class="reauth-value">
+₹{difference:,.2f}
</div>
</div>

</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )

                approve_col, cancel_col = (
                    st.columns(2)
                )

                with approve_col:

                    approve_revised = st.button(
                        (
                            "✓ Approve revised amount "
                            f"₹{current_amount:,.2f}"
                        ),
                        key="approve_reauthorization",
                        use_container_width=True,
                        type="primary",
                    )

                with cancel_col:

                    cancel_revised = st.button(
                        "✕ Cancel Payment",
                        key="cancel_reauthorization",
                        use_container_width=True,
                    )

                if approve_revised:

                    try:

                        with st.spinner(
                            (
                                "Updating authorization and "
                                "re-checking behavioral risk..."
                                if risk_mode
                                == "BEHAVIORAL_MODEL"
                                else
                                "Updating authorization in "
                                "cold-start mode..."
                            )
                        ):

                            new_result = (
                                reevaluate_after_reauthorization(
                                    transaction=
                                        transaction,
                                    revised_limit=
                                        current_amount,
                                    model=model,
                                    scaler=scaler,
                                )
                            )

                        new_result["intent"] = (
                            result.get(
                                "intent",
                                {},
                            )
                        )

                        new_result["user_id"] = (
                            result_user_id
                        )

                        new_result[
                            "profile_before_transaction"
                        ] = result.get(
                            "profile_before_transaction",
                            {},
                        )

                        st.session_state.current_result = (
                            new_result
                        )

                        new_decision = (
                            new_result["decision"]
                        )

                        new_razorpay = (
                            new_result["razorpay"]
                        )

                        add_audit_event(
                            user_id=
                                result_user_id,

                            merchant=
                                transaction[
                                    "merchant_name"
                                ],

                            amount=
                                current_amount,

                            decision=
                                new_decision[
                                    "decision"
                                ],

                            risk=(
                                None
                                if new_decision[
                                    "risk_score"
                                ] is None
                                else round(
                                    new_decision[
                                        "risk_score"
                                    ],
                                    3,
                                )
                            ),

                            execution=
                                new_razorpay[
                                    "status"
                                ],

                            event_type=
                                "REAUTHORIZED",

                            risk_mode=
                                new_result.get(
                                    "risk_mode",
                                    new_decision.get(
                                        "risk_mode",
                                    ),
                                ),
                        )

                        st.session_state.cancelled_message = (
                            None
                        )

                        st.rerun()

                    except Exception as exc:

                        st.error(
                            "Re-authorization failed: "
                            f"{exc}"
                        )

                if cancel_revised:

                    add_audit_event(
                        user_id=result_user_id,
                        merchant=
                            transaction[
                                "merchant_name"
                            ],
                        amount=current_amount,
                        decision="USER_CANCELLED",
                        risk=(
                            None
                            if risk is None
                            else round(
                                risk,
                                3,
                            )
                        ),
                        execution="CANCELLED",
                        event_type=
                            "REAUTHORIZATION_REJECTED",
                        risk_mode=risk_mode,
                    )

                    clear_pending()

                    st.session_state.cancelled_message = (
                        "The revised amount was not "
                        "authorized by the user."
                    )

                    st.rerun()

            # ================================================
            # BEHAVIORAL STEP-UP
            # ================================================

            elif (
                action == "STEP_UP"
                and source == "BEHAVIORAL_RISK"
            ):

                st.markdown(
                    """
<div class="behavior-card">

<div class="reauth-title">
⚠ Unusual activity requires confirmation
</div>

<div class="reauth-description">
The transaction is within explicit authorization,
but AgentShield detected unusual behavioral activity.
Payment remains paused until the user explicitly
confirms or rejects this exact transaction.
</div>

</div>
                    """,
                    unsafe_allow_html=True,
                )

                st.info(
                    "Behavioral STEP_UP does not classify unusual "
                    "behavior as fraud automatically. The user can "
                    "confirm the exact transaction or cancel it."
                )

                confirm_col, cancel_col = (
                    st.columns(2)
                )

                with confirm_col:

                    confirm_behavior = st.button(
                        "✓ Confirm Transaction",
                        key="confirm_behavioral_stepup",
                        use_container_width=True,
                        type="primary",
                    )

                with cancel_col:

                    cancel_behavior = st.button(
                        "✕ Cancel Transaction",
                        key="cancel_behavioral_stepup",
                        use_container_width=True,
                    )

                if confirm_behavior:

                    try:

                        with st.spinner(
                            "Confirming transaction and creating "
                            "Razorpay test order..."
                        ):

                            confirmed_result = (
                                confirm_behavioral_step_up(
                                    transaction=transaction,
                                    original_decision=decision,
                                )
                            )

                        confirmed_result["intent"] = (
                            result.get(
                                "intent",
                                {},
                            )
                        )

                        confirmed_result["user_id"] = (
                            result_user_id
                        )

                        confirmed_result[
                            "profile_before_transaction"
                        ] = result.get(
                            "profile_before_transaction",
                            {},
                        )

                        st.session_state.current_result = (
                            confirmed_result
                        )

                        confirmed_razorpay = (
                            confirmed_result["razorpay"]
                        )

                        add_audit_event(
                            user_id=result_user_id,
                            merchant=
                                transaction[
                                    "merchant_name"
                                ],
                            amount=
                                transaction["amount"],
                            decision="ALLOW",
                            risk=(
                                None
                                if risk is None
                                else round(
                                    risk,
                                    3,
                                )
                            ),
                            execution=
                                confirmed_razorpay[
                                    "status"
                                ],
                            event_type=
                                "BEHAVIORAL_CONFIRMED",
                            risk_mode=
                                "BEHAVIORAL_MODEL",
                        )

                        st.session_state.cancelled_message = (
                            None
                        )

                        st.rerun()

                    except Exception as exc:

                        st.error(
                            "Behavioral confirmation failed: "
                            f"{exc}"
                        )

                if cancel_behavior:

                    add_audit_event(
                        user_id=result_user_id,
                        merchant=
                            transaction[
                                "merchant_name"
                            ],
                        amount=
                            transaction["amount"],
                        decision="USER_CANCELLED",
                        risk=(
                            None
                            if risk is None
                            else round(
                                risk,
                                3,
                            )
                        ),
                        execution="CANCELLED",
                        event_type=
                            "BEHAVIORAL_STEPUP_REJECTED",
                        risk_mode=risk_mode,
                    )

                    clear_pending()

                    st.session_state.cancelled_message = (
                        "The transaction was cancelled "
                        "after the behavioral warning."
                    )

                    st.rerun()

            # ================================================
            # PAYMENT EXECUTION
            # ================================================

            st.markdown(
                "### Payment Execution"
            )

            if razorpay["executed"]:

                order = razorpay["order"]

                st.markdown(
                    f"""
<div class="execution-card">

<div class="execution-label">
Razorpay Test Mode
</div>

<div class="execution-value">
✓ ORDER CREATED
</div>

<br>

<b>Order ID</b><br>
{safe(order['order_id'])}

<br><br>

<b>Amount</b><br>
₹{order['amount_rupees']:,.2f} INR

<br><br>

<span style="color:#718099;font-size:12px;">
A created test order is not a completed real-money payment.
</span>

</div>
                    """,
                    unsafe_allow_html=True,
                )

                history_result = result.get(
                    "history",
                    {},
                )

                if history_result.get(
                    "saved",
                    False,
                ):

                    st.success(
                        "✓ Confirmed test-order event saved "
                        "to persistent behavioral history."
                    )

                    profile_after = (
                        history_result.get(
                            "profile_after_transaction"
                        )
                    )

                    if profile_after:

                        new_count = (
                            profile_after.get(
                                "transaction_count",
                                0,
                            )
                        )

                        st.caption(
                            "Persistent history now contains "
                            f"{new_count} confirmed transaction(s)."
                        )

                        if (
                            profile_after.get(
                                "has_history",
                                False,
                            )
                            and risk_mode == "COLD_START"
                        ):

                            st.info(
                                "Behavioral profile threshold reached. "
                                "The next transaction for this user "
                                "will use behavioral ML."
                            )

            else:

                st.markdown(
                    f"""
<div class="execution-card">

<div class="execution-label">
Razorpay Execution Gate
</div>

<div class="execution-value">
{safe(razorpay['status'])}
</div>

<br>

{safe(razorpay['message'])}

</div>
                    """,
                    unsafe_allow_html=True,
                )


# ============================================================
# AUDIT TRAIL
# ============================================================

elif page == "Audit Trail":

    st.markdown(
        """
<div class="section-kicker">
Decision History
</div>

<div class="section-title">
Agent activity audit trail
</div>

<div class="section-description">
Session-level record of authorization decisions,
behavioral evaluations, re-authorization events
and Razorpay execution outcomes.
</div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.audit_log:

        st.info(
            "No transactions evaluated in this session yet. "
            "Open Evaluate Transaction to run a demo."
        )

    else:

        for event in st.session_state.audit_log:

            risk_text = (
                "N/A"
                if event["risk"] is None
                else f"{event['risk']:.3f}"
            )

            event_type = event.get(
                "event_type",
                "EVALUATION",
            )

            risk_mode = event.get(
                "risk_mode",
            )

            mode_text = (
                "N/A"
                if not risk_mode
                else risk_mode
            )

            event_user = (
                event.get(
                    "user_id"
                )
                or "N/A"
            )

            st.markdown(
                f"""
<div class="execution-card">

<div class="execution-label">
{safe(event['time'])}
&nbsp; · &nbsp;
{safe(event_type)}
</div>

<div class="execution-value">
{safe(event['merchant'])}
&nbsp; · &nbsp;
₹{event['amount']:,.2f}
</div>

<br>

User:
<b>{safe(event_user)}</b>

&nbsp;&nbsp;•&nbsp;&nbsp;

Decision:
<b>{safe(event['decision'])}</b>

&nbsp;&nbsp;•&nbsp;&nbsp;

Risk:
<b>{safe(risk_text)}</b>

&nbsp;&nbsp;•&nbsp;&nbsp;

Mode:
<b>{safe(mode_text)}</b>

&nbsp;&nbsp;•&nbsp;&nbsp;

Execution:
<b>{safe(event['execution'])}</b>

</div>
                """,
                unsafe_allow_html=True,
            )