import json
from datetime import datetime, timezone
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from db.database import get_db


class UAPRegistry:
    """Simulated NPCI UAP Trust Registry for agent verification."""

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        max_budget: int,
    ) -> dict:
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        public_numbers = public_key.public_numbers()

        jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": _int_to_base64url(public_numbers.x, 32),
            "y": _int_to_base64url(public_numbers.y, 32),
        }

        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        now = datetime.now(timezone.utc).isoformat()

        db = await get_db()
        try:
            await db.execute(
                """INSERT OR REPLACE INTO agents (id, name, public_key_jwk, status, max_budget, registered_at)
                   VALUES (?, ?, ?, 'active', ?, ?)""",
                (agent_id, name, json.dumps(jwk), max_budget, now),
            )
            await db.commit()
        finally:
            await db.close()

        return {
            "agent_id": agent_id,
            "name": name,
            "public_key_jwk": jwk,
            "private_key_pem": private_bytes.decode(),
            "max_budget": max_budget,
            "status": "active",
            "registered_at": now,
        }

    async def verify_agent(self, agent_id: str, requested_budget: int = 0) -> dict:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM agents WHERE id = ?", (agent_id,)
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if not row:
            return {
                "authorized": False,
                "reason": "agent_not_found",
                "agent_id": agent_id,
            }

        if row["status"] != "active":
            return {
                "authorized": False,
                "reason": f"agent_status_{row['status']}",
                "agent_id": agent_id,
            }

        if requested_budget > 0 and requested_budget > row["max_budget"]:
            return {
                "authorized": False,
                "reason": "budget_exceeds_max",
                "agent_id": agent_id,
                "requested": requested_budget,
                "max_allowed": row["max_budget"],
            }

        return {
            "authorized": True,
            "agent_id": agent_id,
            "name": row["name"],
            "public_key_jwk": json.loads(row["public_key_jwk"]),
            "max_budget": row["max_budget"],
            "status": row["status"],
        }

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM agents WHERE id = ?", (agent_id,)
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "public_key_jwk": json.loads(row["public_key_jwk"]),
            "status": row["status"],
            "max_budget": row["max_budget"],
            "registered_at": row["registered_at"],
        }

    async def list_agents(self) -> list[dict]:
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM agents")
            rows = await cursor.fetchall()
        finally:
            await db.close()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "max_budget": row["max_budget"],
                "registered_at": row["registered_at"],
            }
            for row in rows
        ]


def _int_to_base64url(value: int, length: int) -> str:
    import base64
    value_bytes = value.to_bytes(length, byteorder="big")
    return base64.urlsafe_b64encode(value_bytes).rstrip(b"=").decode()


uap_registry = UAPRegistry()
