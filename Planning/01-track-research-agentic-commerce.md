# Track 01 — AI Growth & Agentic Commerce: Research Report

## Executive Summary
Track 01 is the most cutting-edge track with the highest novelty potential. The space is simultaneously brand-new and unsolved — NPCI's UAP has no public implementation, AP2's mandate model is the most technically complete spec, and Razorpay's test-mode + MCP server provides everything needed to make it runnable.

---

## Key Protocols Researched

### 1. NPCI UAP (Unified Agent Protocol)
- **Announced:** July 2026 (Business Standard)
- **Status:** Pre-alpha / proposal. No public API, no spec, no pilot, pending RBI approval
- **How it works:** Trust/verification layer on top of UPI. Agent registers → generates payment request → UAP verifies agent → routes through UPI → user approves (or auto within spending limit)
- **Competition relevance:** VERY HIGH — Razorpay explicitly name-drops UAP in the buildathon brief. Building a prototype would be THE FIRST implementation ever.

### 2. ACP (Agentic Commerce Protocol)
- **Built by:** OpenAI + Stripe (NOT Shopify)
- **Launched:** September 2025, powered ChatGPT Instant Checkout
- **Status:** Partially sunset — Instant Checkout retired March 2026. Spec remains open (Apache 2.0)
- **Use:** Architecture reference pattern, not a production platform to build on

### 3. AP2 (Agent Payments Protocol)
- **Built by:** Google, 60+ partners (Adyen, Amex, Coinbase, Mastercard, PayPal, Visa, JusPay India)
- **Announced:** September 2025
- **Architecture — Mandate Model:**
  - Intent Mandate: user's shopping goals + constraints ("max ₹5,000")
  - Cart Mandate: cryptographically signed record of exact items + price
  - Payment Mandate: authorizes payment instrument against Cart Mandate
  - All mandates are tamper-proof, non-repudiable audit trail
- **Status:** Public spec on GitHub (goo.gle/ap2), reference implementations, FIDO Alliance standardization
- **Competition relevance:** HIGHEST — AP2's mandate model maps EXACTLY to the buildathon bar ("every money action explainable, bounded, gated, audit trail")

### 4. x402 Protocol
- **Built by:** Coinbase + Cloudflare
- **How it works:** HTTP 402 status code for instant stablecoin (USDC) payments
- **Stats:** 69K active agents, 165M transactions, ~$50M volume (April 2026)
- **Limitation:** Crypto-native, not directly usable with Razorpay INR flows
- **Use:** Conceptual demo of "machine-pays-machine" pattern

### 5. Razorpay MCP Server
- **v1:** April 2025 — India's first payment gateway MCP server
- **v2 (Remote):** June 2025 — 35+ tools, zero setup
- **Capabilities:** Create/send payment links, create/capture orders, refunds, settlements, reports
- **Test mode:** Fully functional sandbox, immediately accessible

---

## Market Signals
- AI-driven traffic to US retail: up 4,700% YoY (Adobe Analytics)
- AI platforms projected $20.9B retail spending 2026 (4x 2025)
- Amazon "Buy for Me": 500K+ SKUs live
- McKinsey: $3-5T agent-orchestrated retail by 2030

## What's Unsolved
- UAP / agent authorization for UPI (India-specific, unresolved)
- Fraud detection for agent traffic
- Dispute resolution for agent purchases
- Multi-agent delegation

---

## Winning Project Ideas (Ranked)

### Option A — UAP Prototype (HIGHEST NOVELTY)
Simulate what UAP would look like:
- Agent registers with a "trust registry" (simulated)
- Carries a spending-bounded mandate (AP2-style)
- Initiates Razorpay payment links within bounds
- Full audit trail: intent → cart → payment → confirmation
- Handles "budget exceeded" failure case

### Option B — Agent-Readable Catalog + Conversational Checkout
Machine-readable catalog (JSON-LD), LLM shopping agent, Razorpay order + payment APIs

### Option C — Upsell/Cross-Sell Revenue Agent
Monitor merchant orders, identify opportunities, generate personalized offers via Razorpay payment links

---

## Feasibility Assessment
| Component | Feasibility | Complexity |
|---|---|---|
| Razorpay test-mode API | Very High | Low |
| Razorpay MCP Server | Very High | Low |
| AP2-style mandates (simulated) | High | Medium |
| Conversational agent (LangChain) | High | Medium |
| Agent-readable catalog (JSON-LD) | High | Low |
| UAP verification layer (simulated) | High | Medium |

**Recommended stack:** Python + LangChain/LlamaIndex, Razorpay SDK + MCP, FastAPI, SQLite, Claude API
**Time estimate:** 2-3 weeks for polished submission

## Novelty Score: 9.5/10
## Feasibility Score: 8/10
## Differentiation Score: 9.5/10
