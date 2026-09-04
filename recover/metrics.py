"""Benchmark metrics and comparative evaluation for RECOVER."""

from typing import List, Dict, Any, Iterable
import pandas as pd
from .simulator import Case, generate, CLASSES
from .policy import RETRY_ARMS, CONTACT_ARMS, DEFAULT_CONTROLS
from .engine import run


def summarize(cases: List[Case], audit: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes summary recovery and financial metrics for a completed simulation run."""
    cases_n = len(cases)
    at_risk = round(sum(c.amount for c in cases), 2)
    recovered_cases = sum(1 for c in cases if c.state == "RECOVERED")
    recovered = round(sum(c.amount for c in cases if c.state == "RECOVERED"), 2)
    rate = (recovered_cases / cases_n) if cases_n > 0 else 0.0

    retries = sum(
        1
        for e in audit
        if e.get("kind") in {"action", "human"} and e.get("arm") in RETRY_ARMS
    )
    messages = sum(
        1
        for e in audit
        if e.get("kind") in {"action", "human"} and e.get("arm") in CONTACT_ARMS
    )
    cost = round(sum(c.cost for c in cases), 2)
    net = round(recovered - cost, 2)
    violations = sum(e.get("violation", 0) for e in audit)
    escalated = sum(1 for c in cases if c.state == "ESCALATED")
    exhausted = sum(1 for c in cases if c.state == "EXHAUSTED")

    revenue_per_attempt = round(recovered / retries, 2) if retries > 0 else 0.0
    cost_per_recovered_inr = round(cost / recovered, 4) if recovered > 0 else 0.0

    return {
        "cases": cases_n,
        "at_risk": at_risk,
        "recovered_cases": recovered_cases,
        "recovered": recovered,
        "rate": rate,
        "retries": retries,
        "messages": messages,
        "cost": cost,
        "net": net,
        "violations": violations,
        "escalated": escalated,
        "exhausted": exhausted,
        "revenue_per_attempt": revenue_per_attempt,
        "cost_per_recovered_inr": cost_per_recovered_inr,
    }


def by_class(cases: List[Case]) -> pd.DataFrame:
    """Computes breakdown metrics per failure class in standard order."""
    data: Dict[str, Dict[str, Any]] = {
        fc: {
            "cases": 0,
            "recovered": 0,
            "recovery_rate": 0.0,
            "amount_at_risk": 0.0,
            "amount_recovered": 0.0,
        }
        for fc in CLASSES
    }

    for c in cases:
        fc = c.failure_class
        if fc not in data:
            continue
        data[fc]["cases"] += 1
        data[fc]["amount_at_risk"] += c.amount
        if c.state == "RECOVERED":
            data[fc]["recovered"] += 1
            data[fc]["amount_recovered"] += c.amount

    for fc in CLASSES:
        n = data[fc]["cases"]
        r = data[fc]["recovered"]
        data[fc]["recovery_rate"] = (r / n) if n > 0 else 0.0
        data[fc]["amount_at_risk"] = round(data[fc]["amount_at_risk"], 2)
        data[fc]["amount_recovered"] = round(data[fc]["amount_recovered"], 2)

    df = pd.DataFrame.from_dict(data, orient="index")
    df.index.name = "failure_class"
    return df.reindex(CLASSES)


def confidence(
    n: int,
    controls: Dict[str, Any] = DEFAULT_CONTROLS,
    seeds: Iterable[int] = range(10),
) -> pd.DataFrame:
    """Runs a multi-seed benchmark comparing smart vs naive policies."""
    rows = []
    for s in seeds:
        cases = generate(n, 1000 + s)
        smart_cases, smart_audit, _ = run(
            cases, controls=controls, policy="smart", seed=s
        )
        naive_cases, naive_audit, _ = run(
            cases, controls=controls, policy="naive", seed=s
        )

        sm = summarize(smart_cases, smart_audit)
        nm = summarize(naive_cases, naive_audit)

        rows.append(
            {
                "seed": s,
                "smart_rate": sm["rate"],
                "naive_rate": nm["rate"],
                "lift_pp": round(100.0 * (sm["rate"] - nm["rate"]), 2),
                "smart_net": sm["net"],
                "naive_net": nm["net"],
                "net_lift": round(sm["net"] - nm["net"], 2),
                "smart_violations": sm["violations"],
                "naive_violations": nm["violations"],
                "smart_retries": sm["retries"],
                "naive_retries": nm["retries"],
            }
        )

    return pd.DataFrame(rows)
