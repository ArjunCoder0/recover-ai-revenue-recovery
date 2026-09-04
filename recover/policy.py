"""Deterministic policy engine for RECOVER.

Fences legal actions using merchant controls, network rules, and regulatory constraints.
Contains no randomness, no bandit, and no LLM.
"""

from typing import Dict, Tuple, List, Any
from .simulator import day_of_month, Case

ARMS = [
    "RETRY_2H",
    "RETRY_24H",
    "RETRY_SALARY_DAY",
    "SEND_REMINDER",
    "PAYMENT_LINK",
    "ESCALATE",
    "STOP",
]

RETRY_ARMS = {"RETRY_2H", "RETRY_24H", "RETRY_SALARY_DAY"}
CONTACT_ARMS = {"SEND_REMINDER", "PAYMENT_LINK"}

COST = {
    "RETRY_2H": 3.0,
    "RETRY_24H": 3.0,
    "RETRY_SALARY_DAY": 3.0,
    "SEND_REMINDER": 0.5,
    "PAYMENT_LINK": 1.5,
    "ESCALATE": 0.0,
    "STOP": 0.0,
}

ACTION_DELAY_H = {
    "RETRY_2H": 2,
    "RETRY_24H": 24,
    "SEND_REMINDER": 24,
    "PAYMENT_LINK": 48,
}

MIN_SALARY_DELAY_H = 2
MIN_ATTEMPTS_BEFORE_ESCALATION = 1

DEFAULT_CONTROLS = {
    "max_retries": 4,  # int 0..8
    "min_retry_gap_h": 2,  # int >= 1
    "contact_cap": 2,  # int 0..5
    "quiet_hours": (21, 9),  # (start_hour, end_hour)
    "recovery_window_days": 30,  # int 3..45
    "escalate_above": 2500,  # float >= 0
    "pre_debit_notice_h": 24,  # int >= 0
}


def validate_controls(controls: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a sanitized, clamped copy of controls merged with defaults."""
    if not isinstance(controls, dict):
        raise ValueError("controls must be a dictionary")

    sanitized = dict(DEFAULT_CONTROLS)

    for k, v in controls.items():
        if k == "max_retries":
            try:
                val = int(v)
            except (ValueError, TypeError):
                raise ValueError("max_retries must be an integer")
            sanitized[k] = max(0, min(8, val))
        elif k == "contact_cap":
            try:
                val = int(v)
            except (ValueError, TypeError):
                raise ValueError("contact_cap must be an integer")
            sanitized[k] = max(0, min(5, val))
        elif k == "recovery_window_days":
            try:
                val = int(v)
            except (ValueError, TypeError):
                raise ValueError("recovery_window_days must be an integer")
            sanitized[k] = max(1, min(60, val))
        elif k == "escalate_above":
            try:
                val = float(v)
            except (ValueError, TypeError):
                raise ValueError("escalate_above must be numeric")
            if val < 0:
                raise ValueError("escalate_above must be >= 0")
            sanitized[k] = val
        elif k == "min_retry_gap_h":
            try:
                val = int(v)
            except (ValueError, TypeError):
                raise ValueError("min_retry_gap_h must be an integer")
            sanitized[k] = max(1, val)
        elif k == "pre_debit_notice_h":
            try:
                val = int(v)
            except (ValueError, TypeError):
                raise ValueError("pre_debit_notice_h must be an integer")
            sanitized[k] = max(0, val)
        elif k == "quiet_hours":
            if (
                not isinstance(v, (tuple, list))
                or len(v) != 2
                or not all(isinstance(x, int) and 0 <= x <= 23 for x in v)
            ):
                raise ValueError("quiet_hours must be a 2-tuple of ints in 0..23")
            sanitized[k] = (int(v[0]), int(v[1]))
        else:
            sanitized[k] = v

    return sanitized


def is_quiet(hour: int, quiet: Tuple[int, int]) -> bool:
    """Checks whether the given simulation hour falls inside quiet hours."""
    start, end = quiet
    h = hour % 24
    if start > end:
        return h >= start or h < end
    else:
        return start <= h < end


def defer_quiet(hour: int, quiet: Tuple[int, int]) -> int:
    """Defers an action scheduled during quiet hours to the end of the quiet period."""
    if not is_quiet(hour, quiet):
        return hour
    start, end = quiet
    h = hour % 24
    if start > end:
        if h >= start:
            return hour + (24 - h) + end
        else:
            return hour + (end - h)
    else:
        return hour + (end - h)


def salary_delay(case: Case, now: int) -> int:
    """Computes delay in hours to reach 10:00 on the customer's salary day."""
    days_ahead = (case.salary_day - day_of_month(now)) % 28
    target = (now // 24 + days_ahead) * 24 + 10
    if target <= now:
        target += 28 * 24
    return max(MIN_SALARY_DELAY_H, target - now)


def allowed_actions(
    case: Case, now: int, controls: Dict[str, Any] = DEFAULT_CONTROLS
) -> Dict[str, Tuple[bool, str]]:
    """Evaluates rules deterministically and returns {arm: (allowed, reason)} for all 7 arms."""
    res: Dict[str, Tuple[bool, str]] = {}
    age_days = (now - case.failed_at) / 24

    for arm in ARMS:
        if arm == "STOP":
            res[arm] = (True, "ok")
            continue

        # R7 Window rule applies to all arms except STOP
        if age_days > controls.get("recovery_window_days", 30):
            res[arm] = (
                False,
                f"recovery window of {controls.get('recovery_window_days', 30)} days exceeded",
            )
            continue

        if arm in RETRY_ARMS:
            # R1 Hard decline network rule
            if case.failure_class == "HARD":
                res[arm] = (
                    False,
                    f"network rule: never reattempt a hard decline ({case.error_code})",
                )
                continue

            # R3 Max retries cap
            if case.retries >= controls.get("max_retries", 4):
                res[arm] = (
                    False,
                    f"max retries ({controls.get('max_retries', 4)}) reached",
                )
                continue

            # Calculate earliest delay
            if arm == "RETRY_SALARY_DAY":
                delay = salary_delay(case, now)
            else:
                delay = ACTION_DELAY_H[arm]
            earliest_exec = now + delay

            # R4 Min gap rule: delay-aware (uses earliest_exec)
            if (
                case.last_retry_at != -999
                and (earliest_exec - case.last_retry_at)
                < controls.get("min_retry_gap_h", 2)
            ):
                res[arm] = (
                    False,
                    f"minimum gap of {controls.get('min_retry_gap_h', 2)}h between retries not met",
                )
                continue

            # R2 UPI Autopay pre-debit notice check
            if (
                case.method == "upi_autopay"
                and delay < controls.get("pre_debit_notice_h", 24)
            ):
                res[arm] = (
                    False,
                    f"UPI Autopay: {controls.get('pre_debit_notice_h', 24)}h pre-debit notification required before re-presentment",
                )
                continue

            res[arm] = (True, "ok")

        elif arm in CONTACT_ARMS:
            # R5 Contact cap
            if case.messages >= controls.get("contact_cap", 2):
                res[arm] = (
                    False,
                    f"customer contact cap ({controls.get('contact_cap', 2)}) reached",
                )
                continue

            # R6 Quiet hours: enforced via deferral at scheduling, does not block
            res[arm] = (True, "ok")

        elif arm == "ESCALATE":
            # R8 Escalation
            escalate_above = controls.get("escalate_above", 2500)
            if case.amount < escalate_above:
                res[arm] = (
                    False,
                    f"below escalation threshold (₹{escalate_above:,.0f})",
                )
            elif len(case.history) < MIN_ATTEMPTS_BEFORE_ESCALATION:
                res[arm] = (False, "no automated attempt made yet")
            else:
                res[arm] = (True, "ok")

    return res


def check_violations(
    case_before: Case,
    arm: str,
    decided_at: int,
    executed_at: int,
    controls: Dict[str, Any],
) -> List[str]:
    """Independent auditor applied to every executed action of every policy.
    
    Checks invariant rules independently of allowed_actions.
    """
    reasons: List[str] = []

    if arm in RETRY_ARMS:
        if case_before.failure_class == "HARD":
            reasons.append("retry_on_hard_decline")
        if case_before.retries >= controls.get("max_retries", 4):
            reasons.append("max_retries_exceeded")
        if (
            case_before.last_retry_at != -999
            and (executed_at - case_before.last_retry_at)
            < controls.get("min_retry_gap_h", 2)
        ):
            reasons.append("min_retry_gap")
        if (
            case_before.method == "upi_autopay"
            and (executed_at - decided_at) < controls.get("pre_debit_notice_h", 24)
        ):
            reasons.append("upi_pre_debit_notice")

    if arm in CONTACT_ARMS:
        if case_before.messages >= controls.get("contact_cap", 2):
            reasons.append("contact_cap_exceeded")
        if is_quiet(executed_at, controls.get("quiet_hours", (21, 9))):
            reasons.append("quiet_hours")

    if (decided_at - case_before.failed_at) / 24 > controls.get(
        "recovery_window_days", 30
    ):
        reasons.append("outside_recovery_window")

    return reasons
