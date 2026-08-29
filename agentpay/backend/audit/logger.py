import json
from datetime import datetime, timezone
from typing import Optional

from db.database import get_db
from db.models import AuditEventType


class AuditLogger:
    async def log(
        self,
        session_id: str,
        event_type: AuditEventType,
        details: dict,
        agent_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        mandate_type: Optional[str] = None,
        razorpay_refs: Optional[dict] = None,
        constraint_check: Optional[dict] = None,
    ) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "session_id": session_id,
            "timestamp": timestamp,
            "event_type": event_type.value,
            "agent_id": agent_id,
            "mandate_id": mandate_id,
            "mandate_type": mandate_type,
            "details": json.dumps(details),
            "razorpay_refs": json.dumps(razorpay_refs) if razorpay_refs else None,
            "constraint_check": json.dumps(constraint_check) if constraint_check else None,
        }

        db = await get_db()
        try:
            cursor = await db.execute(
                """INSERT INTO audit_log
                   (session_id, timestamp, event_type, agent_id, mandate_id,
                    mandate_type, details, razorpay_refs, constraint_check)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["session_id"],
                    entry["timestamp"],
                    entry["event_type"],
                    entry["agent_id"],
                    entry["mandate_id"],
                    entry["mandate_type"],
                    entry["details"],
                    entry["razorpay_refs"],
                    entry["constraint_check"],
                ),
            )
            await db.commit()
            entry["id"] = cursor.lastrowid
        finally:
            await db.close()

        return entry

    async def get_trail(self, session_id: str) -> list[dict]:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM audit_log WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "agent_id": row["agent_id"],
                    "mandate_id": row["mandate_id"],
                    "mandate_type": row["mandate_type"],
                    "details": json.loads(row["details"]),
                    "razorpay_refs": json.loads(row["razorpay_refs"]) if row["razorpay_refs"] else None,
                    "constraint_check": json.loads(row["constraint_check"]) if row["constraint_check"] else None,
                }
                for row in rows
            ]
        finally:
            await db.close()


audit_logger = AuditLogger()
