from src.risk_engine import (
    train_behavioral_model,
    predict_risk,
)


model, scaler = train_behavioral_model()

profile = {
    "authorized_limit": 2000.0,
    "allowed_categories": ["groceries"],
    "avg_order_value": 450.0,
    "normal_velocity": 2,
    "usual_category": "groceries",
}

for amount in range(500, 1901, 50):
    for velocity in range(1, 7):
        for seen in [0, 1]:

            transaction = {
                "amount": float(amount),
                "merchant_category": "groceries",
                "merchant_name": "StepUpTest",
                "authorized_limit":
                    profile["authorized_limit"],
                "allowed_categories":
                    profile["allowed_categories"],
                "avg_order_value":
                    profile["avg_order_value"],
                "normal_velocity":
                    profile["normal_velocity"],
                "usual_category":
                    profile["usual_category"],
                "txns_in_last_10min": velocity,
                "merchant_seen_before": seen,
            }

            score = predict_risk(
                transaction,
                model,
                scaler,
            )

            if 0.70 <= score < 0.90:
                print("\nFOUND STEP_UP SCENARIO")
                print(f"Amount: ₹{amount}")
                print(f"Velocity: {velocity}")
                print(f"Merchant seen: {bool(seen)}")
                print(f"Risk score: {score:.3f}")
                raise SystemExit


print("No STEP_UP scenario found in search range.")