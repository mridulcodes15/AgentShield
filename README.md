# 🛡️ AgentShield

### Adaptive Risk & Authorization Layer for Agent-Initiated Payments

AgentShield is an AI-powered risk and authorization layer designed for the emerging world of **agentic payments**.

It evaluates whether an AI agent's proposed financial action is not only within the user's explicit authorization, but also behaviorally consistent with the user's historical spending patterns.

Instead of treating every unusual transaction as fraud, AgentShield separates **consent** from **risk** and applies progressive intervention:

- 🟢 **ALLOW** — authorized and low-risk transaction
- 🟡 **STEP_UP** — fresh authorization or behavioral confirmation required
- 🔴 **BLOCK** — reserved for very high-risk transactions supported by multiple strong anomaly signals

> **Core Principle:** Authorization tells us what the agent is allowed to do. Behavioral risk tells us whether the action still looks safe.

---

## 🎯 Problem Statement

AI agents are increasingly capable of initiating purchases and financial actions on behalf of users.

Existing authorization mechanisms can define **what an agent is permitted to spend**, but remaining within those limits does not necessarily mean every transaction is safe.

An agent may remain technically authorized while performing an unusual action, such as:

- Making a significantly larger purchase than the user's normal spending
- Transacting with an unfamiliar merchant
- Generating an abnormal burst of transactions
- Acting outside the user's usual spending behavior

A purely static authorization system may therefore approve transactions that satisfy the original rules while still exhibiting significant behavioral risk.

**AgentShield adds an adaptive risk layer between an AI agent's intent to pay and payment execution.**

---

## 💡 The Solution

AgentShield combines five components:

### 1. Explicit Authorization Validation
Checks whether the proposed amount and merchant category satisfy the user's current authorization.

### 2. Behavioral Risk Analysis
Evaluates the transaction against confirmed historical behavior using features such as amount deviation, velocity deviation, merchant familiarity, and usual category behavior.

### 3. Adaptive Policy Engine
Combines authorization state, ML risk score, and interpretable anomaly signals to choose between:

`ALLOW` → `STEP_UP` → `BLOCK`

### 4. Human-in-the-Loop Verification
Requests fresh authorization or exact transaction confirmation instead of automatically treating every anomaly as fraud.

### 5. Razorpay Test Execution
Only approved actions proceed to Razorpay test-order creation.

---

## 🏗️ System Architecture

AgentShield follows an authorization-first, risk-aware architecture that separates explicit user permission from behavioral risk evaluation.
📐 **Detailed Mermaid architecture:** [View the complete system architecture](docs/architecture.md)

---

## ⚙️ How AgentShield Works

AgentShield separates the decision process into two major security layers.

### Layer 1 — Authorization

The user's natural-language authorization is converted into structured constraints such as:

- Maximum authorized amount
- Allowed spending categories
- Transaction context

If an agent exceeds the current authorization, AgentShield returns:

```text
STEP_UP → Fresh User Authorization Required
```

An authorization violation is **not automatically classified as fraud**.

If the user expands or revises the authorization, AgentShield evaluates the transaction again.

> Re-authorization expands what the agent is permitted to do. It does not override the behavioral risk engine.

### Layer 2 — Behavioral Risk

For users with sufficient confirmed history, AgentShield evaluates:

- Amount deviation from historical spending
- Transaction velocity deviation
- Merchant familiarity
- Usual category behavior

A Logistic Regression model produces a behavioral risk score.

The policy engine then combines this score with interpretable anomaly signals before deciding how strongly to intervene.

---

## 🚦 Adaptive Decision Policy

| Condition | Decision | System Action |
|---|---|---|
| Authorization violated | 🟡 `STEP_UP` | Request fresh authorization |
| Authorized + low behavioral risk | 🟢 `ALLOW` | Permit test-order execution |
| Authorized + elevated/high risk | 🟡 `STEP_UP` | Request exact transaction confirmation |
| Risk ≥ 0.90 + ≥ 3 strong signals | 🔴 `BLOCK` | Prevent execution |

Strong signals currently include:

- Amount ≥ 3× historical average
- Transaction velocity ≥ 3× normal
- Previously unseen merchant

The three-signal BLOCK requirement is a **prototype policy threshold**, not a claim that three signals is universally optimal in production.

> **AgentShield treats anomaly as a reason for verification, not automatically as fraud.**

Hard blocking is deliberately conservative.

---

## 🟡 Two Different STEP_UP Flows

AgentShield distinguishes between two fundamentally different reasons for requesting user involvement.

### Authorization STEP_UP

```text
Agent exceeds authorization
        ↓
Fresh user authorization requested
        ↓
Authorization updated
        ↓
Behavioral risk evaluated
```

The user is changing **what the agent is permitted to do**.

### Behavioral STEP_UP

```text
Transaction is authorized
        ↓
Behavioral anomaly detected
        ↓
User sees warning
        ↓
Confirm Transaction / Cancel Transaction
```

The user is confirming **this exact transaction**.

Confirmation does not erase the original risk score or pretend that the anomaly disappeared.

---

## 🧊 Cold-Start Protection

Behavioral models require historical data.

AgentShield deliberately does **not fabricate behavioral history for new users**.

When sufficient confirmed history is unavailable:

- Explicit authorization checks remain active
- No artificial behavioral risk score is generated
- `risk_score = None`
- `risk_mode = COLD_START`
- Authorized transactions can proceed through the authorization-first flow
- Confirmed transactions gradually establish the behavioral profile

Once sufficient confirmed history exists, behavioral ML becomes active.

> **Authorization protection works from transaction #1. Behavioral protection becomes stronger as confirmed history accumulates.**

---

## 💳 Razorpay Test-Mode Integration

AgentShield places the risk decision **before payment execution**.

```text
Agent proposes transaction
        ↓
AgentShield evaluates authorization + risk
        ↓
ALLOW / STEP_UP / BLOCK
        ↓
Approved action
        ↓
Razorpay Test Order
```

### Execution Rules

- `ALLOW` → Razorpay test order can be created
- Authorization `STEP_UP` → waits for fresh user authorization
- Behavioral `STEP_UP` → waits for confirmation of the exact transaction
- `BLOCK` → no Razorpay order is created
- User cancellation → no Razorpay order is created

Only successfully approved test-order transactions are persisted into the local SQLite history store.

These confirmed transactions are then used to derive future behavioral profiles.

> **Important:** AgentShield currently creates Razorpay **test orders**. Test-order creation does not mean a real payment has been captured or completed.

---

# 📊 Evaluation

AgentShield was evaluated against a **static authorization baseline** using a controlled synthetic dataset.

The final dataset contains **10,000 transactions**, including legitimate activity and four controlled risk scenarios:

- Budget abuse
- Category abuse
- Velocity abuse
- Behavioral anomaly

The dataset intentionally contains approximately **15% risky examples** to provide sufficient evaluation coverage.

This is a controlled benchmark distribution and **does not represent real Razorpay transaction traffic or fraud prevalence**.

---

## 🧪 Unseen-User Evaluation

To reduce user-level leakage between training and evaluation, users were separated using a group-based train/test split.

```text
Training users : 375
Test users     : 125
User overlap   : 0

Training rows  : 7,468
Test rows      : 2,532
```

Therefore, behavioral evaluation is performed on users not present in the model's training split.

---

## 📈 Static Authorization vs AgentShield

| Metric | Static Authorization | AgentShield |
|---|---:|---:|
| Precision | 100.0% | **97.8%** |
| Recall | 46.4% | **100.0%** |
| F1 Score | 0.634 | **0.989** |
| False Negatives | 233 | **0** |
| False Positives | 0 | **10** |

### What changed?

Static authorization successfully detects explicit amount/category violations.

However, it misses transactions that remain technically authorized while exhibiting behavioral or velocity anomalies.

On the controlled held-out benchmark:

```text
Static Authorization
TP = 202
FP = 0
FN = 233
TN = 2097
```

AgentShield produced:

```text
AgentShield
TP = 435
FP = 10
FN = 0
TN = 2087
```

This improved protective-intervention recall from:

```text
46.4% → 100.0%
```

while reducing:

```text
False Negatives: 233 → 0
```

---

## 🎯 Scenario-Wise Detection

| Scenario | Protective Intervention Rate |
|---|---:|
| Budget abuse | 100% |
| Category abuse | 100% |
| Velocity abuse | 100% |
| Behavioral anomaly | 100% |

These values are measured on the controlled synthetic held-out benchmark.

They should **not** be interpreted as claims of 100% fraud detection in real-world payment traffic.

---

## ⚖️ False-Positive Cost & User Friction

A risk system should not be evaluated only on how many risky transactions it catches.

Unnecessary intervention also has a cost.

Among **2,097 legitimate held-out transactions**:

```text
Unnecessary STEP_UPs : 10
False hard BLOCKs    : 0
```

This corresponds to:

```text
Legitimate intervention friction = 0.477%
False hard-block rate            = 0.000%
```

The cost of these false positives is primarily:

- Additional verification friction
- Increased transaction latency
- Potential user abandonment

AgentShield therefore deliberately distinguishes between **verification** and **hard blocking**.

A general production cost model can be represented as:

```text
Total Cost =
    C_FN × False Negatives
  + C_STEPUP × False STEP_UPs
  + C_BLOCK × False BLOCKs
```

No monetary cost is assigned in this prototype because real merchant conversion and loss data were not available.

---

## 🛑 Why Were There Zero BLOCK Decisions in the Final Benchmark?

The final conservative policy requires:

```text
Risk Score ≥ 0.90
        +
At least 3 strong independent anomaly signals
```

The held-out evaluation dataset contained transactions with zero, one, or two strong signals, but no evaluated transaction simultaneously contained all three strong signals required by the final BLOCK policy.

Therefore:

```text
ALLOW    : 2087
STEP_UP  : 445
BLOCK    : 0
```

This is intentional.

The dataset was **not modified to manufacture BLOCK examples after the final policy was selected**.

AgentShield instead reports the observed evaluation honestly.

---

## 🧠 Behavioral Risk Model

The behavioral risk engine uses:

**Logistic Regression + StandardScaler**

Behavioral features include:

```text
amount_to_history_ratio
velocity_ratio
usual_category_match
merchant_seen_before
```

Authorization features are intentionally handled separately by deterministic policy checks.

This prevents the ML model from becoming responsible for decisions that can be verified directly against explicit user permissions.

---

## 🗂️ Persistent Behavioral History

AgentShield uses a local SQLite store to maintain confirmed transaction history.

For established users, the system derives behavioral context such as:

- Average order value
- Usual merchant category
- Merchant familiarity
- Transaction history count
- Prototype velocity baseline

History is updated only after successful approved test-order execution.

The local database itself is excluded from Git through `.gitignore`.

---

## 🧾 Explainable Decisions

Every AgentShield evaluation produces human-readable evidence describing why intervention occurred.

Examples include:

```text
Transaction amount is significantly above the user's historical average.
```

```text
Merchant has not previously appeared in the user's confirmed history.
```

```text
Transaction velocity is significantly above the user's normal baseline.
```

The explanation layer reports **observable evidence** rather than claiming that an individual feature definitively caused fraud.

---

## 🤖 Natural-Language Authorization

AgentShield supports natural-language authorization instructions such as:

```text
Allow my shopping agent to spend up to ₹2,000 on groceries.
```

The intent parser converts the instruction into structured authorization constraints.

The LLM is used only for **structured intent extraction**.

It does **not** decide whether a transaction is fraudulent or whether it should be blocked.

Deterministic validation is applied to extracted financial constraints before they enter the risk pipeline.

---

## 🖥️ Interactive Dashboard

The Streamlit dashboard demonstrates the complete AgentShield lifecycle:

- Natural-language authorization
- Structured intent extraction
- Cold-start users
- Established behavioral profiles
- Transaction simulation
- Risk scoring
- Evidence generation
- `ALLOW / STEP_UP / BLOCK`
- Fresh authorization
- Behavioral transaction confirmation
- Razorpay test-order creation
- Persistent transaction history
- Evaluation metrics

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Dashboard | Streamlit |
| Machine Learning | scikit-learn |
| Data Processing | Pandas, NumPy |
| Risk Model | Logistic Regression |
| LLM Intent Parsing | Groq API |
| Payment Integration | Razorpay Test API |
| Persistent History | SQLite |
| Configuration | python-dotenv |
| Architecture | Mermaid |
| Version Control | Git + GitHub |

---

## 📁 Project Structure

```text
AgentShield/
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── raw/
│   │   ├── synthetic_transactions_v2.csv
│   │   └── synthetic_transactions_v3.csv
│   ├── processed/
│   │   └── agentshield_history.db        # Local / ignored
│   └── generate_synthetic_data.py
│
├── docs/
│   └── architecture.md
│
├── experiments/
│   ├── baseline_vs_agentshield.py
│   ├── final_evaluation.py
│   ├── find_step_up.py
│   ├── test_end_to_end.py
│   └── threshold_analysis.py
│
├── src/
│   ├── decision_engine.py
│   ├── explainer.py
│   ├── feature_engineering.py
│   ├── history_store.py
│   ├── intent_parser.py
│   ├── policy_engine.py
│   ├── razorpay_client.py
│   └── risk_engine.py
│
├── .env                         # Local / ignored
├── .gitignore
├── requirements.txt
└── README.md
```

---

# 🚀 Running AgentShield Locally

## 1. Clone the Repository

```bash
git clone https://github.com/mridulcodes15/AgentShield.git
cd AgentShield
```

## 2. Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a local `.env` file.

```env
GROQ_API_KEY=your_groq_api_key

RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_test_secret
```

Only Razorpay **test credentials** should be used with the prototype.

Never commit `.env` or API secrets to GitHub.

## 5. Run the Final Evaluation

```bash
python -m experiments.final_evaluation
```

## 6. Start the Dashboard

```bash
streamlit run dashboard/app.py
```

---

## 🔐 Security Considerations

AgentShield follows several prototype security practices:

- API credentials are loaded from environment variables
- `.env` is excluded from Git
- Razorpay integration accepts test-mode credentials
- Runtime SQLite history is excluded from source control
- BLOCK decisions cannot directly create payment orders
- STEP_UP requires explicit user interaction before execution
- LLM output does not directly control the final risk decision

---

## 💰 Business Model

AgentShield can be positioned as a **B2B risk infrastructure layer for agentic commerce**.

A potential commercial model could include:

### Developer Tier
Sandbox access for testing agent authorization and risk policies.

### Usage-Based Risk API
Pricing based on the number of agentic transaction risk evaluations.

Example unit:

```text
Risk evaluations per 1,000 agent-initiated transactions
```

### Enterprise Tier
Potential capabilities:

- Custom risk policies
- Organization-specific thresholds
- Audit trails
- Risk analytics
- Advanced behavioral profiles
- SLA-backed risk infrastructure
- Enterprise integrations

This is a conceptual business model for AgentShield and **does not represent Razorpay's actual product pricing**.

---

## 🌍 Potential Production Architecture

A production version could extend the prototype with:

- Real captured-payment outcomes
- Distributed behavioral feature store
- Dynamically calculated transaction velocity
- Risk-score calibration
- Merchant/network-level signals
- Device and session context
- Organization-specific policies
- Real-time monitoring
- Model drift detection
- Stronger audit infrastructure
- Agent identity and authorization standards
- Deeper integration with agentic payment infrastructure

---

## ⚠️ Current Limitations

AgentShield is a hackathon prototype and controlled research implementation.

Current limitations include:

1. **Synthetic Dataset**  
   Evaluation uses generated transactions rather than real Razorpay merchant traffic.

2. **Synthetic Class Distribution**  
   The benchmark intentionally contains a higher proportion of risky examples than may occur in real payment systems.

3. **Prototype Thresholds**  
   Risk thresholds and strong-signal thresholds were selected for the controlled prototype and require production calibration.

4. **Local SQLite History**  
   Behavioral history is currently stored locally rather than in a production feature store.

5. **Simplified Velocity Baseline**  
   Normal transaction velocity uses a prototype baseline rather than a complete streaming behavioral model.

6. **Test Orders Only**  
   Razorpay integration creates test orders and does not represent captured real-money payments.

7. **Behavioral History Requirement**  
   New users initially rely on authorization protection until sufficient confirmed history is available.

These limitations are intentionally documented rather than hidden behind benchmark metrics.

---

## 🧭 Design Principles

AgentShield is built around four principles:

**1. Risk ≠ Consent**  
A transaction can be authorized and still deserve additional verification.

**2. Authorization ≠ Safety**  
Static limits define permission, not behavioral normality.

**3. Anomaly ≠ Fraud**  
Unusual behavior should usually trigger verification before hard blocking.

**4. Re-authorization ≠ Risk Bypass**  
Changing permission does not disable behavioral protection.

---

## 🛡️ Defense-Only Design

AgentShield is designed as a defensive payment-risk prototype.

Its purpose is to:

- Detect risky agent-initiated financial actions
- Enforce user authorization
- Introduce verification when uncertainty exists
- Prevent high-confidence unsafe execution
- Produce interpretable risk evidence

It is not designed to autonomously perform unauthorized financial actions.

---

## 🔮 Vision

As AI agents gain the ability to search, negotiate, purchase, and transact on behalf of users, payment infrastructure needs to answer two separate questions:

> **“Is the agent authorized to do this?”**

and

> **“Even if it is authorized, does this action still look safe?”**

AgentShield explores an adaptive risk layer built around both.

---

## 👩‍💻 Author

**Mridul Paradkar**

Built for the **Razorpay AI Buildathon 2026 — AI Risk Manager Track**.

---

## 📌 Benchmark Disclaimer

All performance metrics reported in this repository are measured on a **controlled synthetic dataset** created for prototype evaluation.

They are not claims about performance on Razorpay production traffic, real merchants, or real-world fraud prevalence.

### 🚀 Live Demo

**[Launch AgentShield →](https://agentshield-ai.streamlit.app/)**
