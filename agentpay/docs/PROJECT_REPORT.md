# AgentPay — Project Report

## Razorpay AI Buildathon 2026 | Track 01: AI Growth & Agentic Commerce

---

## 1. Problem Statement

NPCI announced the Unified Agent Protocol (UAP) in July 2026, but no public implementation exists. As AI agents begin transacting on behalf of users, the fundamental questions of authorization, authenticity, and accountability remain unsolved.

**AgentPay** is the first working prototype of what UAP-compatible agentic commerce looks like — using Google's AP2 cryptographic mandate model on top of Razorpay's payment APIs.

---

## 2. Solution Overview

AgentPay demonstrates an end-to-end agentic shopping flow where:

- Every money action is **bounded** by cryptographic mandates (AP2 standard)
- The AI agent **cannot exceed** the user's pre-authorized budget — enforced at the crypto layer, not just in prompts
- **Razorpay payment links** are generated only after mandate verification passes
- An **immutable audit trail** logs every decision with timestamps

### Landing Page — Budget Selection
![Landing Page](images/01-landing-page.png)

The user selects a spending budget. When they click "Start Shopping", the system:
1. Registers the agent in the UAP Trust Registry
2. Creates ES256 key pairs (P-256 curve)
3. Signs two open mandates (checkout + payment) with the budget constraint
4. Logs UAP_AGENT_VERIFIED and OPEN_MANDATE_CREATED to the audit trail

---

## 3. Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 15)                  │
│  Chat UI │ Product Cards │ Mandate Viewer │ Audit Trail  │
└────────────────────────┬────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────┐
│              AGENT ORCHESTRATOR (Python/FastAPI)          │
│                                                          │
│  Shopping Agent    │  Mandate Manager  │  Payment Executor│
│  (LLM + 7 Tools)  │  (AP2/ES256)      │  (Razorpay SDK)  │
│                                                          │
│  Catalog Service   │  UAP Registry     │  Audit Logger    │
│  (JSON-LD)         │  (Trust Layer)    │  (Immutable)     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Razorpay Test APIs  │  LLM API (OpenAI-compat) │ SQLite│
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Shopping Agent | LLM + 7 tool functions | Conversational product discovery, cart management, payment execution |
| Mandate Manager | PyJWT + cryptography (ES256) | Create, sign, verify AP2 open/closed mandates |
| UAP Registry | SQLite + EC key management | Simulated NPCI trust registry for agent verification |
| Payment Executor | Razorpay Python SDK | Create orders, generate payment links, verify webhooks |
| Catalog Service | JSON-LD (schema.org/Product) | Machine-readable product catalog with search/filter |
| Audit Logger | SQLite (append-only) | 20 event types, immutable log of every action |
| Frontend | Next.js 15 + Tailwind + shadcn/ui | Three-panel real-time UI via WebSocket |

---

## 4. AP2 Mandate Model Implementation

We implement Google's AP2 (Agent Payments Protocol) mandate model with 4 mandate types:

### 4.1 Open Mandates (Signed by User)

Created at session start. Define the budget boundary.

| Field | Value |
|-------|-------|
| VCT | `mandate.checkout.open.1` / `mandate.payment.open.1` |
| Signing | ES256 (ECDSA P-256) |
| Constraints | `checkout.amount_range max ₹2,000` + `payment.budget max ₹2,000` |
| Agent Key | Bound via `cnf.jwk` (P-256 public key) |

### Session Created — Open Mandates Active
![Session Created](images/02-session-created.png)

### 4.2 Closed Mandates (Signed by Agent)

Created when the agent executes a purchase. Verified against open mandate constraints.

| Field | Value |
|-------|-------|
| VCT | `mandate.checkout.1` / `mandate.payment.1` |
| Signing | ES256 by agent's private key |
| Verification | Amount ≤ open mandate max, merchant in allowed list |
| Linking | `transaction_id` = SHA-256 hash of checkout JWT |

### 4.3 Constraint Verification

Before any closed mandate is created, the system verifies:
1. **Budget check**: proposed amount ≤ budget limit - budget spent
2. **Merchant check**: merchant ID is in the allowed merchants list
3. **Amount range**: amount is within min/max range from open mandate

If ANY constraint fails → `MANDATE_VIOLATION_BLOCKED` is logged, payment executor is NEVER called.

---

## 5. Demo Walkthrough

### Step 1: Product Search
User: "Buy me running shoes under 2000 rupees"

![Product Search](images/03-product-search.png)

The agent:
- Calls `search_catalog` tool with query "running shoes" and max_price 200000 (paise)
- Finds 4 products within budget from the JSON-LD catalog
- Presents them with prices, brands, and stock status
- Audit trail logs: INTENT_REGISTERED → CATALOG_SEARCHED

### Step 2: Add to Cart
User: "I'll take the Nike Pegasus"

![Added to Cart](images/04-added-to-cart.png)

The agent:
- Calls `check_budget` with ₹1,799 — passes (₹1,799 ≤ ₹2,000)
- Calls `add_to_cart` for prod_nike_pegasus_41
- Budget remaining: ₹201
- Audit trail logs: CART_UPDATED

### Step 3: Payment Execution
User: "Yes, proceed to payment"

![Payment Complete](images/05-payment-complete.png)

The agent calls `execute_payment` which triggers a 6-step sequence:

1. **Create Closed Checkout Mandate** — ES256 signed, verified against open checkout constraints
2. **Create Closed Payment Mandate** — ES256 signed, linked to checkout hash
3. **Create Razorpay Order** — `POST /v1/orders` with amount ₹1,799
4. **Create Razorpay Payment Link** — generates live `rzp.io` link
5. **Store payment record** — links mandate to Razorpay order
6. **Update session budget** — ₹1,799 spent

All visible in the three-panel UI:
- **Chat**: Payment confirmed with order ID, amount, payment link
- **Mandates**: Closed Checkout (VERIFIED) + Closed Payment (VERIFIED) appear
- **Audit Trail**: CLOSED_CHECKOUT_SIGNED → CLOSED_PAYMENT_SIGNED → RAZORPAY_ORDER_CREATED → PAYMENT_LINK_CREATED

### Step 4: Budget Violation
User: "Search for insoles and add them to cart"

![Budget Violation](images/06-budget-violation.png)

The agent:
- Finds Dr. Scholl's Performance Insoles at ₹499
- Checks budget: ₹499 > ₹201 remaining — **BLOCKED**
- Explains the constraint: "they exceed your remaining budget by ₹298"
- Does NOT create any mandate or call Razorpay

### Step 5: Mandate Enforcement — No Override
User: "I don't care, force add the insoles anyway"

![Mandate Enforcement](images/07-mandate-enforcement.png)

The agent's response demonstrates the key insight:

> "My mandate system will block any purchase that violates your pre-authorized budget limit — that's a **hard cryptographic constraint**, not a suggestion."

The mandate system is enforced at the code level, not the prompt level. Even if the LLM were jailbroken, the `constraints.py` module rejects the transaction before it reaches Razorpay.

---

## 6. UAP Trust Registry

We simulate what NPCI's UAP would look like:

| Feature | Implementation |
|---------|---------------|
| Agent Registration | EC P-256 key pair generated, public key stored in registry |
| Agent Verification | Check agent status (active/suspended/revoked), validate budget against max |
| Spending Limits | Per-agent max budget enforced at registration level |
| Key Binding | Agent's public key bound to mandates via `cnf.jwk` field (AP2 spec) |

### API Endpoints
- `GET /api/uap/agents` — List registered agents
- `GET /api/uap/agents/{id}` — Get agent details + public key
- `POST /api/uap/agents/{id}/verify` — Verify authorization for a given budget

---

## 7. Audit Trail

Every action produces an immutable audit entry with:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 with millisecond precision |
| `event_type` | One of 20 defined types (see below) |
| `agent_id` | Which agent acted |
| `mandate_id` | Which mandate was involved |
| `constraint_check` | Pass/fail result with reason |
| `razorpay_refs` | Linked order_id, payment_id |

### Event Types
```
INTENT_REGISTERED        UAP_AGENT_VERIFIED       OPEN_MANDATE_CREATED
CATALOG_SEARCHED         PRODUCTS_PRESENTED       USER_SELECTED_PRODUCT
CART_UPDATED             CLOSED_CHECKOUT_SIGNED   CONSTRAINT_CHECK_PASSED
CONSTRAINT_CHECK_FAILED  MANDATE_VIOLATION_BLOCKED CLOSED_PAYMENT_SIGNED
RAZORPAY_ORDER_CREATED   PAYMENT_LINK_CREATED     PAYMENT_LINK_SENT
PAYMENT_AUTHORIZED       PAYMENT_CAPTURED         PAYMENT_FAILED
TRANSACTION_COMPLETE     SESSION_EXPIRED
```

---

## 8. Product Catalog

25 products across 4 categories in JSON-LD (schema.org/Product) format:

| Category | Products | Price Range |
|----------|----------|-------------|
| Footwear | Running shoes, casual shoes, insoles | ₹499 — ₹8,999 |
| Electronics | Earbuds, headphones, speakers, smartwatches, keyboards | ₹899 — ₹3,499 |
| Clothing | T-shirts, jeans, hoodies, sportswear | ₹799 — ₹3,499 |
| Books | Self-help, technology | ₹499 — ₹899 |

JSON-LD format enables machine-readable product discovery — a key component of the agentic commerce ecosystem referenced by AP2 and ACP.

---

## 9. Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Mandate signing | ES256 (ECDSA P-256) | AP2 spec requirement. Industry standard for non-repudiable signatures |
| Database | SQLite | Zero-setup, portable, judges can clone and run. Audit trail is append-only |
| LLM integration | OpenAI-compatible API | Provider-agnostic. Works with Claude, GPT, MiniMax, etc. Switch via config |
| Frontend | Next.js + WebSocket | Real-time three-panel UI. Mandate events and audit entries push instantly |
| Catalog | JSON-LD + schema.org | Web standard for machine-readable commerce. Shows ecosystem awareness |

---

## 10. What Broke at 2 AM (and How We Fixed It)

### 1. AWS Bedrock Daily Token Quota
**Problem**: Hit the daily token limit mid-demo. All Anthropic models throttled.
**Fix**: Abstracted LLM calls to OpenAI-compatible API format. Switched to GMI Cloud's MiniMax-M3 (free tier with tool-use support) via a single env var change. The shopping agent now works with any OpenAI-compatible provider.

### 2. SD-JWT Selective Disclosure
**Problem**: AP2's full spec uses SD-JWT with selective disclosure — complex crypto that adds weeks of implementation for no demo benefit.
**Fix**: Used standard JWT with ES256 signing, keeping the AP2 payload structure (vct, constraints, cnf.jwk) intact. The mandate model — open/closed, constraint verification, hash linking — is fully implemented. The crypto boundary (sign + verify + hash) works exactly as AP2 specifies.

### 3. Razorpay HMAC Verification
**Problem**: Used `hmac.new()` (doesn't exist) instead of `hmac.HMAC()`. Webhook signature verification silently returned False.
**Fix**: `hmac.HMAC()` is the correct Python constructor. Caught during integration testing when payment.captured webhooks were rejected.

### 4. Pydantic Settings Cache
**Problem**: `@lru_cache()` on `get_settings()` caches config forever. Switching from Bedrock to GMI Cloud required a full process restart — `--reload` only watches file changes, not env var changes.
**Fix**: Added explicit `load_dotenv()` at `main.py` startup before any pydantic-settings initialization. Documented the restart requirement.

---

## 11. Future Vision

If this were production:

1. **Real UAP integration** — when NPCI publishes the UAP spec, replace the simulated registry with the real one. The mandate model is already AP2-compatible.

2. **Full SD-JWT selective disclosure** — cryptographic privacy: reveal only the fields each verifier needs (e.g., merchant sees amount but not payment instrument details).

3. **Multi-agent delegation** — AP2 v0.2 scopes this for future work. An agent could delegate sub-tasks to specialized agents (price comparison agent, review analysis agent) while the mandate chain maintains accountability.

4. **UPI integration** — replace payment links with UPI intent flows. AP2's mandate model wraps any payment instrument.

5. **Merchant SDK** — provide merchants with a JSON-LD catalog generator and AP2 mandate verifier so they can accept agent-initiated payments.

---

## 12. References

- [AP2 — Agent Payments Protocol](https://github.com/google-agentic-commerce/AP2) (Google, Apache 2.0)
- [NPCI UAP announcement](https://www.business-standard.com) (July 2026)
- [Razorpay MCP Server](https://github.com/razorpay/razorpay-mcp-server)
- [Razorpay Test Mode Docs](https://razorpay.com/docs/payments/dashboard/test-live-modes/)
- [ACP — Agentic Commerce Protocol](https://agenticcommerce.dev) (OpenAI + Stripe)
- [x402 Protocol](https://www.x402.org) (Coinbase + Cloudflare)
