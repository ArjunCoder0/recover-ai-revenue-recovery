"""Tests for enhanced AI visibility, statistics, financial efficiency, and HITL features."""

import pytest
from recover.simulator import Case, generate
from recover.decide import Bandit, decide
from recover.engine import run, execute_human_action
from recover.metrics import summarize
from recover.policy import DEFAULT_CONTROLS


def test_bandit_stats_and_uncertainty():
    bandit = Bandit(seed=42)
    st = bandit.stats("SOFT", "RETRY_SALARY_DAY")
    assert "prior_alpha" in st
    assert "prior_beta" in st
    assert "prior_mean" in st
    assert "posterior_mean" in st
    assert "observations" in st
    assert "successes" in st
    assert "failures" in st
    assert "uncertainty" in st
    assert st["observations"] == 0
    assert st["successes"] == 0
    assert st["failures"] == 0
    assert st["uncertainty"] > 0

    # After update
    bandit.update("SOFT", "RETRY_SALARY_DAY", 1)
    st_after = bandit.stats("SOFT", "RETRY_SALARY_DAY")
    assert st_after["observations"] == 1
    assert st_after["successes"] == 1
    assert st_after["failures"] == 0
    assert st_after["posterior_mean"] > st["prior_mean"]


def test_bandit_snapshot_enriched_fields():
    bandit = Bandit(seed=42)
    bandit.update("TRANSIENT", "RETRY_2H", 1)
    bandit.update("TRANSIENT", "RETRY_2H", 0)
    snap = bandit.snapshot()
    row = next(r for r in snap if r["class"] == "TRANSIENT" and r["arm"] == "RETRY_2H")
    assert row["observations"] == 2
    assert row["successes"] == 1
    assert row["failures"] == 1
    assert "uncertainty" in row
    assert row["uncertainty"] > 0


def test_decide_stores_selected_stats():
    c = Case(
        id=1,
        method="card",
        amount=1000.0,
        error_code="INSUFFICIENT_FUNDS",
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
    )
    bandit = Bandit(seed=42)
    chosen, rationale = decide(c, now=0, bandit=bandit)
    assert chosen in ["RETRY_2H", "RETRY_24H", "RETRY_SALARY_DAY", "SEND_REMINDER", "PAYMENT_LINK"]
    assert "selected_stats" in rationale
    sel = rationale["selected_stats"]
    assert sel is not None
    assert sel["arm"] == chosen
    assert "sampled_p" in sel
    assert "posterior_mean" in sel
    assert "uncertainty" in sel
    assert "action_cost" in sel
    assert "expected_recovery" in sel
    assert "expected_net_value" in sel
    assert sel["expected_net_value"] > 0


def test_financial_efficiency_metrics():
    cases = generate(50, seed=42)
    run_cases, audit, _ = run(cases, policy="smart", seed=1)
    metrics = summarize(run_cases, audit)
    assert "revenue_per_attempt" in metrics
    assert "cost_per_recovered_inr" in metrics
    assert metrics["revenue_per_attempt"] > 0
    assert metrics["cost_per_recovered_inr"] >= 0


def test_hitl_reject_action():
    c = Case(
        id=99,
        method="card",
        amount=5000.0,
        error_code="INSUFFICIENT_FUNDS",
        failed_at=0,
        salary_day=10,
        responsiveness=0.5,
        state="ESCALATED",
        history=[{"kind": "action", "decided_at": 10, "executed_at": 12}],
    )
    audit = []
    bandit = Bandit(seed=1)
    entry = execute_human_action(
        c,
        arm="STOP",
        controls=DEFAULT_CONTROLS,
        audit=audit,
        bandit=bandit,
        seed=1,
    )
    assert c.state == "EXHAUSTED"
    assert entry["arm"] == "STOP"
    assert entry["kind"] == "human"
    assert entry["success"] is False
    assert "rejected" in entry["rationale"]["note"].lower()
    assert len(audit) == 1
