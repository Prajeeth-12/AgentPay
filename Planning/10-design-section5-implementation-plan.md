# Section 5: Implementation Plan & Timeline

## Timeline Overview (6 days to Sept 5)

```
TODAY          Phase 1          Phase 2          Phase 3          Phase 4         SUBMIT
Aug 29    ──── Aug 30-31 ──── Sep 1-2 ──── Sep 3 ──── Sep 4 ──── Sep 5
              FOUNDATION      CORE AGENT     FRONTEND      POLISH & VIDEO
```

## Phase 1: Foundation (Day 1-2)
- Set up Razorpay test account, get API keys
- Initialize Python project (FastAPI + dependencies)
- Initialize Next.js frontend (scaffold only)
- SQLite database schema + migrations
- Razorpay client wrapper (create order, create payment link, verify)
- Webhook handler (payment.captured, payment.failed)
- Product catalog: seed 50+ products as JSON-LD
- Catalog service: search, filter, get by ID
- Basic FastAPI endpoints
- Test: manually create order → payment link → complete test payment

## Phase 2: Core Agent + Mandates (Day 3-4)
- ES256 key pair generation (P-256)
- Mandate schemas (Pydantic models for all 4 types)
- SD-JWT creation + signing + verification
- Open/closed mandate creation + constraint verification
- UAP registry: agent registration, verification
- Audit logger: append-only, all event types
- Shopping agent: Claude via Bedrock with tool-use
- WebSocket endpoint: chat streaming + events
- Full flow wiring + testing
- Budget violation test

## Phase 3: Frontend (Day 5)
- Chat component with streaming
- Product cards, Mandate viewer, Budget gauge
- Audit trail (real-time scrolling)
- Payment status, Constraint violation alerts
- WebSocket client
- Session creation flow

## Phase 4: Polish & Submission (Day 6)
- README.md, architecture diagram
- docker-compose.yml, .env.example
- 5-min pitch video recording
- Final testing (fresh clone → run → demo)
- Push to public GitHub, fill form, submit

## Risk Buffers
- SD-JWT → fallback to standard JWT with AP2 payload
- Frontend → Streamlit fallback if Next.js delayed
- Webhooks → ngrok or poll payment status
- Catalog → 15-20 products minimum viable

## Cut List (if running out of time)
- Full SD-JWT selective disclosure → standard JWT
- 50+ products → 15-20
- Docker compose → manual setup
- Multiple merchants → single merchant
- Real AP2 SDK → implement schemas ourselves
