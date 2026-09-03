# 🛡️ AgentShield

### Adaptive Risk & Authorization Layer for Agent-Initiated Payments

AgentShield is an AI-powered risk and authorization layer designed for the emerging world of agentic payments.

It evaluates whether an AI agent's proposed financial action is not only within the user's explicit authorization, but also behaviorally consistent with the user's historical spending patterns.

Instead of treating every unusual transaction as fraud, AgentShield separates **consent** from **risk** and applies progressive intervention through:

- **ALLOW** — transaction is authorized and low risk
- **STEP_UP** — fresh user authorization or behavioral confirmation is required
- **BLOCK** — reserved for very high-risk transactions supported by multiple strong anomaly signals

> **Core principle:** Authorization tells us what the agent is allowed to do. Behavioral risk tells us whether the action still looks safe.
---

## 🎯 Problem Statement

AI agents are increasingly capable of initiating purchases and financial actions on behalf of users. Existing authorization mechanisms can define **what an agent is permitted to spend**, but staying within those limits does not necessarily mean every transaction is safe.

An agent may still perform an unusual action while remaining technically authorized — such as making a significantly larger purchase than normal, transacting with an unfamiliar merchant, or generating an abnormal burst of transactions.

AgentShield addresses this gap by combining:

- **Explicit Authorization Validation** — verifies amount and category constraints.
- **Behavioral Risk Analysis** — evaluates the transaction against historical user behavior.
- **Adaptive Intervention** — chooses between `ALLOW`, `STEP_UP`, and `BLOCK` based on authorization and risk evidence.
- **Human-in-the-Loop Verification** — asks the user for fresh authorization or transaction confirmation when appropriate.
- **Razorpay Test Execution** — creates a Razorpay test order only after the action is approved.

This creates an additional safety layer between an autonomous agent's **intent to pay** and the payment system's **execution of that intent**.

## ⚙️ How AgentShield Works

AgentShield evaluates every proposed agent-initiated transaction through two separate security layers:

### 1. Authorization Layer

The user's natural-language instruction is converted into structured constraints such as:

- Maximum authorized amount
- Allowed spending categories
- Transaction context

If the proposed transaction exceeds these permissions, AgentShield returns **`STEP_UP`** and requests fresh user authorization.

An authorization violation is **not automatically classified as fraud**.

### 2. Behavioral Risk Layer

For users with sufficient confirmed transaction history, AgentShield evaluates behavioral signals including:

- Amount deviation from historical spending
- Transaction velocity deviation
- Merchant familiarity
- Usual category behavior

A Logistic Regression model produces a behavioral risk score, which is combined with interpretable anomaly signals by the policy engine.

### Adaptive Decision Policy

| Condition | Decision | Action |
|---|---|---|
| Authorization violated | `STEP_UP` | Request fresh authorization |
| Authorized + low behavioral risk | `ALLOW` | Permit test-order execution |
| Authorized + elevated/high risk | `STEP_UP` | Ask user to confirm the exact transaction |
| Risk ≥ 0.90 + ≥ 3 strong anomaly signals | `BLOCK` | Prevent execution |

> AgentShield treats an anomaly as a reason for **verification**, not automatically as fraud. Hard blocking is reserved for stronger combinations of independent risk signals.

---

## 🧊 Cold-Start Protection

Behavioral models require historical data. AgentShield does **not fabricate a behavioral baseline for new users**.

When a user has insufficient confirmed transaction history:

- Explicit authorization checks remain active from the first transaction.
- No artificial behavioral risk score is generated.
- `risk_mode` is set to `COLD_START`.
- An authorized transaction can proceed through the authorization-first flow.
- Confirmed transactions gradually build the user's behavioral profile.

Once sufficient confirmed history is available, AgentShield activates behavioral risk analysis.

> **Authorization protection works from transaction #1. Behavioral protection becomes stronger as confirmed history accumulates.**

---

## 💳 Razorpay Test-Mode Integration

AgentShield places the risk layer **before payment execution**.

```text
Agent proposes transaction
        ↓
AgentShield evaluates authorization + risk
        ↓
ALLOW / STEP_UP / BLOCK
        ↓
Approved transaction
        ↓
Razorpay Test Order Created
