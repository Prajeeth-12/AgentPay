# Track 03 — AI Revenue Recovery: Research Report

## Executive Summary
Track 03 is compelling if angled on India-specific RBI mandate constraints. Checkout abandonment recovery is well-trodden globally. The genuine gap: a Mandate Retry Sequencer with RBI compliance + multi-channel recovery orchestration. No open-source implementation exists for India's specific constraints.

---

## Key Research Areas

### 1. Payment Failure Recovery (State of Art)
- **Stripe Smart Retries:** 8 attempts over 2 weeks, ML-driven time selection, hard vs soft decline classification
- **India RBI constraints:** Pre-debit notification 24h mandatory, ₹1 lakh threshold for enhanced auth, NACH allows only 2 presentation attempts per billing cycle
- **India's retry problem is more constrained** — must pivot faster to non-retry channels (payment links, WhatsApp)
- **Razorpay's current state:** "Smart Payment Retries" exists but is a black box, no unified recovery agent

### 2. Checkout Abandonment Recovery
- Standard email drip recovers 5-15%
- **Novel angle:** LLM-generated personalized messages (15-30% lift in open-to-click)
- **Gap:** No agent-driven recovery system that closes the full loop (detect → triage → outreach → track → confirm)

### 3. Subscription/Mandate Recovery (India-Specific)
- UPI Autopay failures: customer can retry manually, merchant sends payment link
- eMandate (NACH): 2 retry limit per cycle → must switch to non-mandate channels
- **Agent opportunity:** Classify failure → decide retry vs new payment method → send recovery link → escalate → audit log

### 4. B2B Receivables Automation
- Gap in Indian context: WhatsApp is de facto B2B communication channel
- Promise-to-pay tracking (customer says "will pay Friday" → agent monitors)

### 5. Voice AI — Hinglish Recovery
- **Sarvam AI:** Indian-built, 11 languages, Hindi/Hinglish support
- TRAI rules: calls must identify as automated, opt-out required, 9AM-9PM only
- **High novelty but complex** — simulated voice agent may be more feasible for hackathon

### 6. Razorpay's Recovery Products (Siloed)
Subscriptions, Optimizer, Smart Collect, Payment Links, Webhooks — all building blocks exist but NO unified agent layer orchestrating them

---

## Best Framework: LangGraph
- State graph maps to recovery states (detected → triaged → intervention_sent → awaiting → recovered/escalated)
- Persistent state, human-in-loop checkpoints, LangSmith for audit trail

---

## Winning Ideas (Ranked)
1. **Mandate Retry Sequencer + Multi-Channel Recovery Agent** (Highest novelty, India-specific)
2. **B2B Receivables Chaser with Promise-to-Pay** (Medium-high novelty)
3. **Checkout Drop-off Recovery** (Low differentiation — well-trodden)

## Key Strength
Measurable output: "₹ recovered across a batch" — clear, quantifiable result

## Novelty Score: 7.5/10
## Feasibility Score: 8/10
## Differentiation Score: 7.5/10
