# Section 2: Transaction Flow & Mandate Lifecycle

## Full Transaction Flow

### Phase 1: Intent & Agent Registration
```
USER: "Buy me running shoes under ₹2,000"

1. Shopping Agent parses intent via Claude
   → product: "running shoes", budget: ₹2,000 max

2. UAP Registry checks: Is this agent registered?
   → Agent ID, public key (ES256 P-256) verified
   → Spending limit checked: ₹2,000 ≤ user's cap
   → Status: AUTHORIZED

3. Mandate Manager creates OPEN CHECKOUT MANDATE
   → vct: "mandate.checkout.open.1"
   → constraints: allowed_merchants, max budget ₹2,000
   → Signed by user (simulated via Trusted Surface)
   → Agent's public key bound via cnf.jwk
   → Audit log entry #1: INTENT_REGISTERED

4. OPEN PAYMENT MANDATE created alongside
   → vct: "mandate.payment.open.1"
   → constraint: payment.amount_range max ₹2,000
   → constraint: payment.budget max ₹2,000
   → Audit log entry #2: PAYMENT_PREAUTHORIZED
```

### Phase 2: Discovery & Cart
```
5. Shopping Agent queries Catalog Service
   → GET /catalog/search?q=running+shoes&max_price=2000
   → Returns JSON-LD product list

6. Agent ranks products, presents top 3 to user
   → "I found 3 options: Nike ₹1,799, Adidas ₹1,899, Puma ₹1,599"

7. User picks: "Nike"

8. Agent builds cart, creates CLOSED CHECKOUT MANDATE
   → vct: "mandate.checkout.1"
   → checkout_jwt: order_id, merchant, line_items, total: ₹1,799
   → checkout_hash: SHA-256 of checkout_jwt
   → Signed by agent's private key (ES256)
   → Verified: ₹1,799 ≤ ₹2,000 budget ✓
   → Audit log entry #3: CART_FINALIZED
```

### Phase 3: Payment Execution
```
9. Mandate Manager creates CLOSED PAYMENT MANDATE
   → vct: "mandate.payment.1"
   → transaction_id links to checkout_hash
   → payment_amount: ₹1,799 INR
   → Verified against open payment mandate ✓
   → Audit log entry #4: PAYMENT_AUTHORIZED

10. Payment Executor calls Razorpay
    → POST /v1/orders {amount: 179900, currency: INR}
    → Creates payment link with order_id
    → Audit log entry #5: RAZORPAY_ORDER_CREATED

11. User completes payment (test mode)
    → Test card: 4384 7968 2770 3274
    → OR test UPI: success@razorpay
    → Webhook fires: payment.captured
    → Audit log entry #6: PAYMENT_CAPTURED

12. Agent confirms:
    "Done! Nike running shoes ordered for ₹1,799."
    → Audit log entry #7: TRANSACTION_COMPLETE
```

## Failure Scenario (Required Demo)

```
USER: "Also add premium insoles for ₹500"

Agent calculates: ₹1,799 + ₹500 = ₹2,299

Mandate Manager verifies against open mandates:
✗ ₹2,299 > ₹2,000 budget cap

→ MANDATE_VIOLATION raised
→ Payment Executor is NEVER called (blocked at mandate layer)

Agent responds:
"I can't add the insoles — your budget is ₹2,000 and the total
would be ₹2,299. Options:
1. Remove the shoes and buy only insoles (₹500)
2. Choose cheaper shoes under ₹1,500
3. Ask to increase your budget"

→ Audit log: MANDATE_VIOLATION_BLOCKED
  {reason: "budget_exceeded", attempted: 2299, limit: 2000}
```

## Audit Trail Entry Schema
```json
{
  "id": "audit_001",
  "timestamp": "2026-08-30T14:23:01Z",
  "session_id": "sess_abc123",
  "event_type": "INTENT_REGISTERED",
  "agent_id": "agent_uap_001",
  "mandate_type": "open_checkout",
  "mandate_hash": "base64url SHA-256 of the mandate JWT",
  "details": {
    "user_input": "Buy me running shoes under ₹2,000",
    "parsed_intent": {"product": "running shoes", "max_price": 2000},
    "constraint_check": {"passed": true, "budget_remaining": 2000}
  },
  "razorpay_refs": {
    "order_id": null,
    "payment_id": null,
    "payment_link_id": null
  }
}
```

## Mandate Lifecycle State Machine
```
OPEN_MANDATES_CREATED  →  CART_BUILT  →  CLOSED_MANDATES_SIGNED
        │                      │                    │
        │                      │                    ▼
        │                      │          PAYMENT_EXECUTED → COMPLETED
        │                      │                    │
        ▼                      ▼                    ▼
    EXPIRED              VIOLATED              FAILED
   (timeout)         (budget/rules)        (Razorpay error)
```

Each state transition is logged. Mandates only move forward — no reversal (immutability guarantee).
