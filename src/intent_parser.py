"""
AgentShield — Intent Parser

Uses an LLM to convert natural-language payment instructions
into structured authorization.

The LLM NEVER makes the security decision.

If the LLM/API fails, AgentShield falls back to the
deterministic parser.
"""

import os
import re
import json

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


# ============================================================
# Supported categories
# ============================================================

CATEGORY_KEYWORDS = {
    "groceries": [
        "grocery",
        "groceries",
        "supermarket",
    ],
    "food": [
        "food",
        "meal",
        "restaurant",
        "lunch",
        "dinner",
    ],
    "travel": [
        "travel",
        "flight",
        "hotel",
        "cab",
        "taxi",
    ],
    "shopping": [
        "shopping",
        "clothes",
        "clothing",
        "fashion",
    ],
    "utilities": [
        "utility",
        "utilities",
        "electricity",
        "water bill",
        "internet bill",
    ],
}


ALLOWED_CATEGORIES = list(
    CATEGORY_KEYWORDS.keys()
)


# ============================================================
# Deterministic fallback
# ============================================================

def extract_amount(text):

    patterns = [
        r"₹\s*([\d,]+)",
        r"rs\.?\s*([\d,]+)",
        r"inr\s*([\d,]+)",
        r"(?:under|below|upto|up to|max|maximum)"
        r"\s*₹?\s*([\d,]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            amount = (
                match.group(1)
                .replace(",", "")
            )

            return float(amount)

    return None


def extract_categories(text):

    text = text.lower()

    detected = []

    for category, keywords in (
        CATEGORY_KEYWORDS.items()
    ):

        for keyword in keywords:

            if keyword in text:

                detected.append(category)
                break

    return detected


def deterministic_parse(text):

    amount = extract_amount(text)
    categories = extract_categories(text)

    missing_fields = []

    if amount is None:
        missing_fields.append(
            "authorized_limit"
        )

    if not categories:
        missing_fields.append(
            "allowed_categories"
        )

    return {
        "original_instruction": text,
        "intent": "purchase",
        "authorized_limit": amount,
        "allowed_categories": categories,
        "requires_clarification":
            len(missing_fields) > 0,
        "missing_fields": missing_fields,
        "parser": "deterministic_fallback",
    }


# ============================================================
# Validate LLM output
# ============================================================

def validate_llm_result(result, text):
    """
    Validate the LLM output before allowing it into
    the AgentShield security pipeline.
    """

    amount = result.get(
        "authorized_limit"
    )

    categories = result.get(
        "allowed_categories",
        [],
    )

    # Never accept invented/non-positive amounts.
    if amount is not None:

        try:
            amount = float(amount)

            if amount <= 0:
                amount = None

        except (TypeError, ValueError):
            amount = None

    # Only allow categories AgentShield understands.
    if not isinstance(categories, list):
        categories = []

    categories = [
        category
        for category in categories
        if category in ALLOWED_CATEGORIES
    ]

    # --------------------------------------------------------
    # Critical safety validation
    #
    # The LLM cannot create financial authorization that
    # wasn't explicitly present in the user's instruction.
    # --------------------------------------------------------

    deterministic_amount = extract_amount(
        text
    )

    if deterministic_amount is None:
        amount = None

    missing_fields = []

    if amount is None:
        missing_fields.append(
            "authorized_limit"
        )

    if not categories:
        missing_fields.append(
            "allowed_categories"
        )

    return {
        "original_instruction": text,
        "intent": "purchase",
        "authorized_limit": amount,
        "allowed_categories": categories,
        "requires_clarification":
            len(missing_fields) > 0,
        "missing_fields": missing_fields,
        "parser": "groq_llm",
    }


# ============================================================
# Groq parser
# ============================================================

def llm_parse(text):

    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not configured."
        )

    client = Groq(
        api_key=api_key
    )

    prompt = f"""
You are an intent parser for a payment authorization system.

Convert the user's instruction into JSON.

User instruction:
{text}

Return ONLY valid JSON with this exact structure:

{{
  "intent": "purchase",
  "authorized_limit": number or null,
  "allowed_categories": []
}}

Allowed categories are ONLY:

{ALLOWED_CATEGORIES}

Rules:

1. Never invent a spending limit.
2. If no explicit spending limit exists, use null.
3. Never infer financial authorization beyond what the user said.
4. Only use categories from the allowed category list.
5. Return JSON only.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,
        response_format={
            "type": "json_object"
        },
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    result = json.loads(content)

    return validate_llm_result(
        result,
        text,
    )


# ============================================================
# Public parser
# ============================================================

def parse_intent(text):
    """
    Main AgentShield parser.

    Try LLM first.
    Fall back safely if API/model parsing fails.
    """

    try:

        return llm_parse(text)

    except Exception as error:

        print(
            f"[Intent Parser] "
            f"LLM unavailable: {error}"
        )

        return deterministic_parse(
            text
        )


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":

    examples = [
        (
            "Buy my usual groceries but do not "
            "spend more than ₹2,000."
        ),
        (
            "Order dinner for me under ₹800."
        ),
        (
            "Buy some groceries for me."
        ),
    ]

    for example in examples:

        print("\nInstruction:")
        print(example)

        print("\nParsed:")
        print(
            parse_intent(example)
        )

        print("-" * 60)