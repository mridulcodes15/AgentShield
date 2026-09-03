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

---

## 🏗️ System Architecture

```mermaid
flowchart TD

    A["👤 User Authorization<br/>Natural-language spending instruction"]
    B["🤖 AI Agent<br/>Proposes payment action"]

    A --> C
    B --> C

    C["🧠 Intent Parser<br/>Groq LLM + Deterministic Validation<br/>Extract limit • category • constraints"]

    C --> D{"Authorization<br/>Valid?"}

    D -- "No" --> E["⚠️ STEP_UP<br/>Fresh User Authorization"]
    E --> F{"User approves<br/>revised authorization?"}

    F -- "No" --> X["✕ CANCEL<br/>No payment execution"]
    F -- "Yes" --> G

    D -- "Yes" --> G{"Sufficient Confirmed<br/>User History?"}

    G -- "No · Cold Start" --> H["🛡️ Authorization-First Mode<br/>No fabricated behavioral score"]
    H --> R

    G -- "Yes" --> I["📊 Behavioral Risk Engine<br/>Logistic Regression"]

    I --> J["Behavioral Signals<br/>Amount deviation<br/>Velocity deviation<br/>Merchant familiarity<br/>Category behavior"]

    J --> K["⚙️ Adaptive Policy Engine"]

    K --> L{"Risk + Strong<br/>Signal Evidence"}

    L -- "Low Risk" --> R["✓ ALLOW"]
    L -- "Elevated / High Risk" --> M["⚠️ STEP_UP<br/>Behavioral Confirmation"]
    L -- "≥ 0.90 + ≥ 3 strong signals" --> N["⛔ BLOCK"]

    M --> O{"User confirms exact<br/>transaction?"}

    O -- "No" --> X
    O -- "Yes" --> R

    R --> P["💳 Razorpay Test Mode<br/>Create Test Order"]

    P --> Q["🗃️ Persistent SQLite History<br/>Store confirmed transaction"]

    Q -. "Future behavioral profile" .-> G

    N --> S["🔒 Execution Prevented"]
    X --> S

    classDef input fill:#172554,stroke:#60a5fa,color:#fff,stroke-width:2px;
    classDef engine fill:#312e81,stroke:#a78bfa,color:#fff,stroke-width:2px;
    classDef decision fill:#422006,stroke:#fbbf24,color:#fff,stroke-width:2px;
    classDef allow fill:#052e16,stroke:#4ade80,color:#fff,stroke-width:2px;
    classDef step fill:#451a03,stroke:#fb923c,color:#fff,stroke-width:2px;
    classDef block fill:#450a0a,stroke:#f87171,color:#fff,stroke-width:2px;
    classDef payment fill:#082f49,stroke:#38bdf8,color:#fff,stroke-width:2px;

    class A,B input;
    class C,I,J,K engine;
    class D,F,G,L,O decision;
    class R,Q allow;
    class E,M step;
    class N,X,S block;
    class P,H payment;
