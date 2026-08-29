import json
import time
import uuid
from datetime import datetime, timezone

from db.database import get_db
from db.models import MandateType, MandateStatus, AuditEventType
from mandates.crypto import sign_mandate, verify_mandate, hash_mandate
from mandates.schemas import (
    OpenCheckoutMandate,
    ClosedCheckoutMandate,
    OpenPaymentMandate,
    ClosedPaymentMandate,
    CheckoutPayload,
    MerchantInfo,
    LineItem,
)
from mandates.constraints import validate_closed_against_open
from audit.logger import audit_logger


class MandateManager:
    async def create_open_mandates(
        self,
        session_id: str,
        agent_id: str,
        budget_limit: int,
        agent_public_key_jwk: dict,
        private_key_pem: str,
        allowed_merchants: list[dict] = None,
    ) -> dict:
        """Create both open checkout and open payment mandates for a session."""
        now = int(time.time())
        expiry = now + 3600  # 1 hour

        checkout_constraints = [
            {"type": "checkout.amount_range", "max": budget_limit, "min": 0, "currency": "INR"},
        ]
        if allowed_merchants:
            checkout_constraints.append({
                "type": "checkout.allowed_merchants",
                "allowed": allowed_merchants,
            })

        open_checkout = OpenCheckoutMandate(
            constraints=checkout_constraints,
            cnf={"jwk": agent_public_key_jwk},
            iat=now,
            exp=expiry,
        )

        payment_constraints = [
            {"type": "payment.amount_range", "max": budget_limit, "min": 0, "currency": "INR"},
            {"type": "payment.budget", "max": budget_limit, "currency": "INR"},
        ]

        open_payment = OpenPaymentMandate(
            constraints=payment_constraints,
            cnf={"jwk": agent_public_key_jwk},
            iat=now,
            exp=expiry,
        )

        checkout_jwt = sign_mandate(open_checkout.model_dump(), private_key_pem, open_checkout.vct)
        payment_jwt = sign_mandate(open_payment.model_dump(), private_key_pem, open_payment.vct)

        checkout_id = f"mnd_oc_{uuid.uuid4().hex[:8]}"
        payment_id = f"mnd_op_{uuid.uuid4().hex[:8]}"

        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO mandates (id, session_id, type, vct, payload, sd_jwt, mandate_hash, constraints, status, signed_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    checkout_id, session_id, MandateType.OPEN_CHECKOUT.value,
                    open_checkout.vct, json.dumps(open_checkout.model_dump()),
                    checkout_jwt, hash_mandate(checkout_jwt),
                    json.dumps(checkout_constraints), MandateStatus.SIGNED.value,
                    "user", datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.execute(
                """INSERT INTO mandates (id, session_id, type, vct, payload, sd_jwt, mandate_hash, constraints, status, signed_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payment_id, session_id, MandateType.OPEN_PAYMENT.value,
                    open_payment.vct, json.dumps(open_payment.model_dump()),
                    payment_jwt, hash_mandate(payment_jwt),
                    json.dumps(payment_constraints), MandateStatus.SIGNED.value,
                    "user", datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

        await audit_logger.log(
            session_id=session_id,
            event_type=AuditEventType.OPEN_MANDATE_CREATED,
            details={
                "open_checkout_id": checkout_id,
                "open_payment_id": payment_id,
                "budget_limit": budget_limit,
                "constraints": checkout_constraints + payment_constraints,
            },
            agent_id=agent_id,
            mandate_id=checkout_id,
            mandate_type="open_checkout",
        )

        return {
            "open_checkout": {
                "id": checkout_id,
                "vct": open_checkout.vct,
                "constraints": checkout_constraints,
                "jwt": checkout_jwt,
                "hash": hash_mandate(checkout_jwt),
            },
            "open_payment": {
                "id": payment_id,
                "vct": open_payment.vct,
                "constraints": payment_constraints,
                "jwt": payment_jwt,
                "hash": hash_mandate(payment_jwt),
            },
        }

    async def create_closed_checkout(
        self,
        session_id: str,
        agent_id: str,
        private_key_pem: str,
        order_id: str,
        merchant: dict,
        line_items: list[dict],
        total_price: int,
    ) -> dict:
        """Create a closed checkout mandate after cart is finalized."""
        open_mandate = await self._get_open_mandate(session_id, MandateType.OPEN_CHECKOUT)
        if not open_mandate:
            raise ValueError("No open checkout mandate found for session")

        open_constraints = json.loads(open_mandate["constraints"]) if open_mandate["constraints"] else []

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT budget_spent FROM sessions WHERE id = ?", (session_id,)
            )
            session_row = await cursor.fetchone()
            budget_spent = session_row["budget_spent"] if session_row else 0
        finally:
            await db.close()

        checkout_payload = {
            "total_price": total_price,
            "merchant": merchant,
        }
        validation = validate_closed_against_open(checkout_payload, open_constraints, budget_spent)

        if not validation["passed"]:
            await audit_logger.log(
                session_id=session_id,
                event_type=AuditEventType.MANDATE_VIOLATION_BLOCKED,
                details={
                    "attempted_total": total_price,
                    "violations": validation.get("violations", []),
                },
                agent_id=agent_id,
                mandate_id=open_mandate["id"],
                mandate_type="open_checkout",
                constraint_check=validation,
            )
            return {"error": True, "validation": validation}

        now = int(time.time())
        checkout = CheckoutPayload(
            order_id=order_id,
            merchant=MerchantInfo(**merchant),
            line_items=[LineItem(**item) for item in line_items],
            total_price=total_price,
        )

        checkout_jwt_payload = json.dumps(checkout.model_dump(), sort_keys=True)
        checkout_hash = hash_mandate(checkout_jwt_payload)

        closed = ClosedCheckoutMandate(
            checkout_hash=checkout_hash,
            checkout=checkout,
            iat=now,
        )

        closed_jwt = sign_mandate(closed.model_dump(), private_key_pem, closed.vct)
        closed_id = f"mnd_cc_{uuid.uuid4().hex[:8]}"

        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO mandates (id, session_id, type, vct, payload, sd_jwt, mandate_hash, constraints, status, parent_id, signed_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    closed_id, session_id, MandateType.CLOSED_CHECKOUT.value,
                    closed.vct, json.dumps(closed.model_dump()),
                    closed_jwt, hash_mandate(closed_jwt),
                    None, MandateStatus.VERIFIED.value,
                    open_mandate["id"], "agent",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

        await audit_logger.log(
            session_id=session_id,
            event_type=AuditEventType.CLOSED_CHECKOUT_SIGNED,
            details={
                "closed_checkout_id": closed_id,
                "checkout_hash": checkout_hash,
                "total_price": total_price,
                "line_items": line_items,
            },
            agent_id=agent_id,
            mandate_id=closed_id,
            mandate_type="closed_checkout",
            constraint_check={"passed": True, "total_price": total_price},
        )

        return {
            "id": closed_id,
            "vct": closed.vct,
            "checkout_hash": checkout_hash,
            "total_price": total_price,
            "jwt": closed_jwt,
            "hash": hash_mandate(closed_jwt),
            "parent_id": open_mandate["id"],
        }

    async def create_closed_payment(
        self,
        session_id: str,
        agent_id: str,
        private_key_pem: str,
        checkout_hash: str,
        merchant: dict,
        amount: int,
        payment_instrument: dict = None,
    ) -> dict:
        """Create a closed payment mandate after checkout is finalized."""
        open_mandate = await self._get_open_mandate(session_id, MandateType.OPEN_PAYMENT)
        if not open_mandate:
            raise ValueError("No open payment mandate found for session")

        open_constraints = json.loads(open_mandate["constraints"]) if open_mandate["constraints"] else []

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT budget_spent FROM sessions WHERE id = ?", (session_id,)
            )
            session_row = await cursor.fetchone()
            budget_spent = session_row["budget_spent"] if session_row else 0
        finally:
            await db.close()

        payment_payload = {
            "payment_amount": {"amount": amount, "currency": "INR"},
            "payee": merchant,
        }
        validation = validate_closed_against_open(payment_payload, open_constraints, budget_spent)

        if not validation["passed"]:
            await audit_logger.log(
                session_id=session_id,
                event_type=AuditEventType.MANDATE_VIOLATION_BLOCKED,
                details={
                    "attempted_amount": amount,
                    "violations": validation.get("violations", []),
                },
                agent_id=agent_id,
                mandate_id=open_mandate["id"],
                mandate_type="open_payment",
                constraint_check=validation,
            )
            return {"error": True, "validation": validation}

        now = int(time.time())
        instrument = payment_instrument or {"id": "stub", "type": "razorpay_link", "description": "Razorpay Payment Link"}

        closed = ClosedPaymentMandate(
            transaction_id=checkout_hash,
            payee=MerchantInfo(**merchant),
            payment_amount={"amount": amount, "currency": "INR"},
            payment_instrument=instrument,
            iat=now,
        )

        closed_jwt = sign_mandate(closed.model_dump(), private_key_pem, closed.vct)
        closed_id = f"mnd_cp_{uuid.uuid4().hex[:8]}"

        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO mandates (id, session_id, type, vct, payload, sd_jwt, mandate_hash, constraints, status, parent_id, signed_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    closed_id, session_id, MandateType.CLOSED_PAYMENT.value,
                    closed.vct, json.dumps(closed.model_dump()),
                    closed_jwt, hash_mandate(closed_jwt),
                    None, MandateStatus.VERIFIED.value,
                    open_mandate["id"], "agent",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

        await audit_logger.log(
            session_id=session_id,
            event_type=AuditEventType.CLOSED_PAYMENT_SIGNED,
            details={
                "closed_payment_id": closed_id,
                "transaction_id": checkout_hash,
                "amount": amount,
            },
            agent_id=agent_id,
            mandate_id=closed_id,
            mandate_type="closed_payment",
            constraint_check={"passed": True, "amount": amount},
        )

        return {
            "id": closed_id,
            "vct": closed.vct,
            "transaction_id": checkout_hash,
            "amount": amount,
            "jwt": closed_jwt,
            "hash": hash_mandate(closed_jwt),
            "parent_id": open_mandate["id"],
        }

    async def get_session_mandates(self, session_id: str) -> list[dict]:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM mandates WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            )
            rows = await cursor.fetchall()
        finally:
            await db.close()

        return [
            {
                "id": row["id"],
                "type": row["type"],
                "vct": row["vct"],
                "status": row["status"],
                "mandate_hash": row["mandate_hash"],
                "parent_id": row["parent_id"],
                "signed_by": row["signed_by"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload"]) if row["payload"] else None,
                "constraints": json.loads(row["constraints"]) if row["constraints"] else None,
            }
            for row in rows
        ]

    async def _get_open_mandate(self, session_id: str, mandate_type: MandateType) -> dict | None:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM mandates WHERE session_id = ? AND type = ? AND status = 'signed'",
                (session_id, mandate_type.value),
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if not row:
            return None
        return dict(row)


mandate_manager = MandateManager()
