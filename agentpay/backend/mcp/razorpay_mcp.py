"""
Razorpay MCP (Model Context Protocol) integration layer.

Wraps Razorpay's MCP Server capabilities into tools the shopping agent can use.
Adds refund handling, payment status tracking, QR code generation, and
settlement queries beyond what the basic SDK provides.
"""

import asyncio
import logging

from config import get_settings
from payments.razorpay_client import get_razorpay_client

logger = logging.getLogger(__name__)


async def fetch_payment_status(razorpay_order_id: str) -> dict:
    """MCP-style: fetch all payments for an order and return enriched status."""
    client = get_razorpay_client()
    try:
        payments = await asyncio.to_thread(client.order.payments, razorpay_order_id)
        items = payments.get("items", [])
        if not items:
            return {
                "status": "no_payments",
                "order_id": razorpay_order_id,
                "message": "No payments attempted yet for this order",
            }

        latest = items[0]
        return {
            "status": latest.get("status", "unknown"),
            "order_id": razorpay_order_id,
            "payment_id": latest.get("id"),
            "amount": latest.get("amount"),
            "method": latest.get("method"),
            "bank": latest.get("bank"),
            "wallet": latest.get("wallet"),
            "vpa": latest.get("vpa"),
            "error_code": latest.get("error_code"),
            "error_description": latest.get("error_description"),
            "created_at": latest.get("created_at"),
        }
    except Exception as e:
        logger.error("MCP fetch_payment_status failed: %s", e)
        return {"status": "error", "order_id": razorpay_order_id, "error": str(e)}


async def create_qr_code(amount_paise: int, description: str, session_id: str) -> dict:
    """MCP-style: create a Razorpay QR Code for UPI payment."""
    client = get_razorpay_client()
    try:
        qr_data = {
            "type": "upi_qr",
            "name": f"AgentPay QR - {description}",
            "usage": "single_use",
            "fixed_amount": True,
            "payment_amount": amount_paise,
            "description": description,
            "notes": {"session_id": session_id, "source": "agentpay_mcp"},
        }
        result = await asyncio.to_thread(client.qrcode.create, data=qr_data)
        return {
            "qr_id": result.get("id"),
            "image_url": result.get("image_url"),
            "short_url": result.get("short_url"),
            "amount": amount_paise,
            "status": result.get("status"),
        }
    except Exception as e:
        logger.error("MCP create_qr_code failed: %s", e)
        return {"error": str(e)}


async def initiate_refund(payment_id: str, amount_paise: int, reason: str = "customer_request") -> dict:
    """MCP-style: create a refund for a captured payment."""
    client = get_razorpay_client()
    try:
        refund_data = {
            "amount": amount_paise,
            "speed": "normal",
            "notes": {"reason": reason, "source": "agentpay_mcp"},
        }
        result = await asyncio.to_thread(client.payment.refund, payment_id, refund_data)
        return {
            "refund_id": result.get("id"),
            "payment_id": payment_id,
            "amount": result.get("amount"),
            "status": result.get("status"),
            "speed_processed": result.get("speed_processed"),
        }
    except Exception as e:
        logger.error("MCP initiate_refund failed: %s", e)
        return {"error": str(e)}


async def fetch_settlements(count: int = 10) -> dict:
    """MCP-style: fetch recent settlements for reconciliation."""
    client = get_razorpay_client()
    try:
        result = await asyncio.to_thread(client.settlement.all, {"count": count})
        items = result.get("items", [])
        return {
            "count": len(items),
            "settlements": [
                {
                    "id": s.get("id"),
                    "amount": s.get("amount"),
                    "status": s.get("status"),
                    "utr": s.get("utr"),
                    "created_at": s.get("created_at"),
                }
                for s in items
            ],
        }
    except Exception as e:
        logger.error("MCP fetch_settlements failed: %s", e)
        return {"error": str(e)}


async def detect_payment_method_preference(session_id: str) -> dict:
    """MCP-style: suggest optimal payment method based on amount and context."""
    settings = get_settings()
    return {
        "recommendations": [
            {"method": "upi", "reason": "Fastest for Indian payments, zero additional cost"},
            {"method": "payment_link", "reason": "Works across all devices, supports all methods"},
            {"method": "qr_code", "reason": "Ideal for in-person or quick mobile payments"},
        ],
        "default": "payment_link",
        "mcp_server": "razorpay/mcp",
        "mcp_version": "1.0",
    }
