# Section 3: Tech Stack & Project Structure

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | Next.js 15 + Tailwind + shadcn/ui | Polished UI for video demo, fast to build |
| **Backend** | Python 3.12 + FastAPI | Best for agent orchestration, async, Razorpay SDK native |
| **Agent LLM** | Claude Opus 4.6 via AWS Bedrock | Existing creds, excellent tool-use |
| **Mandate Crypto** | PyJWT + cryptography (ES256/P-256) | AP2 uses SD-JWT with ECDSA P-256 |
| **Razorpay** | razorpay Python SDK + REST API | Official SDK for orders, payment links, verification |
| **Database** | SQLite via aiosqlite | Audit trail, mandates, sessions — zero setup |
| **Catalog** | JSON-LD files (schema.org/Product) | Machine-readable, web standard |
| **Communication** | WebSocket (FastAPI → Next.js) | Real-time chat streaming, mandate events |
| **AP2 SDK** | ap2 from GitHub (Google's official) | Pydantic models + JSON schemas |

## Project Structure

```
agentpay/
├── backend/                          # Python FastAPI
│   ├── main.py                       # FastAPI app, WebSocket endpoint
│   ├── config.py                     # Env vars, Razorpay keys, Bedrock config
│   ├── requirements.txt
│   │
│   ├── agent/
│   │   ├── shopping_agent.py         # Claude-powered shopping logic
│   │   ├── tools.py                  # Agent tools: search_catalog, check_budget, etc.
│   │   └── prompts.py                # System prompts for the agent
│   │
│   ├── mandates/
│   │   ├── manager.py                # Create, sign, verify mandates (AP2 model)
│   │   ├── schemas.py                # Pydantic models for all 4 mandate types
│   │   ├── crypto.py                 # ES256 key generation, SD-JWT signing/verification
│   │   └── constraints.py            # Budget check, merchant check, expiry check
│   │
│   ├── uap/
│   │   ├── registry.py               # Simulated UAP trust registry
│   │   └── verification.py           # Agent registration, authorization checks
│   │
│   ├── payments/
│   │   ├── razorpay_client.py        # Razorpay SDK wrapper
│   │   ├── webhook_handler.py        # Handle payment.captured, payment.failed
│   │   └── payment_flow.py           # Orchestrate: mandate → order → link → verify
│   │
│   ├── catalog/
│   │   ├── service.py                # Search, filter, rank products
│   │   └── data/
│   │       └── products.json         # JSON-LD product catalog (50+ products)
│   │
│   ├── audit/
│   │   ├── logger.py                 # Append-only audit trail writer
│   │   └── models.py                 # AuditEntry Pydantic model
│   │
│   └── db/
│       ├── database.py               # SQLite connection, migrations
│       └── models.py                 # DB tables: sessions, mandates, audit_log, payments
│
├── frontend/                         # Next.js 15
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Landing / demo start page
│   │   └── chat/
│   │       └── page.tsx              # Main chat + shopping interface
│   │
│   ├── components/
│   │   ├── Chat.tsx                  # Chat messages, user input
│   │   ├── ProductCard.tsx           # Product display with image, price
│   │   ├── CartView.tsx              # Cart with mandate status
│   │   ├── MandateViewer.tsx         # Visual display of mandates
│   │   ├── AuditTrail.tsx            # Real-time scrolling audit log
│   │   ├── PaymentStatus.tsx         # Razorpay payment status
│   │   └── BudgetGauge.tsx           # Visual budget gauge
│   │
│   └── lib/
│       ├── websocket.ts              # WebSocket client
│       └── types.ts                  # TypeScript types
│
├── docs/
│   └── architecture.md
├── scripts/
│   ├── seed_catalog.py               # Generate 50+ products
│   └── demo_scenario.py              # End-to-end demo script
├── .env.example
├── docker-compose.yml
└── README.md
```

## Key Design Decisions

1. **Separate backend (Python) + frontend (Next.js):** Claude Bedrock SDK is Python-native (boto3), AP2 SDK is Python (Pydantic), Razorpay Python SDK is more mature. Next.js gives polished UI.

2. **SQLite:** Zero setup, judges can clone and run. Audit trail is append-only. Tiny dataset. Entire DB is one file.

3. **WebSocket:** Agent responses stream real-time, mandate events push to UI, audit trail scrolls live, webhook events push immediately. Creates "wow" demo effect.

4. **JSON-LD for catalog:** AP2 and buildathon brief mention "agent-readable catalog". schema.org/Product is the web standard. Shows judges we understand the ecosystem.

## UI Layout

```
┌──────────────────────────────────────────────────────────┐
│  AgentPay — UAP-Compatible Agentic Commerce              │
├──────────┬───────────────────────┬───────────────────────┤
│          │                       │                       │
│  CHAT    │   MANDATE VIEWER      │   AUDIT TRAIL         │
│          │                       │                       │
│  User:   │  ┌─ Open Checkout ─┐  │  14:23:01 INTENT      │
│  "Buy    │  │ Budget: ₹2,000  │  │  14:23:02 UAP_AUTH    │
│  shoes   │  │ Merchants: [All]│  │  14:23:05 CATALOG     │
│  under   │  │ Status: ACTIVE  │  │  14:23:08 CART_BUILT  │
│  ₹2000"  │  └─────────────────┘  │  14:23:09 MANDATE_OK  │
│          │                       │  14:23:10 ORDER_MADE   │
│  Agent:  │  ┌─ Closed Payment ─┐ │  14:23:12 PAYMENT_OK  │
│  "Found  │  │ Amount: ₹1,799  │  │                       │
│  3 opts" │  │ To: Nike Store   │  │  [Budget: ████░ 90%]  │
│          │  │ Status: SIGNED   │  │                       │
│  [Nike]  │  └─────────────────┘  │                       │
│  [Adidas]│                       │                       │
│  [Puma]  │  ┌─ Budget Gauge ──┐  │                       │
│          │  │ ₹201 remaining  │  │                       │
│          │  │ ████████████░   │  │                       │
│          │  └─────────────────┘  │                       │
├──────────┴───────────────────────┴───────────────────────┤
│  [Type your message...]                          [Send]  │
└──────────────────────────────────────────────────────────┘
```

Three-panel: Chat (left), Mandates + Budget (center), Audit Trail (right).
