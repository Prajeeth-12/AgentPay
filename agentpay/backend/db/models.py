from pydantic import BaseModel
from typing import Optional
from enum import Enum


class AgentStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    VIOLATED = "violated"


class MandateType(str, Enum):
    OPEN_CHECKOUT = "open_checkout"
    CLOSED_CHECKOUT = "closed_checkout"
    OPEN_PAYMENT = "open_payment"
    CLOSED_PAYMENT = "closed_payment"


class MandateStatus(str, Enum):
    CREATED = "created"
    SIGNED = "signed"
    VERIFIED = "verified"
    VIOLATED = "violated"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    CREATED = "created"
    LINK_SENT = "link_sent"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class AuditEventType(str, Enum):
    INTENT_REGISTERED = "INTENT_REGISTERED"
    UAP_AGENT_VERIFIED = "UAP_AGENT_VERIFIED"
    OPEN_MANDATE_CREATED = "OPEN_MANDATE_CREATED"
    CATALOG_SEARCHED = "CATALOG_SEARCHED"
    PRODUCTS_PRESENTED = "PRODUCTS_PRESENTED"
    USER_SELECTED_PRODUCT = "USER_SELECTED_PRODUCT"
    CART_UPDATED = "CART_UPDATED"
    CLOSED_CHECKOUT_SIGNED = "CLOSED_CHECKOUT_SIGNED"
    CONSTRAINT_CHECK_PASSED = "CONSTRAINT_CHECK_PASSED"
    CONSTRAINT_CHECK_FAILED = "CONSTRAINT_CHECK_FAILED"
    MANDATE_VIOLATION_BLOCKED = "MANDATE_VIOLATION_BLOCKED"
    CLOSED_PAYMENT_SIGNED = "CLOSED_PAYMENT_SIGNED"
    RAZORPAY_ORDER_CREATED = "RAZORPAY_ORDER_CREATED"
    PAYMENT_LINK_CREATED = "PAYMENT_LINK_CREATED"
    PAYMENT_LINK_SENT = "PAYMENT_LINK_SENT"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    TRANSACTION_COMPLETE = "TRANSACTION_COMPLETE"
    SESSION_EXPIRED = "SESSION_EXPIRED"


class AgentModel(BaseModel):
    id: str
    name: str
    public_key_jwk: str
    status: AgentStatus = AgentStatus.ACTIVE
    max_budget: int
    registered_at: str


class SessionModel(BaseModel):
    id: str
    agent_id: str
    user_intent: Optional[str] = None
    parsed_intent: Optional[str] = None
    budget_limit: int
    budget_spent: int = 0
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: str
    updated_at: str


class MandateModel(BaseModel):
    id: str
    session_id: str
    type: MandateType
    vct: str
    payload: str
    sd_jwt: Optional[str] = None
    mandate_hash: Optional[str] = None
    constraints: Optional[str] = None
    status: MandateStatus = MandateStatus.CREATED
    parent_id: Optional[str] = None
    signed_by: Optional[str] = None
    created_at: str


class CartItemModel(BaseModel):
    id: str
    session_id: str
    product_id: str
    product_title: str
    price: int
    quantity: int = 1
    added_at: str


class PaymentModel(BaseModel):
    id: str
    session_id: str
    mandate_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_link_id: Optional[str] = None
    razorpay_link_url: Optional[str] = None
    amount: int
    currency: str = "INR"
    status: PaymentStatus = PaymentStatus.CREATED
    razorpay_signature: Optional[str] = None
    webhook_payload: Optional[str] = None
    created_at: str
    updated_at: str


class AuditEntryModel(BaseModel):
    id: Optional[int] = None
    session_id: str
    timestamp: str
    event_type: AuditEventType
    agent_id: Optional[str] = None
    mandate_id: Optional[str] = None
    mandate_type: Optional[str] = None
    details: str
    razorpay_refs: Optional[str] = None
    constraint_check: Optional[str] = None
