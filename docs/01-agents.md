# Agent Boundaries (What each agent does and does NOT do)

## Why boundaries matter
We are building 3 helpers that reuse the same backbone.
Each helper has a clear job.
No helper is allowed to “do everything”.

The AI only suggests.
Humans always decide.

---

# 1) Negotiator Agent (Live Whisper Coach)

## What it DOES
- Works during a live sales call (simulated with transcript chunks)
- Reads the current part of the conversation
- Detects customer mood (positive/neutral/negative)
- Detects common objections (price, timing, competitor, trust)
- Suggests a short response the rep can say next

## What it DOES NOT do
- Does not talk to the customer directly
- Does not auto-send messages
- Does not auto-close deals
- Does not force the rep to follow suggestions

## Output to human
- “Whisper suggestion” shown on screen (1–2 lines)
- Optional: objection label + confidence

---

# 2) Retention Agent (Churn Risk Radar)

## What it DOES
- Watches product usage data (mock telemetry)
- Detects usage drops or warning patterns
- Produces a churn risk score (0 to 1)
- Chooses one of these actions:
  - High risk: prepare a re-engagement message (or auto-trigger only if allowed)
  - Medium risk: alert the Customer Success Manager (CSM)
  - Low risk: do nothing

## What it DOES NOT do
- Does not spam customers
- Does not send intrusive outreach
- Does not auto-message unless confidence is high and rules allow it
- Does not make promises to customers

## Output to human
- Risk score + reason (example: “Usage dropped 60% this week”)
- Recommended next action (alert or message draft)

---

# 3) AI Sales Coach (Post-call Performance Coach)

## What it DOES
- Runs after a call ends (batch style, not real-time)
- Reads the full call transcript
- Scores the rep on:
  - Empathy
  - Pacing
  - Objection handling
  - Closing
- Generates 3 short daily improvement tips per rep

## What it DOES NOT do
- Does not judge the rep as a person
- Does not replace a manager
- Does not make HR decisions
- Does not share sensitive call data without consent

## Output to human
- Score summary + 3 micro-tips
- “What to improve next call” suggestions

---

# Shared Safety Rules (All Agents)
- Humans are always in control
- Suggestions can be ignored without penalty
- Consent is required for recording and analysis
- Kill switch exists (global + per-agent)
