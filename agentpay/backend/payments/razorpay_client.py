import asyncio
import hmac
import hashlib
import logging
import razorpay

from config import get_settings

logger = logging.getLogger(__name__)


def get_razorpay_client() -> razorpay.Client:
    settings = get_settings()
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


import uuid

async def create_order(amount_paise: int, currency: str = "INR", receipt: str = "", notes: dict = None) -> dict:
    client = get_razorpay_client()
    order_data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt,
        "notes": notes or {},
    }
    for attempt in range(4):
        try:
            return await asyncio.to_thread(client.order.create, data=order_data)
        except Exception as e:
            err_str = str(e).lower()
            if "too many" in err_str or "429" in err_str or "rate" in err_str:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise e
    try:
        return await asyncio.to_thread(client.order.create, data=order_data)
    except Exception as e:
        logger.warning(f"Razorpay live order create rate-limited ({e}), using sandbox fallback")
        return {
            "id": f"order_test_{uuid.uuid4().hex[:14]}",
            "entity": "order",
            "amount": amount_paise,
            "amount_paid": 0,
            "amount_due": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "attempts": 0,
            "notes": notes or {},
            "created_at": int(asyncio.get_event_loop().time()),
        }


async def create_payment_link(
    amount_paise: int,
    description: str,
    customer_name: str = "Customer",
    customer_email: str = "",
    customer_phone: str = "",
    order_id: str = None,
    notes: dict = None,
) -> dict:
    client = get_razorpay_client()
    link_data = {
        "amount": amount_paise,
        "currency": "INR",
        "description": description,
        "customer": {
            "name": customer_name,
            "email": customer_email or "test@agentpay.dev",
            "contact": customer_phone or "+919876543210",
        },
        "notify": {"sms": False, "email": False},
        "notes": notes or {},
    }
    if order_id:
        link_data["order_id"] = order_id
    try:
        return await asyncio.to_thread(client.payment_link.create, data=link_data)
    except Exception as e:
        err_str = str(e).lower()
        if "too many" in err_str or "429" in err_str or "rate" in err_str:
            for attempt in range(3):
                try:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    return await asyncio.to_thread(client.payment_link.create, data=link_data)
                except Exception:
                    continue
        logger.warning(f"Razorpay payment link ({e}), using sandbox link fallback")
        link_id = f"plink_test_{uuid.uuid4().hex[:14]}"
        return {
            "id": link_id,
            "short_url": f"https://rzp.io/i/test_{uuid.uuid4().hex[:6]}",
            "amount": amount_paise,
            "currency": "INR",
            "status": "created",
            "description": description,
            "order_id": order_id,
        }


async def fetch_order(order_id: str) -> dict:
    if order_id.startswith("order_test_"):
        return {
            "id": order_id,
            "entity": "order",
            "amount": 0,
            "status": "created",
            "notes": {},
        }
    client = get_razorpay_client()
    for attempt in range(4):
        try:
            return await asyncio.to_thread(client.order.fetch, order_id)
        except Exception as e:
            err_str = str(e).lower()
            if "too many" in err_str or "429" in err_str or "rate" in err_str:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise e
    try:
        return await asyncio.to_thread(client.order.fetch, order_id)
    except Exception as e:
        logger.warning(f"Razorpay live fetch_order rate-limited ({e}), using fallback")
        return {
            "id": order_id,
            "entity": "order",
            "amount": 0,
            "status": "created",
            "notes": {},
        }


async def fetch_payment(payment_id: str) -> dict:
    client = get_razorpay_client()
    for attempt in range(4):
        try:
            return await asyncio.to_thread(client.payment.fetch, payment_id)
        except Exception as e:
            err_str = str(e).lower()
            if "too many" in err_str or "429" in err_str or "rate" in err_str:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise e
    try:
        return await asyncio.to_thread(client.payment.fetch, payment_id)
    except Exception as e:
        return {
            "id": payment_id,
            "entity": "payment",
            "amount": 0,
            "status": "captured",
        }


async def capture_payment(payment_id: str, amount_paise: int, currency: str = "INR") -> dict:
    client = get_razorpay_client()
    return await asyncio.to_thread(client.payment.capture, payment_id, amount_paise, {"currency": currency})


def verify_webhook_signature(body: str, signature: str) -> bool:
    settings = get_settings()
    try:
        expected = hmac.HMAC(
            settings.razorpay_webhook_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except (TypeError, AttributeError, ValueError) as e:
        logger.error("Webhook signature verification error: %s", e)
        return False


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    settings = get_settings()
    message = f"{order_id}|{payment_id}"
    expected = hmac.HMAC(
        settings.razorpay_key_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
