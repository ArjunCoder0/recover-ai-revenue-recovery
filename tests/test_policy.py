"""Tests for recover.policy."""

import pytest
from recover.simulator import Case
from recover.policy import (
    ARMS,
    RETRY_ARMS,
    CONTACT_ARMS,
    DEFAULT_CONTROLS,
    validate_controls,
    is_quiet,
    defer_quiet,
    salary_delay,
    allowed_actions,
    check_violations,
)


def make_case(**kwargs):
    defaults = {
        "id": 1,
        "method": "card",
        "amount": 1000.0,
        "error_code": "INSUFFICIENT_FUNDS",
        "failed_at": 10,
        "salary_day": 15,
        "responsiveness": 0.5,
    }
    defaults.update(kwargs)
    return Case(**defaults)


def test_allowed_actions_returns_all_seven_arms():
    c = make_case()
    res = allowed_actions(c, now=10)
    assert set(res.keys()) == set(ARMS)
    assert len(res) == 7


def test_r1_hard_decline_blocks_all_retries():
    c = make_case(error_code="CARD_LOST_STOLEN")
    assert c.failure_class == "HARD"
    res = allowed_actions(c, now=10)
    for arm in RETRY_ARMS:
        allowed, reason = res[arm]
        assert not allowed
        assert "hard decline" in reason.lower()
    # Non-retries can be allowed
    assert res["SEND_REMINDER"][0] is True
    assert res["PAYMENT_LINK"][0] is True
    assert res["STOP"][0] is True


def test_r2_upi_pre_debit_notification():
    c = make_case(method="upi_autopay", error_code="INSUFFICIENT_FUNDS")
    res = allowed_actions(c, now=24)
    # RETRY_2H is 2h delay < 24h notice -> blocked
    assert res["RETRY_2H"][0] is False
    assert "pre-debit" in res["RETRY_2H"][1].lower()
    # RETRY_24H is 24h delay >= 24h notice -> allowed
    assert res["RETRY_24H"][0] is True


def test_r3_max_retries():
    c = make_case(retries=4)
    res = allowed_actions(c, now=10, controls={"max_retries": 4})
    for arm in RETRY_ARMS:
        assert res[arm][0] is False
        assert "max retries" in res[arm][1].lower()


def test_r4_min_gap_delay_aware():
    now = 50
    # case last retried at now
    c = make_case(last_retry_at=now, retries=1)
    # Earliest execution of RETRY_2H is now + 2 = 52.
    # gap = 52 - 50 = 2h.
    # When min_retry_gap_h = 2: 2 >= 2 -> allowed!
    res = allowed_actions(c, now=now, controls={"min_retry_gap_h": 2})
    assert res["RETRY_2H"][0] is True

    # When min_retry_gap_h = 5: 2 < 5 -> blocked!
    res2 = allowed_actions(c, now=now, controls={"min_retry_gap_h": 5})
    assert res2["RETRY_2H"][0] is False
    assert "minimum gap" in res2["RETRY_2H"][1].lower()


def test_r5_contact_cap():
    c = make_case(messages=2)
    res = allowed_actions(c, now=10, controls={"contact_cap": 2})
    for arm in CONTACT_ARMS:
        assert res[arm][0] is False
        assert "contact cap" in res[arm][1].lower()


def test_r7_window_exceeded():
    # Failed at hour 0, now is day 31 (hour 31*24)
    c = make_case(failed_at=0)
    now = 31 * 24
    res = allowed_actions(c, now=now, controls={"recovery_window_days": 30})
    for arm in ARMS:
        if arm == "STOP":
            assert res[arm][0] is True
        else:
            assert res[arm][0] is False
            assert "recovery window" in res[arm][1].lower()


def test_r8_escalation():
    # Low value: blocked
    c_low = make_case(amount=500.0, history=[{"kind": "action"}])
    res_low = allowed_actions(c_low, now=10, controls={"escalate_above": 2500})
    assert res_low["ESCALATE"][0] is False
    assert "below escalation threshold" in res_low["ESCALATE"][1].lower()

    # High value but no attempts: blocked
    c_high_no_hist = make_case(amount=5000.0, history=[])
    res_no_hist = allowed_actions(
        c_high_no_hist, now=10, controls={"escalate_above": 2500}
    )
    assert res_no_hist["ESCALATE"][0] is False
    assert "no automated attempt" in res_no_hist["ESCALATE"][1].lower()

    # High value with attempt: allowed
    c_high_with_hist = make_case(amount=5000.0, history=[{"kind": "action"}])
    res_ok = allowed_actions(
        c_high_with_hist, now=10, controls={"escalate_above": 2500}
    )
    assert res_ok["ESCALATE"][0] is True


def test_is_quiet_and_defer_quiet():
    quiet = (21, 9)  # 21:00 to 09:00 (wrap around)
    assert is_quiet(23, quiet) is True
    assert is_quiet(3, quiet) is True
    assert is_quiet(12, quiet) is False
    assert is_quiet(9, quiet) is False
    assert is_quiet(21, quiet) is True

    # 23:00 -> 09:00 next day (hour 23 + 10 = 33, 33 % 24 = 9)
    assert defer_quiet(23, quiet) == 33
    # 03:00 -> 09:00 same day (hour 3 + 6 = 9)
    assert defer_quiet(3, quiet) == 9
    # 12:00 -> unchanged
    assert defer_quiet(12, quiet) == 12

    # Non-wrap quiet hours: e.g. 13 to 15
    quiet_midday = (13, 15)
    assert is_quiet(14, quiet_midday) is True
    assert is_quiet(12, quiet_midday) is False
    assert defer_quiet(14, quiet_midday) == 15


def test_salary_delay():
    # Day 1, salary day 5
    c = make_case(salary_day=5)
    now = 12  # Day 1, 12:00
    delay = salary_delay(c, now)
    assert delay >= 2
    landing = now + delay
    # Hour of day must be 10:00
    assert landing % 24 == 10
    # Day of month must be salary day
    assert ((landing // 24) % 28 + 1) == 5

    # If salary day has passed in current month, wrap to next
    c_past = make_case(salary_day=2)
    now_past = 3 * 24 + 12  # Day 4
    delay_past = salary_delay(c_past, now_past)
    landing_past = now_past + delay_past
    assert landing_past % 24 == 10
    assert ((landing_past // 24) % 28 + 1) == 2


def test_check_violations_auditor():
    controls = DEFAULT_CONTROLS
    c = make_case()

    # Legal action -> no violations
    assert (
        check_violations(
            c,
            arm="RETRY_24H",
            decided_at=10,
            executed_at=34,
            controls=controls,
        )
        == []
    )

    # Retry on hard decline
    c_hard = make_case(error_code="CARD_LOST_STOLEN")
    v_hard = check_violations(
        c_hard,
        arm="RETRY_24H",
        decided_at=10,
        executed_at=34,
        controls=controls,
    )
    assert "retry_on_hard_decline" in v_hard

    # Max retries exceeded
    c_max = make_case(retries=4)
    v_max = check_violations(
        c_max,
        arm="RETRY_24H",
        decided_at=10,
        executed_at=34,
        controls=controls,
    )
    assert "max_retries_exceeded" in v_max

    # Min retry gap violated
    c_gap = make_case(last_retry_at=20)
    v_gap = check_violations(
        c_gap,
        arm="RETRY_2H",
        decided_at=20,
        executed_at=21,
        controls=controls,
    )
    assert "min_retry_gap" in v_gap

    # UPI notice violated
    c_upi = make_case(method="upi_autopay")
    v_upi = check_violations(
        c_upi,
        arm="RETRY_2H",
        decided_at=10,
        executed_at=12,
        controls=controls,
    )
    assert "upi_pre_debit_notice" in v_upi

    # Quiet hours contact violated
    v_quiet = check_violations(
        c,
        arm="SEND_REMINDER",
        decided_at=10,
        executed_at=23,
        controls=controls,
    )
    assert "quiet_hours" in v_quiet

    # Window violated
    c_old = make_case(failed_at=0)
    v_win = check_violations(
        c_old,
        arm="SEND_REMINDER",
        decided_at=35 * 24,
        executed_at=35 * 24 + 10,
        controls=controls,
    )
    assert "outside_recovery_window" in v_win


def test_validate_controls():
    sanitized = validate_controls(
        {"max_retries": "6", "contact_cap": "1", "escalate_above": "5000"}
    )
    assert sanitized["max_retries"] == 6
    assert sanitized["contact_cap"] == 1
    assert sanitized["escalate_above"] == 5000.0
    assert sanitized["recovery_window_days"] == 30  # default merged

    # Clamping
    clamped = validate_controls(
        {
            "max_retries": 99,
            "contact_cap": -5,
            "recovery_window_days": 100,
            "min_retry_gap_h": 0,
        }
    )
    assert clamped["max_retries"] == 8
    assert clamped["contact_cap"] == 0
    assert clamped["recovery_window_days"] == 60
    assert clamped["min_retry_gap_h"] == 1

    # Raises on non-numeric
    with pytest.raises(ValueError):
        validate_controls({"max_retries": "invalid"})
    with pytest.raises(ValueError):
        validate_controls({"escalate_above": -10})
    with pytest.raises(ValueError):
        validate_controls({"quiet_hours": "invalid"})
