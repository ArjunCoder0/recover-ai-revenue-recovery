"""Tests for recover.outreach."""

from recover.simulator import Case
from recover.outreach import draft, validate_rewrite, TEMPLATES, BANNED


def make_case(amount=499.0):
    return Case(
        id=1,
        method="card",
        amount=amount,
        error_code="INSUFFICIENT_FUNDS",
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
    )


def test_r35_draft_no_key_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    case = make_case(499.0)
    msg, mode = draft(case, "SEND_REMINDER", use_llm=True)
    assert "₹499.00" in msg
    assert "no API key" in mode


def test_r36_draft_deterministic_mode():
    case = make_case(1299.50)
    msg, mode = draft(case, "PAYMENT_LINK", use_llm=False)
    assert "₹1299.50" in msg
    assert "<razorpay-payment-link>" in msg
    assert mode == "template (deterministic mode)"


def test_r37_validate_rewrite_guardrails():
    original = TEMPLATES["PAYMENT_LINK"].format(amount="999.00")
    amount_str = "999.00"

    # Valid rewrite
    clean = (
        "Hello! Your payment of ₹999.00 was unsuccessful. "
        "You can complete it instantly here: <razorpay-payment-link>. "
        "Reply STOP to opt out."
    )
    ok, reason = validate_rewrite(original, clean, amount_str)
    assert ok is True
    assert reason == "ok"

    # Missing amount
    missing_amt = clean.replace("₹999.00", "your payment")
    ok, reason = validate_rewrite(original, missing_amt, amount_str)
    assert ok is False
    assert "missing amount" in reason

    # Missing STOP
    missing_stop = clean.replace("Reply STOP to opt out.", "")
    ok, reason = validate_rewrite(original, missing_stop, amount_str)
    assert ok is False
    assert "missing opt-out" in reason

    # Missing link placeholder
    missing_link = clean.replace("<razorpay-payment-link>", "http://pay.me")
    ok, reason = validate_rewrite(original, missing_link, amount_str)
    assert ok is False
    assert "missing '<razorpay-payment-link>'" in reason

    # Banned words
    for word in ["discount", "urgent", "penalty", "last chance"]:
        with_banned = clean + f" Claim your special {word}."
        ok, reason = validate_rewrite(original, with_banned, amount_str)
        assert ok is False
        assert "banned term" in reason

    # Altered / extra currency amount
    altered_amt = clean + " Late fee ₹50.00."
    ok, reason = validate_rewrite(original, altered_amt, amount_str)
    assert ok is False
    assert "unauthorized currency amount" in reason

    # Word count > 80
    long_msg = clean + " word" * 90
    ok, reason = validate_rewrite(original, long_msg, amount_str)
    assert ok is False
    assert "exceeded 80 words" in reason


def test_r38_llm_exception_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")

    def mock_fail(*args, **kwargs):
        raise ConnectionError("Network timeout")

    monkeypatch.setattr("recover.outreach._llm_rewrite", mock_fail)

    case = make_case(299.0)
    msg, mode = draft(case, "SEND_REMINDER", use_llm=True)
    assert "₹299.00" in msg
    assert "template (LLM unavailable: ConnectionError)" in mode
