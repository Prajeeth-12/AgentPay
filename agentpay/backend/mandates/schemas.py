from pydantic import BaseModel
from typing import Optional


class MerchantInfo(BaseModel):
    id: str
    name: str
    website: str = ""


class LineItem(BaseModel):
    id: str
    product_id: str
    title: str
    price: int  # paise
    currency: str = "INR"
    quantity: int = 1


class CheckoutPayload(BaseModel):
    order_id: str
    merchant: MerchantInfo
    line_items: list[LineItem]
    total_price: int  # paise
    currency: str = "INR"


class AmountRangeConstraint(BaseModel):
    type: str = "checkout.amount_range"
    max: int  # paise
    min: int = 0
    currency: str = "INR"


class AllowedMerchantsConstraint(BaseModel):
    type: str = "checkout.allowed_merchants"
    allowed: list[MerchantInfo]


class BudgetConstraint(BaseModel):
    type: str = "payment.budget"
    max: int  # paise
    currency: str = "INR"


class PaymentAmountRangeConstraint(BaseModel):
    type: str = "payment.amount_range"
    max: int
    min: int = 0
    currency: str = "INR"


class OpenCheckoutMandate(BaseModel):
    vct: str = "mandate.checkout.open.1"
    constraints: list[dict]
    cnf: dict  # {"jwk": {...}}  agent's public key
    iat: int
    exp: int


class ClosedCheckoutMandate(BaseModel):
    vct: str = "mandate.checkout.1"
    checkout_hash: str
    checkout: CheckoutPayload
    aud: str = ""
    iat: int


class OpenPaymentMandate(BaseModel):
    vct: str = "mandate.payment.open.1"
    constraints: list[dict]
    cnf: dict
    iat: int
    exp: int


class ClosedPaymentMandate(BaseModel):
    vct: str = "mandate.payment.1"
    transaction_id: str  # links to checkout_hash
    payee: MerchantInfo
    payment_amount: dict  # {"amount": int, "currency": str}
    payment_instrument: dict  # {"id": str, "type": str, "description": str}
    aud: str = "credential-provider"
    iat: int
