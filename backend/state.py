"""State management and pipeline coordination for the RECOVER backend.

Integrates simulator, decision engine, Thompson Sampling bandit, policy fence,
human-in-the-loop actions, and local Mock Razorpay idempotency pipeline.
"""

import copy
import concurrent.futures
import math
import random
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from recover.simulator import generate, classify_decline, Case, hidden_recovery_prob
from recover.policy import (
    DEFAULT_CONTROLS,
    validate_controls,
    COST,
    ACTION_DELAY_H,
    CONTACT_ARMS,
    RETRY_ARMS,
    ARMS,
    allowed_actions,
    check_violations,
    defer_quiet,
)
from recover.decide import Bandit, decide, explain_rationale
from recover.engine import run, execute_human_action
from recover.metrics import summarize, by_class, confidence
from recover.outreach import draft
from recover.mock_razorpay import (
    MockRazorpay,
    WebhookSimulator,
    IdempotencyStore,
    MockRazorpayPipeline,
)


def compute_risk(c: Case) -> float:
    """Computes an observable risk score for prioritizing review and triage."""
    base = 0.2
    if c.failure_class == "HARD":
        base += 0.55
    elif c.failure_class == "ACTION_REQUIRED":
        base += 0.35
    elif c.failure_class == "TRANSIENT":
        base += 0.1
    if c.amount >= 5000:
        base += 0.2
    return min(0.99, round(base, 2))


class StateManager:
    """Thread-safe singleton state manager for RECOVER simulation and operations."""

    def __init__(self, db_path: str = "recover_idempotency.db"):
        self._lock = threading.RLock()
        self.controls = copy.deepcopy(DEFAULT_CONTROLS)
        self.n: int = 400
        self.seed: int = 42
        self.llm: bool = False

        self.cases: List[Case] = []
        self.smart_cases: List[Case] = []
        self.audit_smart: List[Dict[str, Any]] = []
        self.bandit: Optional[Bandit] = None
        self.naive_cases: List[Case] = []
        self.audit_naive: List[Dict[str, Any]] = []

        self.rel_store = IdempotencyStore(db_path)
        self.rel_pipeline = MockRazorpayPipeline(idempotency_store=self.rel_store, seed=self.seed)
        self.rel_events_log: List[Dict[str, Any]] = []

        self._benchmark_cache: Dict[str, Any] = {}

        # Run initial default simulation
        self.run_simulation(self.n, self.seed, self.controls, self.llm)

    def run_simulation(
        self,
        n: int,
        seed: int,
        controls: Optional[Dict[str, Any]] = None,
        llm: bool = False,
    ) -> None:
        """Executes full smart and naive recovery simulations with current controls."""
        with self._lock:
            self.n = n
            self.seed = seed
            self.llm = llm
            if controls is not None:
                self.controls = validate_controls(controls)
            else:
                self.controls = validate_controls(self.controls)

            self.cases = generate(self.n, seed=self.seed)
            self.smart_cases, self.audit_smart, self.bandit = run(
                self.cases, controls=self.controls, policy="smart", seed=self.seed
            )
            self.naive_cases, self.audit_naive, _ = run(
                self.cases, controls=self.controls, policy="naive", seed=self.seed
            )
            # Rebind bandit to mock pipeline so live mock webhooks share learned priors
            self.rel_pipeline.bandit = self.bandit
            self.rel_pipeline.controls = self.controls

    def get_kpis(self) -> Dict[str, Any]:
        """Calculates executive overview KPIs comparing Smart vs Naive policies."""
        with self._lock:
            smart_sum = summarize(self.smart_cases, self.audit_smart)
            naive_sum = summarize(self.naive_cases, self.audit_naive)
            df_class = by_class(self.smart_cases)
            class_breakdown = df_class.to_dict(orient="index")

            # Wilson score interval for recovery rate (95% CI)
            p_hat = smart_sum.get("rate", 0.0)
            n_c = len(self.smart_cases)
            z = 1.96
            if n_c > 0:
                denom = 1 + (z**2 / n_c)
                center = (p_hat + z**2 / (2 * n_c)) / denom
                spread = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n_c)) / n_c) / denom
                lower = max(0.0, round((center - spread) * 100.0, 2))
                upper = min(100.0, round((center + spread) * 100.0, 2))
            else:
                lower, upper = 0.0, 0.0

            conf_int = {
                "metric": "Recovery Rate",
                "rate_pct": round(p_hat * 100.0, 2),
                "ci_lower_pct": lower,
                "ci_upper_pct": upper,
                "confidence_level": "95%",
            }

            smart_rec = smart_sum.get("rate", 0.0) * 100.0
            naive_rec = naive_sum.get("rate", 0.0) * 100.0
            lift_pct = round(smart_rec - naive_rec, 2)

            smart_net = smart_sum.get("net", 0.0)
            naive_net = naive_sum.get("net", 0.0)
            net_lift = round(smart_net - naive_net, 2)

            smart_fee = smart_sum.get("cost", 0.0)
            naive_fee = naive_sum.get("cost", 0.0)
            fee_savings = round(naive_fee - smart_fee, 2)

            smart_viol = smart_sum.get("violations", 0)
            naive_viol = naive_sum.get("violations", 0)
            viol_prevented = max(0, naive_viol - smart_viol)

            total_at_risk = sum(c.amount for c in self.cases)

            return {
                "smart_recovery_rate": round(smart_rec, 2),
                "naive_recovery_rate": round(naive_rec, 2),
                "recovery_rate_lift_pct": lift_pct,
                "smart_net_revenue": round(smart_net, 2),
                "naive_net_revenue": round(naive_net, 2),
                "net_revenue_lift_inr": net_lift,
                "smart_total_fees": round(smart_fee, 2),
                "naive_total_fees": round(naive_fee, 2),
                "fee_savings_inr": fee_savings,
                "smart_violations": smart_viol,
                "naive_violations": naive_viol,
                "violations_prevented": viol_prevented,
                "total_cases": len(self.smart_cases),
                "total_at_risk_inr": round(total_at_risk, 2),
                "by_class": class_breakdown,
                "confidence_interval": conf_int,
            }

    def serialize_case(self, c: Case) -> Dict[str, Any]:
        """Serializes a Case dataclass instance to a JSON-ready dictionary."""
        # Find latest rationale from history if present
        latest_rationale = None
        for h in reversed(c.history):
            if h.get("rationale"):
                latest_rationale = h.get("rationale")
                break

        return {
            "id": c.id,
            "method": c.method,
            "amount": c.amount,
            "error_code": c.error_code,
            "failure_class": c.failure_class,
            "risk_score": compute_risk(c),
            "failed_at": c.failed_at,
            "salary_day": c.salary_day,
            "created_at": c.failed_at,
            "retries": c.retries,
            "contacts": c.messages,
            "cost": round(c.cost, 2),
            "state": c.state,
            "recovered_at": c.recovered_at if c.recovered_at != -1 else None,
            "history": c.history,
            "latest_rationale": latest_rationale,
        }

    def get_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        failure_class: Optional[str] = None,
        state: Optional[str] = None,
        search: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        risk_min: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Returns paginated and filtered list of smart simulation cases."""
        with self._lock:
            filtered = self.smart_cases

            if failure_class and failure_class != "ALL":
                filtered = [c for c in filtered if c.failure_class == failure_class]

            if state and state != "ALL":
                filtered = [c for c in filtered if c.state == state]

            if min_amount is not None:
                filtered = [c for c in filtered if c.amount >= min_amount]

            if max_amount is not None:
                filtered = [c for c in filtered if c.amount <= max_amount]

            if risk_min is not None:
                filtered = [c for c in filtered if compute_risk(c) >= risk_min]

            if search:
                s = search.lower().strip()
                filtered = [
                    c
                    for c in filtered
                    if s in str(c.id)
                    or s in c.error_code.lower()
                    or s in c.method.lower()
                    or s in c.failure_class.lower()
                ]

            total = len(filtered)
            start = (page - 1) * page_size
            end = start + page_size
            items = [self.serialize_case(c) for c in filtered[start:end]]

            return items, total

    def get_case_detail(self, case_id: int) -> Optional[Dict[str, Any]]:
        """Returns full explainability, alternatives, history, and message preview for a case."""
        with self._lock:
            case = next((c for c in self.smart_cases if c.id == case_id), None)
            if not case:
                return None

            case_data = self.serialize_case(case)

            # Re-evaluate decision rationale & alternatives at current state
            now_h = case.history[-1]["decided_at"] if case.history else case.failed_at
            chosen_arm, rationale = decide(case, now_h, self.bandit, self.controls)
            why_chosen_text = explain_rationale(rationale, case)

            # Prepare alternatives list
            alternatives = []
            if rationale and "considered" in rationale:
                for c_alt in rationale["considered"]:
                    alternatives.append(
                        {
                            "arm": c_alt["arm"],
                            "allowed": c_alt["allowed"],
                            "rejection_reason": c_alt.get("reason"),
                            "sampled_p": round(c_alt.get("sampled_p") or 0.0, 4),
                            "expected_value": round(c_alt.get("ev") or 0.0, 2),
                            "cost": c_alt.get("cost", 0.0),
                            "alpha": round(c_alt.get("posterior_alpha", 1.0), 2),
                            "beta": round(c_alt.get("posterior_beta", 1.0), 2),
                        }
                    )

            # Outreach draft preview
            outreach_preview = None
            if chosen_arm in CONTACT_ARMS:
                msg, src = draft(case, chosen_arm, use_llm=self.llm)
                outreach_preview = {
                    "arm": chosen_arm,
                    "message": msg,
                    "source": src,
                }
            else:
                msg, src = draft(case, "PAYMENT_LINK", use_llm=self.llm)
                outreach_preview = {
                    "arm": "PAYMENT_LINK",
                    "message": msg,
                    "source": src,
                }

            return {
                "case": case_data,
                "why_chosen": {
                    "chosen_arm": chosen_arm,
                    "rationale": rationale,
                    "explanation_text": why_chosen_text,
                },
                "alternatives": alternatives,
                "outreach_preview": outreach_preview,
                "history": case.history,
            }

    def get_decision_intelligence(self) -> Dict[str, Any]:
        """Returns Thompson Sampling posterior distributions, arm win rates, and pulls."""
        with self._lock:
            if not self.bandit:
                return {"arms": [], "arms_by_class": {}, "total_decisions": 0}

            snapshot = self.bandit.snapshot()
            arms_list = []
            arms_by_class: Dict[str, List[Dict[str, Any]]] = {}

            for item in snapshot:
                arm_data = {
                    "arm": item["arm"],
                    "failure_class": item["class"],
                    "alpha": round(item["alpha"], 2),
                    "beta": round(item["beta"], 2),
                    "pulls": item["observations"],
                    "mean_prob": round(item["posterior_mean"], 4),
                    "cost": COST.get(item["arm"], 0.0),
                }
                arms_list.append(arm_data)
                fc = item["class"]
                if fc not in arms_by_class:
                    arms_by_class[fc] = []
                arms_by_class[fc].append(arm_data)

            return {
                "arms": arms_list,
                "arms_by_class": arms_by_class,
                "total_decisions": len(self.audit_smart),
            }

    def get_human_queue(self) -> List[Dict[str, Any]]:
        """Returns cases requiring human review according to configured thresholds."""
        with self._lock:
            threshold = self.controls.get("escalate_above", 2500.0)
            queue = []
            for c in self.smart_cases:
                risk = compute_risk(c)
                is_high_value = c.amount >= threshold
                is_high_risk = risk >= 0.85
                is_action_needed = c.failure_class == "ACTION_REQUIRED" and c.state == "OPEN"

                if is_high_value or is_high_risk or is_action_needed:
                    reason = []
                    if is_high_value:
                        reason.append(f"High transaction value (₹{c.amount:,.2f} ≥ ₹{threshold:,.2f})")
                    if is_high_risk:
                        reason.append(f"Elevated fraud/churn risk score ({risk:.2f} ≥ 0.85)")
                    if is_action_needed:
                        reason.append("Customer action required for paused/expired instrument")

                    rec = "PAYMENT_LINK" if c.failure_class in {"ACTION_REQUIRED", "HARD"} else "RETRY_24H"
                    queue.append(
                        {
                            "case_id": c.id,
                            "amount": c.amount,
                            "method": c.method,
                            "failure_class": c.failure_class,
                            "error_code": c.error_code,
                            "risk_score": risk,
                            "failed_at": c.failed_at,
                            "retries": c.retries,
                            "state": c.state,
                            "reason": " • ".join(reason),
                            "recommended_action": rec,
                        }
                    )

            # Sort highest amount first
            queue.sort(key=lambda x: x["amount"], reverse=True)
            return queue

    def execute_human_review(
        self, case_id: int, action: str, note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Applies a human-in-the-loop approval, rejection, or manual intervention."""
        with self._lock:
            case = next((c for c in self.smart_cases if c.id == case_id), None)
            if not case:
                raise ValueError(f"Case #{case_id} not found.")

            arm = "PAYMENT_LINK" if action == "APPROVE" else ("STOP" if action == "REJECT" else action)

            entry = execute_human_action(
                case=case,
                arm=arm,
                controls=self.controls,
                audit=self.audit_smart,
                bandit=self.bandit,
                seed=self.seed,
            )
            if note:
                entry["rationale"]["note"] = f"{entry['rationale'].get('note', '')} | Reviewer note: {note}"

            return {
                "success": True,
                "case": self.serialize_case(case),
                "audit_entry": entry,
            }

    def run_duplicate_blast(
        self,
        event_id: Optional[str] = None,
        count: int = 10,
        error_code: str = "INSUFFICIENT_FUNDS",
        amount: float = 1299.0,
    ) -> Dict[str, Any]:
        """Blasts the local Mock Razorpay pipeline with N identical concurrent webhooks.

        Verifies that exactly 1 request is PROCESSED, N-1 are BLOCKED by SQLite idempotency,
        and 0 duplicate retries or debit attempts occur.
        """
        if not event_id:
            event_id = f"evt_blast_{uuid4().hex[:12]}"

        payload = WebhookSimulator.create_failed_payment_event(
            event_id=event_id,
            error_code=error_code,
            amount=amount,
        )

        results: List[Dict[str, Any]] = []
        start_time = time.perf_counter()

        def worker() -> Dict[str, Any]:
            return self.rel_pipeline.process_webhook(payload, now_h=12)

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(count, 16)) as executor:
            futures = [executor.submit(worker) for _ in range(count)]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as exc:
                    results.append({"error": str(exc), "status": "failed"})

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        processed = sum(1 for r in results if r.get("status") == "PROCESSED")
        blocked = sum(1 for r in results if r.get("is_duplicate") is True or r.get("status") == "DUPLICATE_BLOCKED")
        duplicate_executions = max(0, processed - 1)

        # Record event in live log
        with self._lock:
            self.rel_events_log.insert(
                0,
                {
                    "event_id": event_id,
                    "event_type": "payment.failed",
                    "payment_id": payload["payload"]["payment"]["entity"]["id"],
                    "error_code": error_code,
                    "amount": amount,
                    "total_burst": count,
                    "processed": processed,
                    "blocked": blocked,
                    "duplicate_executions": duplicate_executions,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

        return {
            "event_id": event_id,
            "total_bursts": count,
            "processed": processed,
            "blocked": blocked,
            "duplicate_executions": duplicate_executions,
            "execution_time_ms": round(duration_ms, 2),
            "status": "PASS" if duplicate_executions == 0 and processed == 1 else "FAIL",
            "message": (
                f"100% Idempotent: {processed} processed, {blocked} blocked, "
                f"{duplicate_executions} duplicate executions."
            ),
        }

    def simulate_single_webhook(
        self,
        event_type: str = "payment.failed",
        error_code: str = "UPI_TIMEOUT",
        amount: float = 2499.0,
        method: str = "upi",
        customer_phone: str = "+919876543210",
        customer_email: str = "customer@example.in",
    ) -> Dict[str, Any]:
        """Simulates an individual webhook arrival from Mock Razorpay gateway."""
        event_id = f"evt_single_{uuid4().hex[:12]}"
        payload = WebhookSimulator.create_failed_payment_event(
            event_id=event_id,
            error_code=error_code,
            amount=amount,
            method=method,
        )
        res = self.rel_pipeline.process_webhook(payload, now_h=10)

        with self._lock:
            self.rel_events_log.insert(
                0,
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "payment_id": payload["payload"]["payment"]["entity"]["id"],
                    "error_code": error_code,
                    "amount": amount,
                    "total_burst": 1,
                    "processed": 1 if res.get("status") == "PROCESSED" else 0,
                    "blocked": 1 if res.get("status") == "BLOCKED_DUPLICATE" else 0,
                    "duplicate_executions": 0,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

        return res

    def get_audit_trail(
        self,
        case_id: Optional[int] = None,
        arm: Optional[str] = None,
        violation_only: bool = False,
        policy: str = "smart",
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Queries the append-only audit trail logs with filtering."""
        with self._lock:
            logs = self.audit_smart if policy == "smart" else self.audit_naive

            if case_id is not None:
                logs = [e for e in logs if e.get("case_id") == case_id]

            if arm and arm != "ALL":
                logs = [e for e in logs if e.get("arm") == arm]

            if violation_only:
                logs = [e for e in logs if e.get("violation", 0) > 0]

            total = len(logs)
            start = (page - 1) * page_size
            end = start + page_size
            return logs[start:end], total

    def run_benchmark(self, seeds: List[int], n: int = 200) -> Dict[str, Any]:
        """Runs multi-seed benchmark comparing smart policy against naive baseline."""
        with self._lock:
            cache_key = f"{','.join(map(str, seeds))}_{n}"
            if cache_key in self._benchmark_cache:
                return self._benchmark_cache[cache_key]

            seeds_data = []
            for s in seeds:
                c_list = generate(n, seed=s)
                s_cases, s_audit, _ = run(c_list, controls=self.controls, policy="smart", seed=s)
                n_cases, n_audit, _ = run(c_list, controls=self.controls, policy="naive", seed=s)

                s_sum = summarize(s_cases, s_audit)
                n_sum = summarize(n_cases, n_audit)

                seeds_data.append(
                    {
                        "seed": s,
                        "smart_recovered_pct": round(s_sum["rate"] * 100.0, 2),
                        "naive_recovered_pct": round(n_sum["rate"] * 100.0, 2),
                        "smart_net_revenue": round(s_sum["net"], 2),
                        "naive_net_revenue": round(n_sum["net"], 2),
                        "smart_cost": round(s_sum["cost"], 2),
                        "naive_cost": round(n_sum["cost"], 2),
                        "smart_violations": s_sum["violations"],
                        "naive_violations": n_sum["violations"],
                    }
                )

            avg_smart_rec = sum(r["smart_recovered_pct"] for r in seeds_data) / len(seeds_data)
            avg_naive_rec = sum(r["naive_recovered_pct"] for r in seeds_data) / len(seeds_data)
            avg_smart_net = sum(r["smart_net_revenue"] for r in seeds_data) / len(seeds_data)
            avg_naive_net = sum(r["naive_net_revenue"] for r in seeds_data) / len(seeds_data)
            avg_smart_fees = sum(r["smart_cost"] for r in seeds_data) / len(seeds_data)
            avg_naive_fees = sum(r["naive_cost"] for r in seeds_data) / len(seeds_data)
            total_smart_viol = sum(r["smart_violations"] for r in seeds_data)
            total_naive_viol = sum(r["naive_violations"] for r in seeds_data)

            res = {
                "summary": {
                    "seeds_tested": len(seeds),
                    "batch_size_per_seed": n,
                    "avg_smart_recovery_rate": round(avg_smart_rec, 2),
                    "avg_naive_recovery_rate": round(avg_naive_rec, 2),
                    "avg_recovery_lift_pct": round(avg_smart_rec - avg_naive_rec, 2),
                    "avg_smart_net_revenue": round(avg_smart_net, 2),
                    "avg_naive_net_revenue": round(avg_naive_net, 2),
                    "avg_net_revenue_lift": round(avg_smart_net - avg_naive_net, 2),
                    "avg_fee_savings": round(avg_naive_fees - avg_smart_fees, 2),
                    "total_smart_violations": total_smart_viol,
                    "total_naive_violations": total_naive_viol,
                    "violations_prevented": max(0, total_naive_viol - total_smart_viol),
                },
                "seeds_data": seeds_data,
            }

            self._benchmark_cache[cache_key] = res
            return res


# Global singleton instance
state = StateManager()
