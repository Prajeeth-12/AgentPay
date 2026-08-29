# Section 4: Data Model & API Endpoints

## SQLite Tables

### agents (UAP Trust Registry)
```sql
CREATE TABLE agents (
    id              TEXT PRIMARY KEY,          -- "agent_uap_001"
    name            TEXT NOT NULL,
    public_key_jwk  TEXT NOT NULL,             -- JSON: ES256 P-256 public key
    status          TEXT DEFAULT 'active',     -- active | suspended | revoked
    max_budget      INTEGER NOT NULL,          -- max per-session spend in paise
    registered_at   TEXT NOT NULL              -- ISO 8601
);
```

### sessions
```sql
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,          -- "sess_abc123"
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    user_intent     TEXT,
    parsed_intent   TEXT,                      -- JSON: {product, max_price, constraints}
    budget_limit    INTEGER NOT NULL,          -- paise (₹2,000 = 200000)
    budget_spent    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'active',     -- active | completed | expired | violated
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

### mandates (All 4 AP2 mandate types)
```sql
CREATE TABLE mandates (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    type            TEXT NOT NULL,             -- open_checkout | closed_checkout |
                                              --   open_payment | closed_payment
    vct             TEXT NOT NULL,             -- AP2 vct value
    payload         TEXT NOT NULL,             -- full JSON payload
    sd_jwt          TEXT,                      -- signed SD-JWT string
    mandate_hash    TEXT,                      -- base64url SHA-256
    constraints     TEXT,                      -- JSON constraint array (open mandates)
    status          TEXT DEFAULT 'created',    -- created | signed | verified | violated | expired
    parent_id       TEXT REFERENCES mandates(id),
    signed_by       TEXT,                      -- "user" | "agent" | "merchant"
    created_at      TEXT NOT NULL
);
```

### cart_items
```sql
CREATE TABLE cart_items (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    product_id      TEXT NOT NULL,
    product_title   TEXT NOT NULL,
    price           INTEGER NOT NULL,          -- paise
    quantity        INTEGER DEFAULT 1,
    added_at        TEXT NOT NULL
);
```

### payments
```sql
CREATE TABLE payments (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    mandate_id      TEXT NOT NULL REFERENCES mandates(id),
    razorpay_order_id   TEXT,
    razorpay_payment_id TEXT,
    razorpay_link_id    TEXT,
    razorpay_link_url   TEXT,
    amount          INTEGER NOT NULL,          -- paise
    currency        TEXT DEFAULT 'INR',
    status          TEXT DEFAULT 'created',    -- created | link_sent | authorized |
                                              --   captured | failed | refunded
    razorpay_signature  TEXT,
    webhook_payload     TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

### audit_log (Append-only, no UPDATE/DELETE)
```sql
CREATE TABLE audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    timestamp       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    agent_id        TEXT,
    mandate_id      TEXT REFERENCES mandates(id),
    mandate_type    TEXT,
    details         TEXT NOT NULL,             -- JSON
    razorpay_refs   TEXT,                      -- JSON: {order_id, payment_id, link_id}
    constraint_check TEXT                      -- JSON: {passed, reason, budget_remaining}
);
```

## Audit Event Types
```
INTENT_REGISTERED        — user intent parsed
UAP_AGENT_VERIFIED       — agent checked against UAP registry
OPEN_MANDATE_CREATED     — open checkout + payment mandates signed
CATALOG_SEARCHED         — products queried
PRODUCTS_PRESENTED       — options shown to user
USER_SELECTED_PRODUCT    — user picked a product
CART_UPDATED             — item added/removed
CLOSED_CHECKOUT_SIGNED   — closed checkout mandate signed by agent
CONSTRAINT_CHECK_PASSED  — constraints verified OK
CONSTRAINT_CHECK_FAILED  — constraint violation detected
MANDATE_VIOLATION_BLOCKED — payment blocked
CLOSED_PAYMENT_SIGNED    — closed payment mandate created
RAZORPAY_ORDER_CREATED   — Razorpay order API called
PAYMENT_LINK_CREATED     — payment link generated
PAYMENT_LINK_SENT        — link delivered
PAYMENT_AUTHORIZED       — webhook: payment.authorized
PAYMENT_CAPTURED         — webhook: payment.captured
PAYMENT_FAILED           — webhook: payment.failed
TRANSACTION_COMPLETE     — full flow completed
SESSION_EXPIRED          — session timed out
```

## FastAPI Endpoints

### Sessions
```
POST   /api/sessions                  Create new shopping session
       Body: {budget_limit: 200000}
       Returns: {session_id, agent_id, open_mandates}

GET    /api/sessions/{id}             Get session state
GET    /api/sessions/{id}/mandates    Get all mandates
GET    /api/sessions/{id}/audit       Get full audit trail
```

### Chat (WebSocket)
```
WS     /ws/{session_id}              Real-time bidirectional chat

Client sends:
  {"type": "user_message", "text": "Buy me shoes under 2000"}
  {"type": "select_product", "product_id": "prod_nike_pegasus"}
  {"type": "confirm_cart"}
  {"type": "confirm_payment"}

Server sends:
  {"type": "agent_token", "token": "I"}
  {"type": "agent_message", "text": "I found 3 options..."}
  {"type": "products", "items": [...]}
  {"type": "mandate_created", "mandate": {...}}
  {"type": "audit_entry", "entry": {...}}
  {"type": "budget_update", "spent": 0, "limit": 200000}
  {"type": "constraint_violation", "details": {...}}
  {"type": "payment_link", "url": "https://rzp.io/..."}
  {"type": "payment_captured", "payment_id": "pay_..."}
  {"type": "error", "message": "..."}
```

### Catalog
```
GET    /api/catalog/products          List all products
GET    /api/catalog/products/{id}     Get single product
GET    /api/catalog/search            Search products
       Query: ?q=running+shoes&max_price=200000&category=footwear
```

### Mandates
```
GET    /api/mandates/{id}             Get mandate details + SD-JWT
GET    /api/mandates/{id}/verify      Verify signature + constraints
POST   /api/mandates/check            Dry-run constraint check
       Body: {session_id, proposed_amount: 229900}
       Returns: {passed: false, reason: "budget_exceeded",
                 limit: 200000, proposed: 229900}
```

### Payments
```
GET    /api/payments/{session_id}     Get payment status
POST   /api/webhooks/razorpay        Razorpay webhook receiver
       (HMAC-SHA256 verified)
```

### UAP Registry
```
GET    /api/uap/agents                List registered agents
GET    /api/uap/agents/{id}           Get agent + public key
POST   /api/uap/agents/{id}/verify    Verify authorization
       Returns: {authorized: true, max_budget: 500000, status: "active"}
```

## Product Catalog Schema (JSON-LD)
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "id": "prod_nike_pegasus_41",
  "name": "Nike Air Zoom Pegasus 41",
  "description": "Responsive cushioning for everyday runs",
  "brand": {"@type": "Brand", "name": "Nike"},
  "category": "Footwear > Running Shoes",
  "image": "https://cdn.example.com/nike-pegasus.jpg",
  "offers": {
    "@type": "Offer",
    "price": 179900,
    "priceCurrency": "INR",
    "priceDisplay": "₹1,799",
    "availability": "https://schema.org/InStock",
    "seller": {
      "@type": "Organization",
      "name": "SportsDirect India",
      "id": "merchant_sportsdirect"
    }
  },
  "additionalProperty": [
    {"@type": "PropertyValue", "name": "size", "value": ["7","8","9","10","11"]},
    {"@type": "PropertyValue", "name": "color", "value": ["Black/White","Blue/Grey"]}
  ]
}
```

Catalog will have 50+ products across categories: footwear, electronics, clothing, books, accessories.
