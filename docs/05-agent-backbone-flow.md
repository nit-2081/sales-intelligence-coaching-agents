# Agent ↔ Backbone Flow (How each agent uses the same pipeline)

## Shared Backbone Reminder
All agents use the same steps:
Input → Understand → Decide → Suggest to Human → Log Feedback

The only difference is:
- the input type
- the decision rules
- the final suggestion shown to the human

---

# 1) Negotiator Agent (Live Whisper Coaching)

## Input
- Transcript text in small chunks (simulated streaming)
- Optional: rep + customer profile context

Example input:
- "Customer: This price feels expensive."

## Understand (signals extracted)
- sentiment: negative / concerned
- objection type: price

## Decide
- if objection detected → generate a suggested response
- confidence score: how sure we are (example: 0.85)

## Suggest to Human
- Output shown to rep as a whisper:
  - Suggested response (1–2 lines)
  - Objection label (price)
  - Confidence score

## Log Feedback
- Rep action:
  - accepted / ignored / edited
- Store for metrics and improvement

---

# 2) Retention Agent (Churn Risk Radar)

## Input
- Usage telemetry data per customer over time (CSV)
- Optional: customer profile context

Example input:
- logins dropped from 18 → 5 in Week 4

## Understand (signals extracted)
- usage trend: dropping sharply
- feature usage: decreasing
- engagement risk pattern detected

## Decide
- churn score: 0 to 1
- action selection:
  - High risk (>= 0.80): prepare re-engagement message
  - Medium risk (0.50–0.79): alert CSM for review
  - Low risk (< 0.50): no action

## Suggest to Human
- Output shown to CSM:
  - churn score + reason
  - recommended action
  - optional: safe message draft

## Log Feedback
- CSM action:
  - sent / ignored / postponed / modified
- Store for evaluating false positives and impact

---

# 3) AI Sales Coach (Post-Call Coaching)

## Input
- Full call transcript (call complete)
- Rep profile context

Example input:
- entire transcript of call_01.txt

## Understand (signals extracted)
- empathy signals (acknowledgement, tone)
- pacing signals (too long without pauses, long monologues)
- objection handling signals
- closing attempt signals

## Decide
- score categories:
  - empathy
  - pacing
  - objection handling
  - closing
- pick top 2–3 improvement areas

## Suggest to Human
- Output shown to rep/manager:
  - score summary
  - 3 micro-improvement tips (short and actionable)

## Log Feedback
- Rep/manager action:
  - helpful / not helpful feedback
  - which tip they tried
- Store for improvement tracking
