# System Diagram (High-Level)

## Purpose
This diagram shows how the whole system works from input to human output.
We use mock data now, but the same flow works with real data later.

---

## High-Level Flow (One Backbone → Three Agents)

(Mock Data)
- Call transcripts (chunked for Negotiator)
- Full call transcripts (for Sales Coach)
- Usage telemetry CSV (for Retention)
- Rep + Customer profiles

        │
        ▼

[Shared Intelligence Backbone]
1) Input Loader (reads mock files)
2) Understanding (extracts signals)
3) Decision (rules + confidence)
4) Human-facing output formatter
5) Feedback logger

        │
        ▼

[Agent Policies (Different outputs, same backbone)]
- Negotiator Agent: real-time whisper suggestions
- Retention Agent: churn risk + alert/message suggestion
- AI Sales Coach: scoring + 3 daily micro-tips

        │
        ▼

[Human in Control]
- Rep or CSM sees suggestions
- Human chooses: accept / ignore / override

        │
        ▼

[Feedback + Observability]
- log: accepted/ignored
- track: usage rate, overrides, impact
