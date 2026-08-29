# Track 02 — AI Risk Manager: Research Report

## Executive Summary
Track 02 is technically deep but the easiest directions (RTO scorer, PaySim XGBoost) are well-trodden by Razorpay's own Thirdwatch product. Winning requires finding a genuine gap. The biggest opportunities: Chargeback Evidence Responder (no Indian open-source tool exists) and Cross-Merchant Abuse-Ring Detection (GNNs).

---

## Key Research Areas

### 1. AI Fraud Detection (2025-2026)
- **GNNs:** Dominant paradigm. Fraud is relational — shared devices, addresses, cards across accounts. Tools: DGL, PyTorch Geometric
- **LLMs for fraud:** Emerging but lag specialized models on tabular data. Best pattern: LLM + traditional ML hybrid
- **Key papers:** arXiv 2411.05815 (GNN survey), SSRN 5319335 (Graph-Augmented RNN for rings), FraudTransformer (IEEE CAI 2026)

### 2. Chargeback Auto-Responders
- **How it works:** Ingest transaction metadata + reason code → compile evidence package → submit representment
- **Commercial landscape:** Chargeblast, Chargeflow, Justt.ai — ALL US/EU focused
- **THE GAP:** No open-source Indian chargeback responder exists. Indian payments use RBI ODR, UPI Dispute Resolution — completely different from US card network rules

### 3. Return-Risk Scoring (RTO)
- **Indian RTO:** 20-25% average, 30-40% for COD
- **CROWDED:** Razorpay Thirdwatch, GoKwik, Delhivery, Parcelmind all do this
- **NOT recommended** unless novel angle (graph-based serial RTO abuser detection)

### 4. Abuse-Ring Detection
- **Techniques:** Entity resolution → community detection (Louvain) → GNN scoring (GraphSAGE, R-GCN)
- **India angle:** Synthetic identity fraud up 450% since 2022 (NASSCOM-DSCI)
- **HIGH novelty** but complex to execute

### 5. Indian BFSI Fraud Landscape
- 7.1% of digital payments suspected fraud (TransUnion 2025)
- 300% surge in account takeover attacks
- 1 in 5 UPI users experienced fraud in 2025
- Global AI fraud: 1,210% surge in 2025

---

## Available Datasets
| Dataset | Size | Best For |
|---|---|---|
| PaySim | 6.3M txns | Baseline fraud detection |
| IEEE-CIS/Vesta | 590K txns | Card fraud, feature engineering |
| BAF Suite | Multiple splits | Account fraud |
| Elliptic Bitcoin | 203K nodes | Graph fraud |

**No Indian payment dataset is public** — need synthetic augmentation

---

## Winning Ideas (Ranked)
1. **Chargeback Evidence Responder** (High novelty, India gap, feasible)
2. **Cross-Merchant Abuse-Ring Sentinel** (Highest novelty, harder to execute)
3. **Fraud-Spike Detector + Explainable Alerts** (Solid but less novel)

## Key Challenge
Requires honest ML metrics (precision/recall/FP cost on held-out test set) — higher evaluation bar than other tracks.

## Novelty Score: 7/10
## Feasibility Score: 6.5/10
## Differentiation Score: 7/10
