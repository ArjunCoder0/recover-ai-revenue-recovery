"""Simulated world and domain models for RECOVER.

GROUND TRUTH of the simulated world. Only engine.run and engine.execute_human_action
may call hidden_recovery_prob or read case.responsiveness.
"""

from dataclasses import dataclass, field
import random
from typing import List

METHODS = ["card", "upi_autopay", "netbanking"]
CLASSES = ["SOFT", "TRANSIENT", "ACTION_REQUIRED", "HARD"]

CODES = {
    "INSUFFICIENT_FUNDS": "SOFT",
    "DO_NOT_HONOR": "SOFT",
    "ISSUER_UNAVAILABLE": "TRANSIENT",
    "UPI_TIMEOUT": "TRANSIENT",
    "EXPIRED_CARD": "ACTION_REQUIRED",
    "MANDATE_PAUSED": "ACTION_REQUIRED",
    "AUTH_TIMEOUT": "ACTION_REQUIRED",
    "MANDATE_REVOKED": "HARD",
    "CARD_LOST_STOLEN": "HARD",
    "RISK_DECLINE": "HARD",
}

WEIGHTS = [0.34, 0.12, 0.10, 0.08, 0.07, 0.06, 0.05, 0.06, 0.06, 0.06]


@dataclass
class Case:
    """Represents a failed payment case.
    
    Note on hidden vs observable variables:
    - responsiveness is HIDDEN: only hidden_recovery_prob may read it.
    - salary_day is an observable estimate (e.g. inferred from prior history).
    """

    id: int
    method: str
    amount: float
    error_code: str
    failed_at: int
    salary_day: int
    responsiveness: float
    state: str = "OPEN"
    retries: int = 0
    messages: int = 0
    last_retry_at: int = -999
    recovered_at: int = -1
    cost: float = 0.0
    history: list = field(default_factory=list)

    @property
    def failure_class(self) -> str:
        return CODES[self.error_code]


def day_of_month(hour: int) -> int:
    """Returns day of month (1..28) for an integer simulation hour."""
    return (hour // 24) % 28 + 1


def generate(n: int, seed: int = 42) -> List[Case]:
    """Generates n synthetic payment failure cases deterministically."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return []

    rng = random.Random(seed)
    cases: List[Case] = []

    for i in range(n):
        method = rng.choices(METHODS, [0.45, 0.45, 0.10])[0]
        code = rng.choices(list(CODES.keys()), WEIGHTS)[0]

        # Method-compatibility repair (deterministic)
        if code in {"MANDATE_PAUSED", "MANDATE_REVOKED"} and method != "upi_autopay":
            code = "INSUFFICIENT_FUNDS"
        elif code in {"EXPIRED_CARD", "CARD_LOST_STOLEN"} and method != "card":
            code = "DO_NOT_HONOR"
        elif code == "UPI_TIMEOUT" and method != "upi_autopay":
            code = "ISSUER_UNAVAILABLE"

        amount = round(
            rng.choice([199, 299, 499, 999, 1499, 2999, 4999]) * rng.uniform(0.9, 1.3),
            2,
        )
        failed_at = rng.randint(0, 119)
        salary_day = rng.randint(1, 28)
        responsiveness = rng.random()

        cases.append(
            Case(
                id=i,
                method=method,
                amount=amount,
                error_code=code,
                failed_at=failed_at,
                salary_day=salary_day,
                responsiveness=responsiveness,
            )
        )

    return cases


def hidden_recovery_prob(case: Case, action: str, at_hour: int) -> float:
    """GROUND TRUTH of the simulated world. Only engine.run and engine.execute_human_action may call this."""
    fc = case.failure_class
    r = case.responsiveness
    since_salary = (day_of_month(at_hour) - case.salary_day) % 28

    if action.startswith("RETRY"):
        if fc == "HARD":
            return 0.0
        elif fc == "ACTION_REQUIRED":
            return 0.02
        elif fc == "TRANSIENT":
            return 0.75 if (at_hour - case.failed_at) >= 2 else 0.15
        elif fc == "SOFT":
            return 0.65 if since_salary <= 2 else 0.12
        else:
            return 0.0
    elif action == "SEND_REMINDER":
        base = {
            "HARD": 0.0,
            "TRANSIENT": 0.30,
            "SOFT": 0.25,
            "ACTION_REQUIRED": 0.35,
        }.get(fc, 0.0)
        return base * (0.4 + 0.6 * r)
    elif action == "PAYMENT_LINK":
        base = {
            "HARD": 0.25,
            "TRANSIENT": 0.50,
            "SOFT": 0.40,
            "ACTION_REQUIRED": 0.55,
        }.get(fc, 0.0)
        return base * (0.4 + 0.6 * r)
    else:
        return 0.0
