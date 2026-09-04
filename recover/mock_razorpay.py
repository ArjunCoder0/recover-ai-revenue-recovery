"""Local Mock Razorpay API, Webhook Simulator, and SQLite Idempotency Layer.

Provides a lightweight, realistic Razorpay-shaped API simulator and webhook delivery
pipeline for the RECOVER engine, inspired by stripe-mock and payment gateway architectures.
Runs 100% locally with ZERO API keys and ZERO network calls.
"""

import json
import random
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from .simulator import Case, classify_decline, hidden_recovery_prob
from .policy import (
    COST,
    DEFAULT_CONTROLS,
    allowed_actions,
    validate_controls,
    salary_delay,
    defer_quiet,
    check_violations,
)
from .decide import Bandit, decide


class MockRazorpay:
    """Simulates Razorpay API endpoints locally without live network calls."""

    @staticmethod
    def create_payment_link(
        payment_id: str,
        amount: float,
        customer_phone: str = "+919876543210",
        customer_email: str = "customer@example.in",
        description: str = "Payment recovery link",
    ) -> Dict[str, Any]:
        """Simulates POST /v1/payment_links."""
        link_id = f"plink_mock_{uuid4().hex[:14]}"
        return {
            "id": link_id,
            "entity": "payment_link",
            "status": "created",
            "amount": int(round(amount * 100)),  # in paise
            "amount_paid": 0,
            "currency": "INR",
            "short_url": f"https://mock.razorpay.local/plink/{link_id}",
            "payment_id": payment_id,
            "description": description,
            "customer": {
                "contact": customer_phone,
                "email": customer_email,
            },
            "created_at": int(time.time()),
            "simulated": True,
            "mock_provider": "Razorpay Local Simulator",
        }

    @staticmethod
    def retry_payment(
        payment_id: str,
        amount: float,
        method: str,
        failure_class: str,
        now_h: int = 10,
        case: Optional[Case] = None,
        arm: str = "RETRY_24H",
        rng: Optional[random.Random] = None,
        force_failure: bool = False,
    ) -> Dict[str, Any]:
        """Simulates POST /v1/subscriptions/:id/retry or recurring debit re-presentment."""
        retry_id = f"pay_mock_{uuid4().hex[:14]}"
        if rng is None:
            rng = random.Random()

        if force_failure:
            success = False
        elif case is not None:
            # Internal environment outcome determination
            success = rng.random() < hidden_recovery_prob(case, arm, now_h)
        else:
            # Baseline realistic probability based on failure class
            base_p = 0.65 if failure_class in {"TRANSIENT", "SOFT"} else 0.05
            success = rng.random() < base_p

        status = "captured" if success else "failed"
        err_code = None if success else ("CARD_DECLINED" if failure_class == "HARD" else "GATEWAY_TIMEOUT")

        return {
            "id": retry_id,
            "entity": "payment",
            "status": status,
            "amount": int(round(amount * 100)),
            "currency": "INR",
            "method": method,
            "error_code": err_code,
            "error_description": None if success else "Transaction declined by issuing bank",
            "captured": success,
            "created_at": int(time.time()),
            "simulated": True,
            "mock_provider": "Razorpay Local Simulator",
        }

    @staticmethod
    def send_recovery_notification(
        payment_id: str,
        channel: str,
        recipient: str,
        template_name: str = "payment_recovery_prompt",
    ) -> Dict[str, Any]:
        """Simulates POST /v1/notifications."""
        notif_id = f"notif_mock_{uuid4().hex[:14]}"
        return {
            "id": notif_id,
            "entity": "notification",
            "channel": channel,
            "recipient": recipient,
            "template": template_name,
            "status": "sent",
            "created_at": int(time.time()),
            "simulated": True,
            "mock_provider": "Razorpay Local Simulator",
        }

    @staticmethod
    def resolve_payment(payment_id: str, amount: float) -> Dict[str, Any]:
        """Simulates manual or customer-initiated recovery resolution."""
        return {
            "id": payment_id,
            "entity": "payment",
            "status": "captured",
            "amount": int(round(amount * 100)),
            "currency": "INR",
            "recovered": True,
            "resolved_at": int(time.time()),
            "simulated": True,
            "mock_provider": "Razorpay Local Simulator",
        }

    @staticmethod
    def escalate_payment(payment_id: str, reason: str) -> Dict[str, Any]:
        """Simulates routing a high-value payment to Human Operations."""
        return {
            "id": payment_id,
            "entity": "case_escalation",
            "status": "escalated_to_human",
            "reason": reason,
            "escalated_at": int(time.time()),
            "simulated": True,
            "mock_provider": "Razorpay Local Simulator",
        }


class WebhookSimulator:
    """Generates and delivers Razorpay-formatted webhook events for testing."""

    COMMON_DECLINES = [
        ("INSUFFICIENT_FUNDS", "SOFT", "card"),
        ("ISSUER_UNAVAILABLE", "TRANSIENT", "upi_autopay"),
        ("UPI_TIMEOUT", "TRANSIENT", "upi_autopay"),
        ("EXPIRED_CARD", "ACTION_REQUIRED", "card"),
        ("MANDATE_REVOKED", "HARD", "upi_autopay"),
        ("DO_NOT_HONOR", "SOFT", "netbanking"),
    ]

    @staticmethod
    def create_failed_payment_event(
        payment_id: Optional[str] = None,
        event_id: Optional[str] = None,
        amount: float = 1499.0,
        method: str = "card",
        error_code: str = "INSUFFICIENT_FUNDS",
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Constructs a canonical Razorpay `payment.failed` webhook payload."""
        if payment_id is None:
            payment_id = f"pay_mock_{uuid4().hex[:14]}"
        if event_id is None:
            event_id = f"evt_mock_{uuid4().hex[:14]}"
        if timestamp is None:
            timestamp = int(time.time())

        return {
            "entity": "event",
            "account_id": "acc_mock_merchant_001",
            "event_id": event_id,
            "event": "payment.failed",
            "event_type": "payment.failed",
            "payment_id": payment_id,
            "amount": amount,
            "method": method,
            "error_code": error_code,
            "timestamp": timestamp,
            "created_at": timestamp,
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "amount": int(round(amount * 100)),
                        "currency": "INR",
                        "status": "failed",
                        "method": method,
                        "error_code": error_code,
                        "error_description": f"Payment failed due to {error_code}",
                        "error_source": "issuing_bank",
                        "error_step": "payment_authorization",
                        "error_reason": error_code.lower(),
                        "created_at": timestamp,
                    }
                }
            },
            "simulated": True,
        }

    @classmethod
    def create_batch(cls, count: int = 10, seed: int = 42) -> List[Dict[str, Any]]:
        """Creates a batch of realistic failure webhook events."""
        rng = random.Random(seed)
        events = []
        for i in range(count):
            err_code, _, method = rng.choice(cls.COMMON_DECLINES)
            amt = round(rng.uniform(499.0, 15000.0), 2)
            evt = cls.create_failed_payment_event(
                amount=amt,
                method=method,
                error_code=err_code,
                timestamp=int(time.time()) - (count - i) * 60,
            )
            events.append(evt)
        return events

    @staticmethod
    def create_duplicate_events(original_event: Dict[str, Any], count: int = 10) -> List[Dict[str, Any]]:
        """Returns identical copies of the same webhook event (same event_id and payload)."""
        duplicates = []
        for _ in range(count):
            # Exact deep copy with identical event_id
            duplicates.append(json.loads(json.dumps(original_event)))
        return duplicates

    @staticmethod
    def create_stale_event(original_event: Dict[str, Any], hours_old: int = 80) -> Dict[str, Any]:
        """Creates a webhook event that is older than the configured recovery window."""
        stale = json.loads(json.dumps(original_event))
        stale_ts = int(time.time()) - (hours_old * 3600)
        stale["event_id"] = f"evt_mock_stale_{uuid4().hex[:10]}"
        stale["timestamp"] = stale_ts
        stale["created_at"] = stale_ts
        stale["payload"]["payment"]["entity"]["created_at"] = stale_ts
        return stale


class IdempotencyStore:
    """Thread-safe SQLite-backed idempotency store for webhook events."""

    def __init__(self, db_path: str = "recover_idempotency.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_idempotency (
                    event_id TEXT PRIMARY KEY,
                    payment_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    action_taken TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    duplicate_count INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()

    def check_and_record(
        self,
        event_id: str,
        payment_id: str,
        event_type: str,
        handler_fn: Callable[[], Dict[str, Any]],
    ) -> Tuple[bool, Dict[str, Any], str]:
        """Atomically checks event_id.

        Returns (is_duplicate: bool, result: Dict[str, Any], status_msg: str).
        Guarantees that handler_fn is executed AT MOST ONCE per event_id.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT event_id, status, action_taken, result_json, duplicate_count FROM webhook_idempotency WHERE event_id = ?",
                    (event_id,),
                )
                row = cur.fetchone()

                if row is not None:
                    # Duplicate detected!
                    new_dup_count = row["duplicate_count"] + 1
                    cur.execute(
                        "UPDATE webhook_idempotency SET duplicate_count = ? WHERE event_id = ?",
                        (new_dup_count, event_id),
                    )
                    conn.commit()
                    cached_result = json.loads(row["result_json"]) if row["result_json"] else {}
                    return (
                        True,
                        cached_result,
                        f"DUPLICATE_BLOCKED: Event '{event_id}' already processed. Returned cached result.",
                    )

                # Reserve event_id with PROCESSING status
                cur.execute(
                    """
                    INSERT INTO webhook_idempotency (
                        event_id, payment_id, event_type, status, created_at, duplicate_count
                    ) VALUES (?, ?, ?, 'PROCESSING', ?, 0)
                    """,
                    (event_id, payment_id, event_type, now_iso),
                )
                conn.commit()

        # Execute handler outside the lock to prevent blocking
        try:
            result = handler_fn()
            action_taken = result.get("action", "UNKNOWN")
            processed_iso = datetime.now(timezone.utc).isoformat()

            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        UPDATE webhook_idempotency
                        SET status = 'PROCESSED',
                            action_taken = ?,
                            result_json = ?,
                            processed_at = ?
                        WHERE event_id = ?
                        """,
                        (action_taken, json.dumps(result), processed_iso, event_id),
                    )
                    conn.commit()

            return (False, result, f"PROCESSED: Event '{event_id}' processed successfully.")

        except Exception as exc:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        "UPDATE webhook_idempotency SET status = 'FAILED', result_json = ? WHERE event_id = ?",
                        (json.dumps({"error": str(exc)}), event_id),
                    )
                    conn.commit()
            raise exc

    def get_stats(self) -> Dict[str, int]:
        """Returns aggregate metrics from the idempotency table."""
        with self._lock, self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total_events,
                    SUM(CASE WHEN status = 'PROCESSED' THEN 1 ELSE 0 END) as processed_count,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
                    SUM(duplicate_count) as total_duplicates_blocked
                FROM webhook_idempotency
                """
            )
            row = cur.fetchone()
            return {
                "total_events": row["total_events"] or 0,
                "processed_count": row["processed_count"] or 0,
                "failed_count": row["failed_count"] or 0,
                "total_duplicates_blocked": row["total_duplicates_blocked"] or 0,
            }

    def clear(self) -> None:
        """Clears idempotency table (useful for isolated tests)."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM webhook_idempotency")
            conn.commit()


class MockRazorpayPipeline:
    """Coordinates incoming webhooks, Idempotency, Policy Fence, and Thompson Sampling AI."""

    def __init__(
        self,
        idempotency_store: Optional[IdempotencyStore] = None,
        bandit: Optional[Bandit] = None,
        controls: Optional[Dict[str, Any]] = None,
        seed: int = 42,
    ):
        self.idempotency_store = idempotency_store or IdempotencyStore()
        self.bandit = bandit or Bandit(seed=seed)
        self.controls = validate_controls(controls or DEFAULT_CONTROLS)
        self.audit_trail: List[Dict[str, Any]] = []
        self.outcome_rng = random.Random(seed)
        self.seq = 0

    def process_webhook(
        self,
        event: Dict[str, Any],
        now_h: int = 10,
        force_failure: bool = False,
    ) -> Dict[str, Any]:
        """Main end-to-end entry point:

        Webhook Event
          → Idempotency Check
          → Decline Diagnosis & Policy Fence
          → Thompson Sampling AI
          → Mock Razorpay Action
          → Outcome Observation
          → Bandit Learning
          → Audit Log
        """
        event_id = event["event_id"]
        payment_id = event.get("payment_id") or event["payload"]["payment"]["entity"]["id"]
        event_type = event.get("event_type", event.get("event", "payment.failed"))

        def handler() -> Dict[str, Any]:
            # 1. Extract payload details
            payment_entity = event["payload"]["payment"]["entity"]
            amount = float(payment_entity.get("amount", 100000)) / 100.0  # paise to INR
            method = payment_entity.get("method", "card")
            error_code = payment_entity.get("error_code", "INSUFFICIENT_FUNDS")
            fc = classify_decline(error_code)

            # 2. Build local Case representation
            case = Case(
                id=self.seq + 1,
                method=method,
                amount=amount,
                error_code=error_code,
                failed_at=now_h,
                salary_day=1,
                responsiveness=0.5,
                state="OPEN",
                cost=0.0,
                retries=0,
                messages=0,
                last_retry_at=-999,
                history=[],
            )

            # 3. Policy Safety Check (Rules R1-R8)
            allowed_map = allowed_actions(case, now_h, self.controls)
            legal_arms = {a for a, (is_ok, _) in allowed_map.items() if is_ok}

            # 4. Thompson Sampling AI Decision
            arm, rationale = decide(case, now_h, self.bandit, self.controls)

            # Safety guarantee: AI cannot choose an action blocked by policy
            if arm not in legal_arms:
                raise RuntimeError(
                    f"CRITICAL SAFETY VIOLATION: AI selected blocked arm '{arm}'. Legal: {legal_arms}"
                )

            # 5. Execute Action against Mock Razorpay API
            api_response: Dict[str, Any] = {}
            success: Optional[bool] = None

            if arm in {"STOP", "ESCALATE"}:
                case.state = "ESCALATED" if arm == "ESCALATE" else "EXHAUSTED"
                if arm == "ESCALATE":
                    api_response = MockRazorpay.escalate_payment(
                        payment_id=payment_id,
                        reason="High-value case passed automated recovery",
                    )
                else:
                    api_response = {
                        "id": payment_id,
                        "status": "closed",
                        "action": "STOP",
                        "reason": "Negative EV or policy stop",
                        "simulated": True,
                    }
            elif arm == "PAYMENT_LINK":
                api_response = MockRazorpay.create_payment_link(
                    payment_id=payment_id,
                    amount=amount,
                    description=f"Recover payment for invoice {payment_id}",
                )
                case.messages += 1
                case.cost += COST[arm]
                # Simulating customer payment through link
                success = self.outcome_rng.random() < hidden_recovery_prob(case, arm, now_h)
                if success:
                    case.state = "RECOVERED"
                    MockRazorpay.resolve_payment(payment_id, amount)
            elif arm in {"WHATSAPP_LINK", "SMS_REMINDER"}:
                channel = "whatsapp" if arm == "WHATSAPP_LINK" else "sms"
                api_response = MockRazorpay.send_recovery_notification(
                    payment_id=payment_id,
                    channel=channel,
                    recipient="+919876543210",
                )
                case.messages += 1
                case.cost += COST[arm]
                success = self.outcome_rng.random() < hidden_recovery_prob(case, arm, now_h)
                if success:
                    case.state = "RECOVERED"
                    MockRazorpay.resolve_payment(payment_id, amount)
            else:
                # Retry arms: RETRY_2H, RETRY_24H, RETRY_72H, RETRY_SALARY_DAY
                api_response = MockRazorpay.retry_payment(
                    payment_id=payment_id,
                    amount=amount,
                    method=method,
                    failure_class=fc,
                    now_h=now_h,
                    case=case,
                    arm=arm,
                    rng=self.outcome_rng,
                    force_failure=force_failure,
                )
                case.retries += 1
                case.last_retry_at = now_h
                case.cost += COST[arm]
                success = api_response.get("captured", False)
                if success:
                    case.state = "RECOVERED"

            # 6. Online Bandit Learning (Update Beta distribution)
            if success is not None and arm not in {"STOP", "ESCALATE"}:
                self.bandit.update(fc, arm, success)

            # 7. Audit Logging
            self.seq += 1
            audit_entry = {
                "seq": self.seq,
                "event_id": event_id,
                "payment_id": payment_id,
                "failure_class": fc,
                "decline_code": error_code,
                "amount": amount,
                "method": method,
                "action": arm,
                "success": success,
                "legal_arms_count": len(legal_arms),
                "rationale": rationale,
                "api_response": api_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.audit_trail.append(audit_entry)

            return {
                "event_id": event_id,
                "payment_id": payment_id,
                "action": arm,
                "success": success,
                "state": case.state,
                "amount": amount,
                "failure_class": fc,
                "api_response": api_response,
                "rationale": rationale,
                "simulated": True,
            }

        # Run with SQLite idempotency protection
        is_duplicate, result, message = self.idempotency_store.check_and_record(
            event_id=event_id,
            payment_id=payment_id,
            event_type=event_type,
            handler_fn=handler,
        )

        return {
            "is_duplicate": is_duplicate,
            "status": "DUPLICATE_BLOCKED" if is_duplicate else "PROCESSED",
            "message": message,
            "data": result,
        }
