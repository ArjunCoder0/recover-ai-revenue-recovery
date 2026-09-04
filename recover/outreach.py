"""Customer outreach drafting and strict guardrails.

Deterministic templates first. Optional LLM rewrite strictly confined to tone/wording,
guaranteed not to alter actions, amounts, or terms, with full graceful fallback.
"""

import os
import re
from typing import Tuple
from .simulator import Case

TEMPLATES = {
    "SEND_REMINDER": (
        "Hi! Your payment of ₹{amount} could not be processed. "
        "We'll retry shortly — please ensure funds are available. "
        "Reply STOP to opt out."
    ),
    "PAYMENT_LINK": (
        "Hi! Your payment of ₹{amount} failed. "
        "Pay securely via UPI in one tap: <razorpay-payment-link>. "
        "Reply STOP to opt out."
    ),
}

BANNED = [
    "discount",
    "offer",
    "% off",
    "cashback",
    "free",
    "penalty",
    "legal",
    "court",
    "blacklist",
    "last chance",
    "final warning",
    "urgent",
    "immediately",
    "within 24 hours",
    "suspend",
    "terminate",
]


def validate_rewrite(
    original: str, rewritten: str, amount_str: str
) -> Tuple[bool, str]:
    """Validates an AI-rewritten outreach message against strict guardrail rules."""
    if not rewritten or not rewritten.strip():
        return False, "empty message"

    if amount_str not in rewritten:
        return False, f"missing amount ₹{amount_str}"

    if "STOP" not in rewritten:
        return False, "missing opt-out clause 'Reply STOP to opt out.'"

    if "<razorpay-payment-link>" in original:
        if "<razorpay-payment-link>" not in rewritten:
            return False, "missing '<razorpay-payment-link>' placeholder"

    words = rewritten.strip().split()
    if len(words) > 80:
        return False, f"exceeded 80 words ({len(words)} words)"

    lower = rewritten.lower()
    for b in BANNED:
        if b in lower:
            return False, f"contains banned term: '{b}'"

    # Ensure no unauthorized currency amounts exist
    matches = re.finditer(r"₹\s?\d[\d,]*(\.\d+)?", rewritten)
    expected = amount_str.replace(",", "")
    for m in matches:
        val_str = m.group(0).replace("₹", "").replace(" ", "").replace(",", "")
        try:
            if float(val_str) != float(expected):
                return False, f"unauthorized currency amount found: {m.group(0)}"
        except ValueError:
            return False, f"malformed currency amount found: {m.group(0)}"

    return True, "ok"


def _llm_rewrite(template: str, amount_str: str, timeout_s: int = 8) -> str:
    """Invokes Gemini 1.5 Flash to rewrite customer communication."""
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY", "")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = (
        f"Rewrite the following customer message in a warm, concise tone (≤60 words). "
        f"You MUST keep the exact amount ₹{amount_str}, keep any `<razorpay-payment-link>` placeholder verbatim, "
        f"and keep the sentence 'Reply STOP to opt out.' "
        f"You MUST NOT mention discounts, offers, penalties, legal action, deadlines, or urgency. "
        f"Return only the message.\n\n{template}"
    )
    response = model.generate_content(prompt, request_options={"timeout": timeout_s})
    return response.text.strip()


def draft(
    case: Case, arm: str, use_llm: bool = False, timeout_s: int = 8
) -> Tuple[str, str]:
    """Drafts customer outreach with multi-tier fallback and guardrail validation."""
    if arm not in TEMPLATES:
        return "", "n/a"

    amount_str = f"{case.amount:.2f}"
    template = TEMPLATES[arm].format(amount=amount_str)

    if not use_llm:
        return template, "template (deterministic mode)"

    if not os.environ.get("GEMINI_API_KEY"):
        return template, "template (no API key)"

    try:
        rewritten = _llm_rewrite(template, amount_str, timeout_s)
    except Exception as e:
        return template, f"template (LLM unavailable: {type(e).__name__})"

    ok, reason = validate_rewrite(template, rewritten, amount_str)
    if not ok:
        return template, f"template (LLM output failed guardrail: {reason})"

    return rewritten, "gemini-1.5-flash (guardrail passed)"
