import json
import logging
from datetime import datetime, timezone

from db.database import get_db
from db.models import PaymentStatus, AuditEventType
from audit.logger import audit_logger

logger = logging.getLogger(__name__)


async def handle_webhook(event_type: str, payload: dict) -> dict:
    if event_type == "payment.authorized":
        return await _handle_payment_authorized(payload)
    elif event_type == "payment.captured":
        return await _handle_payment_captured(payload)
    elif event_type == "payment.failed":
        return await _handle_payment_failed(payload)
    elif event_type == "order.paid":
        return await _handle_order_paid(payload)
    logger.warning("Unhandled webhook event type: %s", event_type)
    return {"status": "ignored", "event": event_type}


async def _handle_payment_authorized(payload: dict) -> dict:
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE payments SET
               razorpay_payment_id = ?, status = ?, webhook_payload = ?, updated_at = ?
               WHERE razorpay_order_id = ?""",
            (razorpay_payment_id, PaymentStatus.AUTHORIZED.value, json.dumps(payload), now, razorpay_order_id),
        )
        if cursor.rowcount == 0:
            logger.error("Webhook payment.authorized: no payment found for order %s", razorpay_order_id)
            return {"status": "error", "event": "payment.authorized", "reason": "no_matching_payment"}
        await db.commit()

        cursor = await db.execute(
            "SELECT session_id FROM payments WHERE razorpay_order_id = ?",
            (razorpay_order_id,),
        )
        row = await cursor.fetchone()
        if row:
            await audit_logger.log(
                session_id=row["session_id"],
                event_type=AuditEventType.PAYMENT_AUTHORIZED,
                details={"razorpay_payment_id": razorpay_payment_id},
                razorpay_refs={"order_id": razorpay_order_id, "payment_id": razorpay_payment_id},
            )
    finally:
        await db.close()

    return {"status": "processed", "event": "payment.authorized"}


async def _handle_payment_captured(payload: dict) -> dict:
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE payments SET
               razorpay_payment_id = ?, status = ?, webhook_payload = ?, updated_at = ?
               WHERE razorpay_order_id = ?""",
            (razorpay_payment_id, PaymentStatus.CAPTURED.value, json.dumps(payload), now, razorpay_order_id),
        )
        if cursor.rowcount == 0:
            logger.error("Webhook payment.captured: no payment found for order %s", razorpay_order_id)
            return {"status": "error", "event": "payment.captured", "reason": "no_matching_payment"}
        await db.commit()

        cursor = await db.execute(
            "SELECT session_id, mandate_id FROM payments WHERE razorpay_order_id = ?",
            (razorpay_order_id,),
        )
        row = await cursor.fetchone()
        if row:
            await audit_logger.log(
                session_id=row["session_id"],
                event_type=AuditEventType.PAYMENT_CAPTURED,
                details={"razorpay_payment_id": razorpay_payment_id, "amount": payment_entity.get("amount")},
                razorpay_refs={"order_id": razorpay_order_id, "payment_id": razorpay_payment_id},
            )
            await db.execute(
                "UPDATE sessions SET status = 'completed', updated_at = ? WHERE id = ?",
                (now, row["session_id"]),
            )
            await db.commit()
    finally:
        await db.close()

    return {"status": "processed", "event": "payment.captured"}


async def _handle_payment_failed(payload: dict) -> dict:
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")
    error = payment_entity.get("error_description", "Unknown error")
    failed_amount = payment_entity.get("amount", 0)
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE payments SET
               razorpay_payment_id = ?, status = ?, webhook_payload = ?, updated_at = ?
               WHERE razorpay_order_id = ?""",
            (razorpay_payment_id, PaymentStatus.FAILED.value, json.dumps(payload), now, razorpay_order_id),
        )
        if cursor.rowcount == 0:
            logger.error("Webhook payment.failed: no payment found for order %s", razorpay_order_id)
            return {"status": "error", "event": "payment.failed", "reason": "no_matching_payment"}
        await db.commit()

        cursor = await db.execute(
            "SELECT session_id, amount FROM payments WHERE razorpay_order_id = ?",
            (razorpay_order_id,),
        )
        row = await cursor.fetchone()
        if row:
            rollback_amount = row["amount"] or failed_amount
            if rollback_amount > 0:
                await db.execute(
                    "UPDATE sessions SET budget_spent = MAX(0, budget_spent - ?), updated_at = ? WHERE id = ?",
                    (rollback_amount, now, row["session_id"]),
                )
                await db.commit()

            await audit_logger.log(
                session_id=row["session_id"],
                event_type=AuditEventType.PAYMENT_FAILED,
                details={
                    "razorpay_payment_id": razorpay_payment_id,
                    "error": error,
                    "budget_rolled_back": rollback_amount,
                },
                razorpay_refs={"order_id": razorpay_order_id, "payment_id": razorpay_payment_id},
            )
    finally:
        await db.close()

    return {"status": "processed", "event": "payment.failed"}


async def _handle_order_paid(payload: dict) -> dict:
    logger.info("Received order.paid webhook: %s", json.dumps(payload.get("payload", {}).get("order", {}).get("entity", {}).get("id", "unknown")))
    return {"status": "processed", "event": "order.paid"}
