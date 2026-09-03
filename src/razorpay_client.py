"""
AgentShield — Razorpay Test Client

Creates Razorpay Orders only when AgentShield has approved
a transaction.

Safety:
- Test Mode only
- Refuses live Razorpay keys
- BLOCK and STEP_UP do not create orders
"""

import os
import uuid

import razorpay
from dotenv import load_dotenv


load_dotenv()


def get_razorpay_client():
    """
    Create a Razorpay client using TEST credentials only.
    """

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise ValueError(
            "Razorpay credentials are not configured."
        )

    # Critical hackathon safety guard
    if not key_id.startswith("rzp_test_"):
        raise ValueError(
            "AgentShield refuses to use Razorpay Live Mode. "
            "Use a rzp_test_ key."
        )

    return razorpay.Client(
        auth=(key_id, key_secret)
    )


def create_test_order(
    amount_rupees,
    merchant_name="AgentShield Demo",
):
    """
    Create a Razorpay Test Mode order.

    Razorpay expects INR amounts in paise.
    Example:
        ₹500 → 50000
    """

    if amount_rupees <= 0:
        raise ValueError(
            "Order amount must be greater than zero."
        )

    client = get_razorpay_client()

    amount_paise = int(
        round(amount_rupees * 100)
    )

    # Razorpay receipts should be unique and <= 40 chars.
    receipt = (
        "agentshield_"
        + uuid.uuid4().hex[:16]
    )

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "notes": {
            "source": "AgentShield",
            "merchant": str(merchant_name)[:200],
        },
    }

    order = client.order.create(
        data=order_data
    )

    return {
        "order_id": order["id"],
        "status": order["status"],
        "amount_rupees":
            order["amount"] / 100,
        "currency": order["currency"],
        "receipt": order["receipt"],
    }


def execute_if_allowed(
    proposed_transaction,
    decision_result,
):
    """
    Create a Razorpay order only for ALLOW decisions.
    """

    decision = decision_result["decision"]

    if decision == "BLOCK":
        return {
            "executed": False,
            "status": "BLOCKED",
            "message": (
                "Razorpay order was not created because "
                "AgentShield blocked the transaction."
            ),
        }

    if decision == "STEP_UP":
        return {
            "executed": False,
            "status": "AWAITING_CONFIRMATION",
            "message": (
                "Razorpay order was not created because "
                "additional user confirmation is required."
            ),
        }

    if decision != "ALLOW":
        raise ValueError(
            f"Unknown AgentShield decision: {decision}"
        )

    order = create_test_order(
        amount_rupees=
            proposed_transaction["amount"],
        merchant_name=
            proposed_transaction["merchant_name"],
    )

    return {
        "executed": True,
        "status": "ORDER_CREATED",
        "order": order,
    }


if __name__ == "__main__":

    print(
        create_test_order(
            amount_rupees=10.0,
            merchant_name="AgentShield Test",
        )
    )