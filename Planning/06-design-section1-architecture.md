# Section 1: Project Overview & Architecture

## Project Name
**AgentPay** — India's First UAP-Compatible Agentic Commerce Platform

## What It Does
A working prototype that demonstrates how AI agents can discover products, negotiate purchases, and execute payments autonomously — using AP2's cryptographic mandate model for trust/authorization, running on Razorpay's real test-mode APIs.

## Decisions Made
- **Track:** 01 — AI Growth & Agentic Commerce
- **Direction:** UAP Prototype with AP2 Mandate Model (Option A)
- **LLM:** Claude Opus 4.6 via AWS Bedrock
- **Razorpay:** Test mode (need to create account)
- **Demo:** Web app (Next.js frontend) for best competition impact

## High-Level Architecture (4 Layers)

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                     │
│  Chat UI │ Product Cards │ Mandate Viewer │ Audit Trail  │
└────────────────────────┬────────────────────────────────┘
                         │ REST/WebSocket
┌────────────────────────▼────────────────────────────────┐
│              AGENT ORCHESTRATOR (Python/FastAPI)          │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Shopping  │  │ Mandate  │  │ Payment  │              │
│  │ Agent     │  │ Manager  │  │ Executor │              │
│  │ (Claude)  │  │ (AP2)    │  │(Razorpay)│              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Catalog   │  │ UAP      │  │ Audit    │              │
│  │ Service   │  │ Registry │  │ Logger   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              EXTERNAL SERVICES                           │
│  Razorpay Test APIs  │  Claude (Bedrock)  │  SQLite DB  │
└─────────────────────────────────────────────────────────┘
```

## The 6 Internal Services

| Service | Role |
|---------|------|
| **Shopping Agent** | Claude-powered conversational agent: understands user intent, searches catalog, recommends products, builds cart |
| **Mandate Manager** | Implements AP2 mandate model: creates/signs/verifies Intent, Checkout, and Payment mandates using SD-JWT + ES256 |
| **Payment Executor** | Calls Razorpay APIs: create order, create payment link, verify payment |
| **Catalog Service** | JSON-LD merchant product catalog, machine-readable for the agent |
| **UAP Registry** | Simulated NPCI UAP trust registry: agent registration, verification, spending-limit enforcement |
| **Audit Logger** | Immutable append-only log of every action: intent → mandate → payment → outcome |
