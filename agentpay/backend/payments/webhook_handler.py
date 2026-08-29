import json
from datetime import datetime, timezone

from db.database import get_db
from db.models import PaymentStatus, AuditEventType
from audit.logger import audit_logger


async def handle_webhook(event_type: str, payload: dict) -> dict:
    if event_type == "payment.authorized":
        return await _handle_payment_authorized(payload)
    elif event_type == "payment.captured":
        return await _handle_payment_captured(payload)
    elif event_type == "payment.failed":
        return await _handle_payment_failed(payload)
    elif event_type == "order.paid":
        return await _handle_order_paid(payload)
    return {"status": "ignored", "event": event_type}


async def _handle_payment_authorized(payload: dict) -> dict:
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        await db.execute(
            """UPDATE payments SET
               razorpay_payment_id = ?, status = ?, webhook_payload = ?, updated_at = ?
               WHERE razorpay_order_id = ?""",
            (razorpay_payment_id, PaymentStatus.AUTHORIZED.value, json.dumps(payload), now, razorpay_order_id),
        )
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
        await db.execute(
            """UPDATE payments SET
               razorpay_payment_id = ?, status = ?, webhook_payload = ?, updated_at = ?
               WHERE razorpay_order_id = ?""",
            (razorpay_payment_id, PaymentStatus.CAPTURED.value, json.dumps(payload), now, razorpay_order_id),
        )
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
    now = datetime.now(timezone.utc).isoformat()

    db = await get_db()
    try:
        await db.execute(
            """UPDATE payments SET
               razorpay_payment_id = ?, status = ?, webhook_payload = ?, updated_at = ?
               WHERE razorpay_order_id = ?""",
            (razorpay_payment_id, PaymentStatus.FAILED.value, json.dumps(payload), now, razorpay_order_id),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT session_id FROM payments WHERE razorpay_order_id = ?",
            (razorpay_order_id,),
        )
        row = await cursor.fetchone()
        if row:
            await audit_logger.log(
                session_id=row["session_id"],
                event_type=AuditEventType.PAYMENT_FAILED,
                details={"razorpay_payment_id": razorpay_payment_id, "error": error},
                razorpay_refs={"order_id": razorpay_order_id, "payment_id": razorpay_payment_id},
            )
    finally:
        await db.close()

    return {"status": "processed", "event": "payment.failed"}


async def _handle_order_paid(payload: dict) -> dict:
    return {"status": "processed", "event": "order.paid"}
