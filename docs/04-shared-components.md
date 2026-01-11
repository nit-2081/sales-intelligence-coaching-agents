# Shared Components (Built Once, Reused Everywhere)

## Why shared components?
All 3 agents use the same backbone.
So we build common parts once to avoid duplicate work.

---

## 1) Input Loader
**Job:** Reads mock data files and converts them into a clean format.
**Used by:** All agents.

Inputs:
- mock-data/calls/*.txt
- mock-data/telemetry/usage.csv
- mock-data/profiles/*.json

Output:
- standard JSON objects (clean structured data)

---

## 2) Transcript Chunker (for Negotiator)
**Job:** Splits a call transcript into small chunks (simulating live streaming).
**Used by:** Negotiator Agent.

Output:
- chunk text + chunk number

---

## 3) Signal Extractor
**Job:** Pulls useful signals from input text/data.
Examples:
- sentiment (positive/neutral/negative)
- objection type (price, timing, trust, competitor)
- usage drop patterns (telemetry)

**Used by:** All agents.

---

## 4) Decision Layer (Rules + Confidence)
**Job:** Decides what action to take based on signals.
Examples:
- if churn risk high → suggest re-engagement
- if objection detected → suggest response
- if coaching gap detected → suggest micro-tip

**Used by:** All agents.

Output:
- decision + confidence score + short reasons

---

## 5) Suggestion Generator (LLM Templates Later)
**Job:** Produces a short suggestion text in a structured format.
Today: can be basic templates.
Later: can use LLM with strict JSON output.

**Used by:** Negotiator + Sales Coach (and optionally Retention for message drafts).

---

## 6) Human Output Formatter
**Job:** Formats results into something readable for humans.
Example outputs:
- whisper coaching line for rep
- churn alert card for CSM
- 3 coaching tips for rep

**Used by:** All agents.

---

## 7) Feedback Logger
**Job:** Stores what the human did with the suggestion.
Logs:
- accepted / ignored / edited
- timestamp
- agent type
- short context

**Used by:** All agents.

---

## 8) Kill Switch Checker
**Job:** A simple check that can disable:
- all agents (global)
- a specific agent

When ON:
- system stops generating suggestions safely

**Used by:** All agents.
