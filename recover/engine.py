"""Workflow execution engine, event queue, and audit trail for RECOVER.

Executes bounded state machines for smart and naive policies, logs every decision,
updates bandit beliefs online, and handles human-in-the-loop actions.
"""

import copy
import heapq
import random
from typing import List, Dict, Any, Tuple

from .simulator import Case, hidden_recovery_prob
from .policy import (
    COST,
    ACTION_DELAY_H,
    RETRY_ARMS,
    CONTACT_ARMS,
    DEFAULT_CONTROLS,
    validate_controls,
    check_violations,
    salary_delay,
    defer_quiet,
)
from .decide import Bandit, decide

# Re-export per Section O specification
__all__ = ["run", "execute_human_action", "salary_delay", "defer_quiet"]


def run(
    cases: List[Case],
    controls: Dict[str, Any] = DEFAULT_CONTROLS,
    policy: str = "smart",
    seed: int = 1,
) -> Tuple[List[Case], List[Dict[str, Any]], Bandit]:
    """Runs the payment recovery workflow simulation across a list of cases."""
    if policy not in {"smart", "naive"}:
        raise ValueError(f"Unknown policy: '{policy}'. Expected 'smart' or 'naive'.")

    controls = validate_controls(controls)
    cases_copy = copy.deepcopy(cases)
    by_id = {c.id: c for c in cases_copy}

    outcome_rng = random.Random(seed)
    bandit = Bandit(seed * 7 + 1)
    audit: List[Dict[str, Any]] = []
    seq = 0
    quiet = controls.get("quiet_hours", (21, 9))

    heap: List[Tuple[int, int, int]] = []
    for i, c in enumerate(cases_copy):
        heap.append((c.failed_at, i, c.id))
    heapq.heapify(heap)
    seq = len(cases_copy)

    while heap:
        now, _, cid = heapq.heappop(heap)
        case = by_id[cid]
        if case.state != "OPEN":
            continue

        fc = case.failure_class

        if policy == "smart":
            arm, rationale = decide(case, now, bandit, controls)
        else:
            arm = "RETRY_24H" if case.retries < 3 else "STOP"
            rationale = {
                "decided_at": now,
                "chosen": arm,
                "failure_class": fc,
                "note": (
                    "naive fixed schedule: retry every 24h ×3, "
                    "ignores decline code and policy"
                ),
            }

        if arm in {"ESCALATE", "STOP"}:
            case.state = "ESCALATED" if arm == "ESCALATE" else "EXHAUSTED"
            seq += 1
            entry = {
                "seq": seq,
                "kind": "terminal",
                "policy": policy,
                "decided_at": now,
                "executed_at": None,
                "case_id": case.id,
                "arm": arm,
                "failure_class": fc,
                "method": case.method,
                "amount": case.amount,
                "success": None,
                "violation": 0,
                "violation_reasons": [],
                "deferred": False,
                "rationale": rationale,
            }
            case.history.append(entry)
            audit.append(entry)
            continue

        if arm == "RETRY_SALARY_DAY":
            delay = salary_delay(case, now)
        else:
            delay = ACTION_DELAY_H[arm]

        at = now + delay
        deferred = False

        if arm in CONTACT_ARMS and policy == "smart":
            at2 = defer_quiet(at, quiet)
            deferred = (at2 != at)
            at = at2

        reasons = check_violations(case, arm, now, at, controls)
        violation = len(reasons)

        success = outcome_rng.random() < hidden_recovery_prob(case, arm, at)
        case.cost += COST[arm]

        if arm in RETRY_ARMS:
            case.retries += 1
            case.last_retry_at = at
        else:
            case.messages += 1

        seq += 1
        entry = {
            "seq": seq,
            "kind": "action",
            "policy": policy,
            "decided_at": now,
            "executed_at": at,
            "case_id": case.id,
            "arm": arm,
            "failure_class": fc,
            "method": case.method,
            "amount": case.amount,
            "success": success,
            "violation": violation,
            "violation_reasons": reasons,
            "deferred": deferred,
            "rationale": rationale,
        }
        case.history.append(entry)
        audit.append(entry)

        if policy == "smart":
            bandit.update(fc, arm, int(success))

        if success:
            case.state = "RECOVERED"
            case.recovered_at = at
        else:
            seq += 1
            heapq.heappush(heap, (at, seq, cid))

    return cases_copy, audit, bandit


def execute_human_action(
    case: Case,
    arm: str,
    controls: Dict[str, Any],
    audit: List[Dict[str, Any]],
    bandit: Bandit,
    seed: int,
) -> Dict[str, Any]:
    """Executes a human reviewer override action for an escalated case."""
    if arm not in {"PAYMENT_LINK", "STOP"}:
        raise ValueError(
            f"Unsupported human action: '{arm}'. Expected 'PAYMENT_LINK' or 'STOP'."
        )

    controls = validate_controls(controls)
    last_entry = case.history[-1] if case.history else None
    if last_entry and last_entry.get("executed_at") is not None:
        decided_at = last_entry["executed_at"]
    elif last_entry and last_entry.get("decided_at") is not None:
        decided_at = last_entry["decided_at"]
    else:
        decided_at = case.failed_at

    if arm == "STOP":
        case.state = "EXHAUSTED"
        seq = (audit[-1]["seq"] + 1) if audit else 1
        entry = {
            "seq": seq,
            "kind": "human",
            "policy": "smart",
            "decided_at": decided_at,
            "executed_at": None,
            "case_id": case.id,
            "arm": "STOP",
            "failure_class": case.failure_class,
            "method": case.method,
            "amount": case.amount,
            "success": False,
            "violation": 0,
            "violation_reasons": [],
            "deferred": False,
            "rationale": {
                "chosen": "STOP",
                "note": "Case manually rejected and closed by human reviewer.",
            },
        }
        case.history.append(entry)
        audit.append(entry)
        return entry

    # arm == "PAYMENT_LINK"
    quiet = controls.get("quiet_hours", (21, 9))
    raw_at = decided_at + ACTION_DELAY_H[arm]
    at = defer_quiet(raw_at, quiet)
    deferred = (at != raw_at)

    reasons = check_violations(case, arm, decided_at, at, controls)
    violation = len(reasons)

    outcome_rng = random.Random(seed + 10_000 + case.id)
    success = outcome_rng.random() < hidden_recovery_prob(case, arm, at)

    case.messages += 1
    case.cost += COST[arm]

    if success:
        case.state = "RECOVERED"
        case.recovered_at = at
    else:
        case.state = "EXHAUSTED"

    seq = (audit[-1]["seq"] + 1) if audit else 1
    entry = {
        "seq": seq,
        "kind": "human",
        "policy": "smart",
        "decided_at": decided_at,
        "executed_at": at,
        "case_id": case.id,
        "arm": arm,
        "failure_class": case.failure_class,
        "method": case.method,
        "amount": case.amount,
        "success": success,
        "violation": violation,
        "violation_reasons": reasons,
        "deferred": deferred,
        "rationale": {"chosen": arm, "note": "approved by human reviewer"},
    }

    case.history.append(entry)
    audit.append(entry)
    bandit.update(case.failure_class, arm, int(success))

    return entry
