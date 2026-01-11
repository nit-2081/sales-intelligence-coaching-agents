# Sales Intelligence & Coaching Agents

> **A safety-first, human-in-the-loop AI system for sales intelligence, coaching, and decision support.**

This repository demonstrates the design and implementation of **three AI agents**—Negotiator Agent, Retention Agent, and AI Sales Coach—built on **one shared intelligence backbone**. The system strictly follows a **Phase 1–9 agent framework**, prioritizing transparency, safety, and human control over automation.

---

## 🎯 Project Goal

The goal of this project is **not** to replace humans, but to:
- Reduce repetitive analysis work
- Provide actionable insights and suggestions
- Keep humans as final decision-makers
- Demonstrate safe, explainable AI agent design

All data used is **mock data**, and all automation runs in **Shadow Mode (Level 1)**.

---

## 🧠 Core Design Principle

**One Shared Intelligence Backbone → Multiple Agent Policies**

```
Input (Mock Data)
   ↓
Understand (Signals, ML-lite, Rules)
   ↓
Decide (Confidence + Thresholds)
   ↓
Suggest to Human (Insights / Tips / Alerts)
   ↓
Log Feedback & Observability
```

This backbone is reused across all agents to avoid duplication and ensure consistency.

---

## 🤖 Agents Overview

### 1️⃣ AI Sales Coach (✅ Complete)

**Purpose**: Post-call coaching for sales representatives.

**What it does**:
- Analyzes completed sales call transcripts (2–3 min, mock)
- Scores reps on:
  - Empathy
  - Pacing
  - Objection handling
  - Closing
- Generates **exactly 3 micro-improvement tips** per call

**Key Characteristics**:
- Batch processing (post-call)
- Rule-based scoring + optional ML confidence
- LLM used only for structured tip generation (with safe fallback)
- Full human-in-the-loop control

**Automation Level**: Level 1 – Shadow Mode

---

### 2️⃣ Retention Agent (✅ Complete)

**Purpose**: Early warning system for customer churn.

**What it does**:
- Analyzes mock product usage telemetry (CSV)
- Detects negative engagement trends
- Computes churn risk (0–1)
- Recommends safe next steps to a Customer Success Manager (CSM)

**Key Characteristics**:
- Explainable ML-lite scoring
- Rule-based action routing
- Never contacts customers directly
- Human review required for all actions

**Automation Level**: Level 1 – Shadow Mode

---

### 3️⃣ Negotiator Agent (✅ Complete)

**Purpose**: Real-time whisper coaching during sales calls.

**Planned Behavior**:
- Simulated live transcript chunking
- Detects sentiment and objections in real time
- Suggests short responses to reps ("whispers")

**Status**:
- Phase 1–9 design completed
- Implementation completed

---

## 🧱 Shared Components

Built once and reused across agents:
- Input Loader (mock data)
- Signal Extractors
- Decision Layer (rules + confidence)
- Suggestion Generator (templates / LLM)
- Human Output Formatter
- Feedback Logger (JSONL)
- Kill Switch (global + per-agent)

---

## 🔐 Safety, Governance & Human Control

Safety is **non-negotiable**:
- Explicit consent required for call analysis
- AI only provides suggestions—never actions
- Humans can accept, ignore, or override any output
- No penalties for ignoring AI suggestions
- Global and per-agent kill switches supported

If a kill switch is enabled:
- No analysis is performed
- No outputs are generated
- System safely degrades to manual mode

---

## 📊 Progressive Automation Ladder

| Level | Description |
|------|-------------|
| 0 | Manual (AI off) |
| 1 | Shadow Mode (insights only) ← **Current** |
| 2 | Suggested actions |
| 3 | Conditional automation (high confidence) |
| 4 | Scaled automation with kill switch |

This project intentionally stops at **Level 1**.

---

## 🗂 Repository Structure (High-Level)

```
src/
 ├── agents/
 │   ├── ai_sales_coach/
 │   └── retention_agent/
 ├── shared/
 │   ├── llm/
 │   ├── ml/
 │   ├── input_loader.py
 │   ├── kill_switch.py
 │   └── observability.py
mock-data/
 ├── calls/
 ├── telemetry/
 ├── outputs/
 └── feedback/
docs/
 ├── backbone & architecture docs
 ├── agent documentation
 └── daily updates
tests/
 └── unit tests for all critical components
```

---

## ▶️ How to Run

### AI Sales Coach (Batch)
```
python -m src.agents.ai_sales_coach.run_batch
```

### Retention Agent (Daily Batch)
```
python -m src.agents.retention_agent.run_daily
```

### Negotiator Agent (Batch)
```
python -m src.agents.negotiator_agent.run_stream
```


> All outputs are written to `mock-data/outputs/`

---

## 🧪 Testing

Unit tests cover:
- Signal extraction
- Scoring logic
- Action routing
- Feedback logging
- Kill switch behavior

Run tests with:
```
pytest
```

---

## 📅 Project Status

- ✅ Shared Backbone: Complete
- ✅ AI Sales Coach: Complete (Phase 1–9 verified)
- ✅ Retention Agent: Complete (Phase 1–9 verified)
- 🟡 Negotiator Agent: Implementation pending

---

## 🏁 Final Notes

- This project emphasizes **clarity over complexity**
- Accuracy is less important than **explainability and safety**
- The system is evaluator-ready and extensible

> **AI assists. Humans decide. Safety always wins.**

