# 🛡️ AgentShield

### Adaptive Risk & Authorization Layer for Agent-Initiated Payments

AgentShield is an AI-powered risk and authorization layer designed for the emerging world of agentic payments.

It evaluates whether an AI agent's proposed financial action is not only within the user's explicit authorization, but also behaviorally consistent with the user's historical spending patterns.

Instead of treating every unusual transaction as fraud, AgentShield separates **consent** from **risk** and applies progressive intervention through:

- **ALLOW** — transaction is authorized and low risk
- **STEP_UP** — fresh user authorization or behavioral confirmation is required
- **BLOCK** — reserved for very high-risk transactions supported by multiple strong anomaly signals

> **Core principle:** Authorization tells us what the agent is allowed to do. Behavioral risk tells us whether the action still looks safe.
