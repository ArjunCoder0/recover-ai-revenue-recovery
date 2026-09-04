"""Tests for recover.decide."""

import json
import random
from recover.simulator import Case, generate
from recover.policy import allowed_actions, DEFAULT_CONTROLS
from recover.decide import Bandit, decide, explain_rationale


def test_invariant_chosen_arm_always_allowed():
    rng = random.Random(42)
    bandit = Bandit(seed=123)
    cases = generate(50, seed=42)

    for case in cases:
        for _ in range(20):
            now = rng.randint(0, 500)
            controls = {
                "max_retries": rng.randint(0, 5),
                "contact_cap": rng.randint(0, 3),
                "escalate_above": rng.choice([500.0, 2500.0, 10000.0]),
                "recovery_window_days": rng.randint(5, 30),
            }
            allowed = allowed_actions(case, now, controls)
            chosen, rationale = decide(case, now, bandit, controls)
            # The chosen arm MUST be marked allowed by policy
            assert allowed[chosen][0] is True, f"Arm {chosen} chosen but was blocked: {allowed[chosen]}"
            # Must be valid json
            json_str = json.dumps(rationale, default=str)
            assert len(json_str) > 0


def test_ev_negative_falls_back_to_stop():
    bandit = Bandit(seed=42)
    # Amount is ₹1.0, all action costs >= ₹0.5 and P <= 1.0 -> EV could be negative
    # With costs = 3.0 and 1.5, ev = p*1 - 3.0 < 0
    # Amount ₹1 < escalate threshold ₹2500 -> ESCALATE blocked -> STOP chosen
    c = Case(
        id=1,
        method="card",
        amount=1.0,
        error_code="INSUFFICIENT_FUNDS",
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
    )
    chosen, rationale = decide(c, now=0, bandit=bandit)
    assert chosen == "STOP"
    assert rationale["fallback"] == "STOP"


def test_high_value_no_viable_escalates():
    bandit = Bandit(seed=42)
    # High value ₹10,000, but all executables blocked (max_retries=0, contact_cap=0)
    # Case has history so escalation rule len(history) >= 1 passes
    c = Case(
        id=1,
        method="card",
        amount=10000.0,
        error_code="INSUFFICIENT_FUNDS",
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
        history=[{"kind": "action"}],
    )
    controls = dict(DEFAULT_CONTROLS, max_retries=0, contact_cap=0, escalate_above=2500)
    chosen, rationale = decide(c, now=0, bandit=bandit, controls=controls)
    assert chosen == "ESCALATE"
    assert rationale["fallback"] == "ESCALATE"


def test_bandit_learning_updates():
    bandit = Bandit(seed=42)
    initial_mean = bandit.mean("SOFT", "RETRY_2H")
    assert bandit.counts.get(("SOFT", "RETRY_2H"), 0) == 0

    # 10 successes
    for _ in range(10):
        bandit.update("SOFT", "RETRY_2H", success=1)
    higher_mean = bandit.mean("SOFT", "RETRY_2H")
    assert higher_mean > initial_mean
    assert bandit.counts[("SOFT", "RETRY_2H")] == 10

    # 20 failures
    for _ in range(20):
        bandit.update("SOFT", "RETRY_2H", success=0)
    lower_mean = bandit.mean("SOFT", "RETRY_2H")
    assert lower_mean < higher_mean
    assert bandit.counts[("SOFT", "RETRY_2H")] == 30


def test_reproducibility_same_seed():
    c = Case(
        id=1,
        method="card",
        amount=1000.0,
        error_code="INSUFFICIENT_FUNDS",
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
    )
    b1 = Bandit(seed=99)
    b2 = Bandit(seed=99)

    decisions1 = [decide(c, now=i * 2, bandit=b1)[0] for i in range(20)]
    decisions2 = [decide(c, now=i * 2, bandit=b2)[0] for i in range(20)]
    assert decisions1 == decisions2


def test_explain_rationale_contents():
    c = Case(
        id=1,
        method="upi_autopay",
        amount=1000.0,
        error_code="CARD_LOST_STOLEN",  # Note: method-repaired in generate, but tested directly
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
    )
    bandit = Bandit(seed=42)
    chosen, rationale = decide(c, now=0, bandit=bandit)
    lines = explain_rationale(rationale, c)
    assert any("CARD_LOST_STOLEN" in l for l in lines)
    # Check that blocked retries are explained
    assert any("RETRY_2H blocked" in l for l in lines)
    assert any("selected" in l for l in lines)


def test_bandit_snapshot():
    bandit = Bandit(seed=42)
    bandit.update("SOFT", "RETRY_2H", 1)
    snapshot = bandit.snapshot()
    assert len(snapshot) > 0
    row = next(r for r in snapshot if r["class"] == "SOFT" and r["arm"] == "RETRY_2H")
    assert row["observations"] == 1
    assert "prior_mean" in row
    assert "posterior_mean" in row
