import hmac
import hashlib
import razorpay

from config import get_settings


def get_razorpay_client() -> razorpay.Client:
    settings = get_settings()
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


async def create_order(amount_paise: int, currency: str = "INR", receipt: str = "", notes: dict = None) -> dict:
    client = get_razorpay_client()
    order_data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt,
        "notes": notes or {},
    }
    return client.order.create(data=order_data)


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
            "contact": customer_phone or "+919999999999",
        },
        "notify": {"sms": False, "email": False},
        "notes": notes or {},
    }
    if order_id:
        link_data["order_id"] = order_id
    return client.payment_link.create(data=link_data)


async def fetch_order(order_id: str) -> dict:
    client = get_razorpay_client()
    return client.order.fetch(order_id)


async def fetch_payment(payment_id: str) -> dict:
    client = get_razorpay_client()
    return client.payment.fetch(payment_id)


async def capture_payment(payment_id: str, amount_paise: int, currency: str = "INR") -> dict:
    client = get_razorpay_client()
    return client.payment.capture(payment_id, amount_paise, {"currency": currency})


def verify_webhook_signature(body: str, signature: str) -> bool:
    settings = get_settings()
    try:
        expected = hmac.HMAC(
            settings.razorpay_webhook_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
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
