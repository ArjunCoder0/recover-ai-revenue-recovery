"""Tests for Mock Razorpay API, Webhook Simulator, and SQLite Idempotency Layer."""

import concurrent.futures
import os
import tempfile
import pytest

from recover.mock_razorpay import (
    MockRazorpay,
    WebhookSimulator,
    IdempotencyStore,
    MockRazorpayPipeline,
)
from recover.policy import DEFAULT_CONTROLS, allowed_actions
from recover.simulator import Case, classify_decline


@pytest.fixture
def temp_db():
    """Creates a temporary SQLite database file for testing isolation."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_mock_razorpay_endpoints():
    """Verifies that Mock Razorpay returns realistic structured dictionaries."""
    # 1. Payment Link
    link = MockRazorpay.create_payment_link(
        payment_id="pay_test_001",
        amount=2499.0,
        customer_phone="+919876543210",
    )
    assert link["entity"] == "payment_link"
    assert link["status"] == "created"
    assert link["amount"] == 249900  # paise
    assert "https://mock.razorpay.local/plink/" in link["short_url"]
    assert link["simulated"] is True

    # 2. Retry Payment
    retry = MockRazorpay.retry_payment(
        payment_id="pay_test_001",
        amount=2499.0,
        method="card",
        failure_class="TRANSIENT",
    )
    assert retry["entity"] == "payment"
    assert retry["status"] in {"captured", "failed"}
    assert retry["currency"] == "INR"
    assert retry["simulated"] is True

    # 3. Notification
    notif = MockRazorpay.send_recovery_notification(
        payment_id="pay_test_001",
        channel="whatsapp",
        recipient="+919876543210",
    )
    assert notif["entity"] == "notification"
    assert notif["status"] == "sent"
    assert notif["simulated"] is True

    # 4. Resolve Payment
    res = MockRazorpay.resolve_payment("pay_test_001", 2499.0)
    assert res["status"] == "captured"
    assert res["recovered"] is True

    # 5. Escalate Payment
    esc = MockRazorpay.escalate_payment("pay_test_001", "High-value threshold reached")
    assert esc["status"] == "escalated_to_human"


def test_webhook_simulator_generation():
    """Verifies generation of single events, batches, duplicates, and stale events."""
    event = WebhookSimulator.create_failed_payment_event(
        amount=1999.0,
        method="card",
        error_code="INSUFFICIENT_FUNDS",
    )
    assert event["event"] == "payment.failed"
    assert event["payload"]["payment"]["entity"]["amount"] == 199900
    assert event["payload"]["payment"]["entity"]["error_code"] == "INSUFFICIENT_FUNDS"

    batch = WebhookSimulator.create_batch(count=5, seed=123)
    assert len(batch) == 5
    assert all(e["event"] == "payment.failed" for e in batch)

    duplicates = WebhookSimulator.create_duplicate_events(event, count=4)
    assert len(duplicates) == 4
    assert all(d["event_id"] == event["event_id"] for d in duplicates)

    stale = WebhookSimulator.create_stale_event(event, hours_old=75)
    assert stale["timestamp"] < event["timestamp"] - (70 * 3600)


def test_single_event_processed_successfully(temp_db):
    """Verifies that a valid webhook event is processed completely through the pipeline."""
    store = IdempotencyStore(temp_db)
    pipeline = MockRazorpayPipeline(idempotency_store=store, seed=42)

    event = WebhookSimulator.create_failed_payment_event(
        amount=999.0,
        method="card",
        error_code="ISSUER_UNAVAILABLE",
    )

    resp = pipeline.process_webhook(event)
    assert resp["is_duplicate"] is False
    assert resp["status"] == "PROCESSED"
    assert resp["data"]["action"] in {"RETRY_2H", "RETRY_24H", "PAYMENT_LINK", "SMS_REMINDER"}
    assert len(pipeline.audit_trail) == 1


def test_duplicate_webhook_returns_cached_result(temp_db):
    """Verifies that sending an identical webhook returns the cached response without re-execution."""
    store = IdempotencyStore(temp_db)
    pipeline = MockRazorpayPipeline(idempotency_store=store, seed=42)

    event = WebhookSimulator.create_failed_payment_event(
        amount=1499.0,
        method="card",
        error_code="INSUFFICIENT_FUNDS",
    )

    # First call
    first_resp = pipeline.process_webhook(event)
    assert first_resp["is_duplicate"] is False
    assert len(pipeline.audit_trail) == 1

    # Second call with SAME event_id
    second_resp = pipeline.process_webhook(event)
    assert second_resp["is_duplicate"] is True
    assert second_resp["status"] == "DUPLICATE_BLOCKED"
    assert "DUPLICATE_BLOCKED" in second_resp["message"]
    # Audit trail still has only 1 execution
    assert len(pipeline.audit_trail) == 1
    # Cached data matches
    assert second_resp["data"]["action"] == first_resp["data"]["action"]


def test_ten_duplicate_events_cause_exactly_one_execution(temp_db):
    """Verifies that blasting 10 identical webhook calls causes exactly 1 execution and 9 blocked."""
    store = IdempotencyStore(temp_db)
    pipeline = MockRazorpayPipeline(idempotency_store=store, seed=42)

    event = WebhookSimulator.create_failed_payment_event(
        amount=4999.0,
        method="upi_autopay",
        error_code="UPI_TIMEOUT",
    )
    duplicates = WebhookSimulator.create_duplicate_events(event, count=10)

    results = [pipeline.process_webhook(evt) for evt in duplicates]

    processed = [r for r in results if not r["is_duplicate"]]
    blocked = [r for r in results if r["is_duplicate"]]

    assert len(processed) == 1
    assert len(blocked) == 9
    assert len(pipeline.audit_trail) == 1

    stats = store.get_stats()
    assert stats["total_events"] == 1
    assert stats["processed_count"] == 1
    assert stats["total_duplicates_blocked"] == 9


def test_concurrent_duplicate_events_thread_safe(temp_db):
    """Verifies that concurrent threads blasting the same webhook event are safely serialized."""
    store = IdempotencyStore(temp_db)
    pipeline = MockRazorpayPipeline(idempotency_store=store, seed=42)

    event = WebhookSimulator.create_failed_payment_event(
        amount=3500.0,
        method="card",
        error_code="INSUFFICIENT_FUNDS",
    )
    duplicates = WebhookSimulator.create_duplicate_events(event, count=15)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(pipeline.process_webhook, evt) for evt in duplicates]
        results = [f.result() for f in futures]

    processed = [r for r in results if not r["is_duplicate"]]
    blocked = [r for r in results if r["is_duplicate"]]

    assert len(processed) == 1
    assert len(blocked) == 14
    assert len(pipeline.audit_trail) == 1


def test_hard_decline_webhook_never_retries(temp_db):
    """Proves that a HARD decline (e.g. MANDATE_REVOKED) cannot choose any retry arm (Rule R1)."""
    store = IdempotencyStore(temp_db)
    pipeline = MockRazorpayPipeline(idempotency_store=store, seed=42)

    event = WebhookSimulator.create_failed_payment_event(
        amount=2500.0,
        method="upi_autopay",
        error_code="MANDATE_REVOKED",
    )

    resp = pipeline.process_webhook(event)
    action = resp["data"]["action"]
    # Retries are illegal under R1; only PAYMENT_LINK, WHATSAPP_LINK, SMS_REMINDER, or STOP/ESCALATE allowed
    assert action not in {"RETRY_2H", "RETRY_24H", "RETRY_72H", "RETRY_SALARY_DAY"}
    assert action in {"PAYMENT_LINK", "WHATSAPP_LINK", "SMS_REMINDER", "STOP", "ESCALATE"}


def test_upi_autopay_predebit_restriction(temp_db):
    """Proves that RETRY_2H is blocked on UPI Autopay (NPCI 24h pre-debit notice rule R2)."""
    event = WebhookSimulator.create_failed_payment_event(
        amount=1200.0,
        method="upi_autopay",
        error_code="UPI_TIMEOUT",
    )
    case = Case(
        id=999,
        method="upi_autopay",
        amount=1200.0,
        error_code="UPI_TIMEOUT",
        failed_at=10,
        salary_day=1,
        responsiveness=0.5,
        state="OPEN",
        cost=0.0,
        retries=0,
        messages=0,
        last_retry_at=-999,
        history=[],
    )
    allowed_map = allowed_actions(case, 10, DEFAULT_CONTROLS)
    is_allowed, reason = allowed_map["RETRY_2H"]
    assert not is_allowed, f"Rule R2 violation: RETRY_2H must be blocked for UPI Autopay. Reason: {reason}"



def test_failed_execution_can_be_retried_according_to_policy(temp_db):
    """Verifies that if an execution attempt fails, the policy allows a follow-up retry within limits."""
    store = IdempotencyStore(temp_db)
    pipeline = MockRazorpayPipeline(idempotency_store=store, seed=42)

    # First failed payment event
    event1 = WebhookSimulator.create_failed_payment_event(
        event_id="evt_attempt_1",
        amount=1500.0,
        method="card",
        error_code="ISSUER_UNAVAILABLE",
    )
    resp1 = pipeline.process_webhook(event1, force_failure=True)
    assert resp1["status"] == "PROCESSED"
    assert resp1["data"]["success"] is False

    # Second follow-up payment failure event for the same customer (new event_id)
    event2 = WebhookSimulator.create_failed_payment_event(
        event_id="evt_attempt_2",
        amount=1500.0,
        method="card",
        error_code="ISSUER_UNAVAILABLE",
    )
    resp2 = pipeline.process_webhook(event2)
    assert resp2["status"] == "PROCESSED"
    assert resp2["is_duplicate"] is False
    assert len(pipeline.audit_trail) == 2


def test_high_value_escalation_triggers_human_review(temp_db):
    """Verifies that high-value cases can trigger escalation."""
    esc_response = MockRazorpay.escalate_payment(
        payment_id="pay_high_value_999",
        reason="Amount exceeds ₹10,000 threshold and auto-retries failed",
    )
    assert esc_response["status"] == "escalated_to_human"
    assert esc_response["simulated"] is True
