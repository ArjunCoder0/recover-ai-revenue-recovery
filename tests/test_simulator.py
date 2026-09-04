"""Tests for recover.simulator."""

import pytest
from recover.simulator import (
    generate,
    day_of_month,
    hidden_recovery_prob,
    Case,
    CODES,
    CLASSES,
    METHODS,
)


def test_reproducibility_same_seed():
    cases1 = generate(100, seed=42)
    cases2 = generate(100, seed=42)
    assert len(cases1) == 100
    assert len(cases2) == 100
    for c1, c2 in zip(cases1, cases2):
        assert c1.id == c2.id
        assert c1.method == c2.method
        assert c1.amount == c2.amount
        assert c1.error_code == c2.error_code
        assert c1.failed_at == c2.failed_at
        assert c1.salary_day == c2.salary_day
        assert c1.responsiveness == c2.responsiveness


def test_different_seeds_differ():
    cases1 = generate(50, seed=42)
    cases2 = generate(50, seed=99)
    amounts1 = [c.amount for c in cases1]
    amounts2 = [c.amount for c in cases2]
    assert amounts1 != amounts2


def test_no_incompatible_method_code_pairs():
    cases = generate(2000, seed=123)
    for c in cases:
        if c.error_code in {"MANDATE_PAUSED", "MANDATE_REVOKED", "UPI_TIMEOUT"}:
            assert c.method == "upi_autopay"
        if c.error_code in {"EXPIRED_CARD", "CARD_LOST_STOLEN"}:
            assert c.method == "card"


def test_field_ranges():
    cases = generate(200, seed=7)
    for c in cases:
        assert c.amount > 0
        assert 0 <= c.failed_at < 120
        assert 1 <= c.salary_day <= 28
        assert 0.0 <= c.responsiveness <= 1.0
        assert c.state == "OPEN"
        assert c.retries == 0
        assert c.messages == 0
        assert c.last_retry_at == -999
        assert c.recovered_at == -1
        assert c.failure_class in CLASSES


def test_edge_cases_n():
    assert generate(0) == []
    with pytest.raises(ValueError):
        generate(-1)


def test_hidden_recovery_prob_bounds_and_hard_rules():
    cases = generate(100, seed=42)
    actions = [
        "RETRY_2H",
        "RETRY_24H",
        "RETRY_SALARY_DAY",
        "SEND_REMINDER",
        "PAYMENT_LINK",
        "STOP",
    ]
    for c in cases:
        for a in actions:
            p = hidden_recovery_prob(c, a, at_hour=c.failed_at + 2)
            assert 0.0 <= p <= 1.0
            if c.failure_class == "HARD" and a.startswith("RETRY"):
                assert p == 0.0


def test_day_of_month():
    assert day_of_month(0) == 1
    assert day_of_month(23) == 1
    assert day_of_month(24) == 2
    assert day_of_month(27 * 24) == 28
    assert day_of_month(28 * 24) == 1
