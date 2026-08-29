# Track 04 — AI Finance Controller: Research Report

## Executive Summary
Track 04 rewards engineering rigor over design polish. The winning approach is multi-source settlement + TDS reconciliation with Razorpay-specific exception taxonomy. Combines deterministic accuracy (verifiable) with LLM value layer (exception explanation). The "verification capacity, not generation speed" signal means judges want rigorous match-rate measurement.

---

## Key Research Areas

### 1. AI-Powered Reconciliation
- **Rule-based:** Handles 70-80% of transactions (exact match on amount + date + reference)
- **AI layer:** Fuzzy matching (RapidFuzz), ML classifiers (XGBoost), LLM exception classification
- **Accuracy:** AI-augmented achieves 95%+ auto-match, reduces error from 1.5% to 0.4%
- **LLM role:** Exception classification + pattern detection + natural language explanation (NOT core matching)

### 2. Razorpay Settlement Reconciliation (India-Specific)
Multi-pass matching problem:
1. Match settlement_id → bank UTR + date + net amount
2. Explode by order_id and payment_id
3. Map each to: MDR, GST on MDR (18%), refund deductions

**Exception taxonomy:**
| Code | Cause |
|---|---|
| FEE_DEDUCTION | MDR rate differs from contract |
| TAX_DEDUCTION | GST on MDR variance |
| ROUNDING | Sub-rupee rounding |
| PARTIAL_PAYMENT | Refund reducing gross |
| UNEXPLAINED | Settlement ref absent from OMS |

### 3. Settlement Q&A Agent (Text-to-SQL)
- LangGraph + SQLite/DuckDB pattern
- Well-documented, solved problem
- **Novelty is LOW** standalone but good when combined with reconciliation

### 4. Cash Flow Forecasting
- **Weakest fit for this track** — synthetic data makes forecasting trivially easy
- TimesFM 3.0, Prophet, StatsForecast available but not differentiating
- Becomes curve-fitting exercise with known outcomes

### 5. TDS/GST Tax-Line Matching (HIGH NOVELTY for India)
- **TDS 194-O:** Razorpay deducts 1% TDS from e-commerce sellers
- **Three-source reconciliation:** Settlement report + Bank statement + TDS Form 26AS
- **Common exceptions:** PAN mismatch (5% vs 1%), timing difference, missing certificates, duplicate deduction on refunds
- **Completely under-automated in India**

---

## Winning Ideas (Ranked)
1. **Multi-Source Reconciliation Agent** (Settlement + Bank + TDS 26AS) — highest differentiation
2. **Settlement Recon + Conversational Q&A Hybrid** — closed-loop approach
3. **GST MDR ITC Matcher** — very India-specific, real merchant pain

## What Most Teams Will Build (AVOID)
- Simple text-to-SQL agent over SQLite
- Prophet forecasting notebook with Streamlit
- Reconciliation script with pandas merge + chatbot wrapper

---

## Feasibility
| Component | Time |
|---|---|
| Synthetic data (3 CSVs, exceptions injected) | 4-6 hours |
| Core reconciliation (Pandas + FuzzyWuzzy) | 1-2 days |
| LLM exception classification (LangGraph) | 1-2 days |
| Metrics reporting + audit trail | 4-6 hours |
| Demo UI (Streamlit/FastAPI) | 4-6 hours |
| **Total** | **4-5 days** |

## Novelty Score: 7/10
## Feasibility Score: 9/10
## Differentiation Score: 7.5/10
