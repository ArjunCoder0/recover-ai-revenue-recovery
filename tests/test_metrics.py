"""Tests for recover.metrics."""

import pandas as pd
from recover.simulator import generate, CLASSES
from recover.engine import run
from recover.metrics import summarize, by_class, confidence


def test_r31_summarize_empty():
    res = summarize([], [])
    assert res["cases"] == 0
    assert res["rate"] == 0.0
    assert res["net"] == 0.0
    assert res["violations"] == 0


def test_r32_net_math():
    cases = generate(50, seed=42)
    run_cases, audit, _ = run(cases, policy="smart", seed=1)
    res = summarize(run_cases, audit)
    expected_net = round(res["recovered"] - res["cost"], 2)
    assert res["net"] == expected_net


def test_r33_by_class_structure():
    cases = generate(100, seed=42)
    run_cases, _, _ = run(cases, policy="smart", seed=1)
    df = by_class(run_cases)
    assert list(df.index) == CLASSES
    expected_cols = {
        "cases",
        "recovered",
        "recovery_rate",
        "amount_at_risk",
        "amount_recovered",
    }
    assert expected_cols.issubset(set(df.columns))
    # Sum of cases in df equals total cases
    assert df["cases"].sum() == len(run_cases)


def test_r34_confidence_schema():
    df = confidence(50, seeds=range(2))
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    required_cols = {
        "seed",
        "smart_rate",
        "naive_rate",
        "lift_pp",
        "smart_net",
        "naive_net",
        "net_lift",
        "smart_violations",
        "naive_violations",
        "smart_retries",
        "naive_retries",
    }
    assert required_cols.issubset(set(df.columns))
