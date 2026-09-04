"""Tests for recover.engine."""

import pytest
from recover.simulator import Case, generate
from recover.policy import DEFAULT_CONTROLS
from recover.engine import run, execute_human_action, salary_delay, defer_quiet


def test_reexports():
    assert callable(salary_delay)
    assert callable(defer_quiet)


def test_r24_all_cases_terminal():
    cases = generate(300, seed=42)
    controls = dict(DEFAULT_CONTROLS, max_retries=8, contact_cap=5)

    smart_cases, smart_audit, _ = run(cases, controls=controls, policy="smart", seed=1)
    for c in smart_cases:
        assert c.state in {"RECOVERED", "EXHAUSTED", "ESCALATED"}

    naive_cases, naive_audit, _ = run(cases, controls=controls, policy="naive", seed=1)
    for c in naive_cases:
        assert c.state in {"RECOVERED", "EXHAUSTED"}


def test_r25_smart_zero_violations():
    controls = DEFAULT_CONTROLS
    for seed in range(1, 6):
        cases = generate(200, seed=100 + seed)
        _, audit, _ = run(cases, controls=controls, policy="smart", seed=seed)
        total_violations = sum(e["violation"] for e in audit)
        assert total_violations == 0, f"Seed {seed} had {total_violations} smart violations!"


def test_r26_naive_violations_exist():
    cases = generate(300, seed=42)
    _, audit, _ = run(cases, policy="naive", seed=1)
    total_violations = sum(e["violation"] for e in audit)
    # Naive retries hard declines, so violations MUST exist
    assert total_violations > 0
    hard_violations = [
        e for e in audit if "retry_on_hard_decline" in e["violation_reasons"]
    ]
    assert len(hard_violations) > 0


def test_r27_audit_schema_and_integrity():
    cases = generate(50, seed=42)
    run_cases, audit, _ = run(cases, policy="smart", seed=1)

    # Audit count equals sum of history lengths
    assert len(audit) == sum(len(c.history) for c in run_cases)

    # Monotonically increasing seq
    seqs = [e["seq"] for e in audit]
    assert seqs == sorted(seqs)

    required_keys = {
        "seq",
        "kind",
        "policy",
        "decided_at",
        "executed_at",
        "case_id",
        "arm",
        "failure_class",
        "method",
        "amount",
        "success",
        "violation",
        "violation_reasons",
        "deferred",
        "rationale",
    }

    for e in audit:
        assert required_keys.issubset(set(e.keys()))
        assert e["kind"] in {"action", "terminal", "human"}


def test_r28_input_cases_not_mutated():
    cases = generate(50, seed=42)
    initial_states = [c.state for c in cases]
    initial_retries = [c.retries for c in cases]

    run(cases, policy="smart", seed=1)
    assert [c.state for c in cases] == initial_states
    assert [c.retries for c in cases] == initial_retries


def test_r29_quiet_hour_deferral():
    # Construct a case that forces a contact arm into quiet hours
    # quiet_hours is (21, 9). SEND_REMINDER has delay 24h.
    # If decided_at is 23:00, raw executed_at is 23:00 next day (quiet!).
    # defer_quiet will defer it to 09:00 following day, setting deferred=True.
    c = Case(
        id=999,
        method="card",
        amount=1000.0,
        error_code="CARD_LOST_STOLEN",  # HARD -> retries blocked, only contact arms allowed
        failed_at=23,
        salary_day=15,
        responsiveness=0.8,
    )
    # Force contact arms allowed, no retries
    controls = dict(DEFAULT_CONTROLS, max_retries=0)
    run_cases, audit, _ = run([c], controls=controls, policy="smart", seed=1)

    contact_entries = [e for e in audit if e["arm"] in {"SEND_REMINDER", "PAYMENT_LINK"}]
    assert len(contact_entries) > 0
    first_contact = contact_entries[0]
    # Scheduled from hour 23, with delay 24/48 -> 23:00 which is quiet -> deferred to 09:00
    assert first_contact["deferred"] is True
    assert first_contact["executed_at"] % 24 == 9


def test_r30_execute_human_action():
    cases = generate(100, seed=42)
    # Run smart with threshold to generate some escalated cases
    controls = dict(DEFAULT_CONTROLS, escalate_above=2000)
    smart_cases, audit, bandit = run(cases, controls=controls, policy="smart", seed=1)

    escalated = [c for c in smart_cases if c.state == "ESCALATED"]
    if not escalated:
        # Lower threshold to get at least one
        controls["escalate_above"] = 500
        smart_cases, audit, bandit = run(cases, controls=controls, policy="smart", seed=1)
        escalated = [c for c in smart_cases if c.state == "ESCALATED"]

    assert len(escalated) > 0
    target_case = escalated[0]
    initial_history_len = len(target_case.history)

    entry = execute_human_action(
        target_case,
        arm="PAYMENT_LINK",
        controls=controls,
        audit=audit,
        bandit=bandit,
        seed=42,
    )

    assert target_case.state in {"RECOVERED", "EXHAUSTED"}
    assert len(target_case.history) == initial_history_len + 1
    assert entry["kind"] == "human"
    assert entry["arm"] == "PAYMENT_LINK"
    assert entry == audit[-1]

    # Unsupported action raises ValueError
    with pytest.raises(ValueError):
        execute_human_action(
            target_case,
            arm="RETRY_2H",
            controls=controls,
            audit=audit,
            bandit=bandit,
            seed=42,
        )
