"""Thompson Sampling decision engine with bounded action spaces and explainability.

Learns recovery probabilities per failure class and action arm online.
Fenced strictly by recover.policy. Contains no world-simulation or hidden variables.
"""

import math
import random
from typing import Dict, Tuple, List, Any, Optional
from .policy import (
    ARMS,
    COST,
    DEFAULT_CONTROLS,
    allowed_actions,
)

# Informed prior distributions (alpha, beta) over P(recover | class, arm)
PRIORS: Dict[Tuple[str, str], Tuple[float, float]] = {
    ("SOFT", "RETRY_2H"): (1, 8),
    ("SOFT", "RETRY_24H"): (2, 6),
    ("SOFT", "RETRY_SALARY_DAY"): (5, 3),
    ("SOFT", "SEND_REMINDER"): (2, 6),
    ("SOFT", "PAYMENT_LINK"): (3, 5),
    ("TRANSIENT", "RETRY_2H"): (6, 2),
    ("TRANSIENT", "RETRY_24H"): (5, 3),
    ("TRANSIENT", "RETRY_SALARY_DAY"): (3, 3),
    ("TRANSIENT", "SEND_REMINDER"): (2, 6),
    ("TRANSIENT", "PAYMENT_LINK"): (3, 4),
    ("ACTION_REQUIRED", "RETRY_2H"): (1, 20),
    ("ACTION_REQUIRED", "RETRY_24H"): (1, 20),
    ("ACTION_REQUIRED", "RETRY_SALARY_DAY"): (1, 20),
    ("ACTION_REQUIRED", "SEND_REMINDER"): (3, 5),
    ("ACTION_REQUIRED", "PAYMENT_LINK"): (4, 4),
    ("HARD", "SEND_REMINDER"): (1, 10),
    ("HARD", "PAYMENT_LINK"): (2, 6),
}

DEFAULT_PRIOR: Tuple[float, float] = (1, 3)


class Bandit:
    """Beta-Bernoulli Thompson Sampling bandit for online learning."""

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        self.post: Dict[Tuple[str, str], Tuple[float, float]] = {}
        self.counts: Dict[Tuple[str, str], int] = {}

    def params(self, fc: str, arm: str) -> Tuple[float, float]:
        """Returns the current (alpha, beta) parameters for (fc, arm)."""
        return self.post.get((fc, arm), PRIORS.get((fc, arm), DEFAULT_PRIOR))

    def sample(self, fc: str, arm: str) -> float:
        """Draws a random probability sample from Beta(alpha, beta)."""
        a, b = self.params(fc, arm)
        return self.rng.betavariate(a, b)

    def mean(self, fc: str, arm: str) -> float:
        """Returns the expected probability alpha / (alpha + beta)."""
        a, b = self.params(fc, arm)
        return a / (a + b)

    def update(self, fc: str, arm: str, success: int) -> None:
        """Updates belief with a binary observation (1 for recovered, 0 for failed)."""
        a, b = self.params(fc, arm)
        self.post[(fc, arm)] = (a + success, b + (1 - success))
        self.counts[(fc, arm)] = self.counts.get((fc, arm), 0) + 1

    def stats(self, fc: str, arm: str) -> Dict[str, Any]:
        """Returns comprehensive Bayesian statistics and uncertainty for (fc, arm)."""
        pa, pb = PRIORS.get((fc, arm), DEFAULT_PRIOR)
        a, b = self.params(fc, arm)
        obs = self.counts.get((fc, arm), 0)
        successes = int(round(a - pa))
        failures = int(round(b - pb))
        post_mean = a / (a + b)
        prior_mean = pa / (pa + pb)
        variance = (a * b) / (((a + b) ** 2) * (a + b + 1))
        uncertainty = math.sqrt(variance)
        return {
            "prior_alpha": pa,
            "prior_beta": pb,
            "prior_mean": prior_mean,
            "alpha": a,
            "beta": b,
            "posterior_mean": post_mean,
            "observations": obs,
            "successes": max(0, successes),
            "failures": max(0, failures),
            "uncertainty": uncertainty,
        }

    def snapshot(self) -> List[Dict[str, Any]]:
        """Returns a serializable snapshot of beliefs for inspection and UI."""
        rows = []
        classes = ["SOFT", "TRANSIENT", "ACTION_REQUIRED", "HARD"]
        arms = [
            "RETRY_2H",
            "RETRY_24H",
            "RETRY_SALARY_DAY",
            "SEND_REMINDER",
            "PAYMENT_LINK",
        ]

        for fc in classes:
            fc_arms = (
                arms if fc != "HARD" else ["SEND_REMINDER", "PAYMENT_LINK"]
            )
            for arm in fc_arms:
                st = self.stats(fc, arm)
                rows.append(
                    {
                        "class": fc,
                        "arm": arm,
                        "prior_alpha": st["prior_alpha"],
                        "prior_beta": st["prior_beta"],
                        "prior_mean": st["prior_mean"],
                        "alpha": st["alpha"],
                        "beta": st["beta"],
                        "posterior_mean": st["posterior_mean"],
                        "observations": st["observations"],
                        "successes": st["successes"],
                        "failures": st["failures"],
                        "uncertainty": st["uncertainty"],
                    }
                )
        return rows


def decide(
    case: Any,
    now: int,
    bandit: Bandit,
    controls: Dict[str, Any] = DEFAULT_CONTROLS,
) -> Tuple[str, Dict[str, Any]]:
    """Chooses the highest expected value action strictly permitted by policy."""
    allowed = allowed_actions(case, now, controls)
    fc = case.failure_class
    considered: List[Dict[str, Any]] = []

    executable_arms = [
        "RETRY_2H",
        "RETRY_24H",
        "RETRY_SALARY_DAY",
        "SEND_REMINDER",
        "PAYMENT_LINK",
    ]

    for arm in executable_arms:
        ok, why = allowed[arm]
        st = bandit.stats(fc, arm)
        if ok:
            p = bandit.sample(fc, arm)
            ev = p * case.amount - COST[arm]
            exp_rec = round(p * case.amount, 2)
        else:
            p = None
            ev = None
            exp_rec = None
        considered.append(
            {
                "arm": arm,
                "allowed": ok,
                "reason": why,
                "sampled_p": p,
                "cost": COST[arm],
                "ev": ev,
                "expected_recovery": exp_rec,
                "chosen": False,
                "posterior_mean": st["posterior_mean"],
                "prior_alpha": st["prior_alpha"],
                "prior_beta": st["prior_beta"],
                "posterior_alpha": st["alpha"],
                "posterior_beta": st["beta"],
                "observations": st["observations"],
                "successes": st["successes"],
                "failures": st["failures"],
                "uncertainty": st["uncertainty"],
            }
        )

    viable = [
        c
        for c in considered
        if c["allowed"] and c["ev"] is not None and c["ev"] > 0
    ]

    selected_stats = None

    if viable:
        best = max(viable, key=lambda c: c["ev"])
        chosen = best["arm"]
        fallback = None
        fallback_reason = None
        expected_p = best["sampled_p"]
        expected_value = best["ev"]
        selected_stats = {
            "arm": chosen,
            "sampled_p": best["sampled_p"],
            "posterior_mean": best["posterior_mean"],
            "prior_alpha": best["prior_alpha"],
            "prior_beta": best["prior_beta"],
            "posterior_alpha": best["posterior_alpha"],
            "posterior_beta": best["posterior_beta"],
            "observations": best["observations"],
            "successes": best["successes"],
            "failures": best["failures"],
            "uncertainty": best["uncertainty"],
            "action_cost": best["cost"],
            "expected_recovery": best["expected_recovery"],
            "expected_net_value": best["ev"],
        }
    elif allowed["ESCALATE"][0]:
        chosen = "ESCALATE"
        fallback = "ESCALATE"
        fallback_reason = "no allowed action with positive expected value; case qualifies for human review"
        expected_p = None
        expected_value = None
    else:
        chosen = "STOP"
        fallback = "STOP"
        fallback_reason = (
            "no allowed action with positive expected value; "
            + allowed["ESCALATE"][1]
        )
        expected_p = None
        expected_value = None

    for c in considered:
        if c["arm"] == chosen:
            c["chosen"] = True

    rationale = {
        "decided_at": now,
        "chosen": chosen,
        "failure_class": fc,
        "expected_p": expected_p,
        "expected_value": expected_value,
        "fallback": fallback,
        "fallback_reason": fallback_reason,
        "considered": considered,
        "selected_stats": selected_stats,
    }

    return chosen, rationale


def explain_rationale(rationale: Dict[str, Any], case: Any) -> List[str]:
    """Builds a human-readable explanation of the decision rationale."""
    lines = []
    fc = rationale.get("failure_class", case.failure_class)
    lines.append(f"{case.error_code} on {case.method} → class {fc}.")

    considered = rationale.get("considered", [])
    for c in considered:
        if not c["allowed"]:
            lines.append(f"{c['arm']} blocked — {c['reason']}.")

    chosen = rationale.get("chosen")
    if not rationale.get("fallback"):
        ev = rationale.get("expected_value", 0.0)
        p = rationale.get("expected_p", 0.0)
        cost = COST.get(chosen, 0.0)
        lines.append(
            f"{chosen} selected — highest expected value ₹{ev:,.0f} "
            f"(sampled P(recover)={p:.0%}, cost ₹{cost})."
        )
    else:
        reason = rationale.get("fallback_reason", "")
        lines.append(f"{chosen} selected — {reason}.")

    for c in considered:
        if c["allowed"] and c["arm"] != chosen:
            ev = c.get("ev")
            if ev is not None:
                lines.append(f"{c['arm']} allowed but ranked lower (EV ₹{ev:,.0f}).")

    return lines
