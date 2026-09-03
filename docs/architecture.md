# AgentShield — System Architecture

This document describes the end-to-end architecture and decision flow of AgentShield, from agent authorization to behavioral risk evaluation and Razorpay test-order execution.

## Architecture Diagram

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
```

## Decision Philosophy

AgentShield separates **authorization** from **behavioral risk**:

- Authorization violation → `STEP_UP` for fresh authorization.
- Authorized but unusual behavior → `STEP_UP` for transaction confirmation.
- Low-risk authorized behavior → `ALLOW`.
- Very high risk supported by at least three strong independent anomaly signals → `BLOCK`.

This prevents unusual but legitimate transactions from being automatically treated as fraud.
