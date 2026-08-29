# Track Comparison Matrix & Final Recommendation

## Scoring Matrix (1-10 scale)

| Criteria | Track 01: Agentic Commerce | Track 02: Risk Manager | Track 03: Revenue Recovery | Track 04: Finance Controller |
|---|---|---|---|---|
| **Novelty / Cutting-Edge** | 9.5 | 7.0 | 7.5 | 7.0 |
| **Differentiation from other submissions** | 9.5 | 7.0 | 7.5 | 7.5 |
| **Alignment with what Razorpay wants** | 10.0 | 7.5 | 8.0 | 8.0 |
| **Feasibility (2-3 weeks)** | 8.0 | 6.5 | 8.0 | 9.0 |
| **Uses newest protocols/frameworks** | 10.0 | 6.0 | 7.0 | 6.0 |
| **Uniqueness of problem space** | 10.0 | 6.5 | 7.0 | 7.5 |
| **Demo impact / "Wow factor"** | 9.5 | 7.0 | 7.5 | 6.5 |
| **Available tools/APIs** | 9.0 | 6.5 | 8.0 | 8.5 |
| **TOTAL** | **75.5** | **54.0** | **60.5** | **60.0** |

---

## Why Track 01 Wins (Decisively)

### 1. It's the NEWEST problem space
- UAP announced July 2026 — less than 2 months old, no public implementation exists anywhere
- AP2 spec from September 2025 — still being standardized through FIDO Alliance
- ACP, x402 — all 2025-2026 protocols
- This is literally the frontier of fintech. No student (or company) has built a UAP prototype yet.

### 2. Razorpay EXPLICITLY signals this is what they want
- The buildathon brief NAME-DROPS UAP, ACP, AP2, x402 — they're telling you what to build
- "Agent-to-agent commerce the open problem of the year" — they want someone to tackle this
- Razorpay's own Sprint 2026 launch was titled "The Age of Agentic Payments"
- Their entire product strategy is pivoting to agentic commerce

### 3. Strongest differentiation potential
- Other tracks (fraud, recovery, reconciliation) have existing products and well-known approaches
- Track 01 has NO existing open-source implementations to copy from
- Your submission can't be compared against a Kaggle notebook or a GitHub repo because they don't exist
- You're building in a greenfield, not competing in a crowded field

### 4. The tech stack is achievable
- Razorpay MCP Server (35+ tools, plug and play)
- Razorpay test-mode APIs (fully documented sandbox)
- Python + LangChain/LlamaIndex (well-supported agent frameworks)
- AP2 mandate model is well-specified — implement the schema yourself
- No need for ML training, no need for datasets, no need for specialized hardware

### 5. Demo has the highest "wow factor"
- "User says 'buy me shoes under ₹2,000' → agent registers intent → discovers products → presents cart → user approves → Razorpay payment executes → audit trail shows every step → then demo the failure case where budget is exceeded"
- This is a live, end-to-end demo that judges can SEE working
- Compare to: "here's my precision/recall curve on PaySim data" (Track 02) or "here's a reconciliation match rate" (Track 04)

### 6. Aligns with global tech trends
- Google's AP2 has 60+ enterprise partners
- Shopify's UCP is powering Google AI Mode checkout
- Amazon's "Buy for Me" has 500K+ SKUs
- McKinsey: $3-5T agent-orchestrated retail by 2030
- You're not solving yesterday's problem — you're building tomorrow's infrastructure

---

## Why NOT the other tracks

### Track 02 (Risk Manager) — Skip
- Razorpay OWNS Thirdwatch (RTO scoring product) — hard to impress them with what they already have
- Requires honest ML metrics on held-out test sets — higher evaluation bar, more room for error
- No Indian payment datasets publicly available — synthetic data weakens credibility
- GNN fraud ring detection is cool but very complex for 2-3 weeks

### Track 03 (Revenue Recovery) — Decent but not outstanding
- Checkout abandonment recovery is well-trodden globally
- Razorpay already has Smart Retries, Optimizer, Payment Links
- The India-specific mandate angle is novel but niche
- Measured "₹ recovered" metric is clean but less impressive than a live agent demo

### Track 04 (Finance Controller) — Safe but not exciting
- Reconciliation is well-understood; most approaches are pandas merge + fuzzy matching
- Judges may see it as "solved problem + LLM wrapper"
- Highest feasibility but lowest wow factor
- Good for a safe submission, not for a winning one

---

## RECOMMENDATION

# → Track 01: AI Growth & Agentic Commerce

## Build: UAP Prototype with AP2 Mandate Model on Razorpay Test APIs

### The killer demo:
1. User says "buy me running shoes under ₹2,000"
2. Agent registers an **Intent Mandate** (AP2-style) with spending bounds
3. Agent discovers products via merchant catalog API
4. Agent presents cart → user countersigns a **Cart Mandate**
5. Agent creates a Razorpay payment link bounded to that exact amount
6. Payment executes via Razorpay test mode
7. Full audit trail shows every step: intent → cart → payment → confirmation
8. THEN: demo the failure case — ₹3,000 item blocked, agent explains why

### Why this wins:
- First UAP prototype ever built
- Uses AP2's mandate model (Google's spec with 60+ partners)
- Runs on Razorpay's own APIs (test mode)
- Every money action explainable, bounded, gated (EXACTLY what the brief asks)
- Shows audit trail (EXACTLY what the brief asks)
- Shows failure handled gracefully (EXACTLY what the brief asks)
- No one else will have built this

### Tech stack:
- Python + LangChain or LlamaIndex (agent framework)
- Razorpay Python SDK + MCP Server (payment execution)
- FastAPI (merchant catalog + simulated UAP registry)
- SQLite (audit trail + mandate storage)
- Claude API or GPT-4o (LLM backbone)
- Streamlit or React (demo UI)

### Timeline: 2-3 weeks
