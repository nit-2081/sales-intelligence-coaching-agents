# Shared Intelligence Backbone

## What are we building?
We are building one shared intelligence system that helps humans make better sales decisions.

The system never talks to customers directly.
The system only suggests actions to humans.

This same backbone is reused by:
- Negotiator Agent
- Retention Agent
- AI Sales Coach

---

## Core Flow (Same for all agents)

Every agent follows this exact flow:

1. Input  
2. Understand  
3. Decide  
4. Suggest to Human  
5. Log Feedback  

---

## Step-by-step Explanation (Simple)

### 1. Input
The system receives information such as:
- Call transcript text
- Product usage data
- Rep or customer profile

This data can be real or mock.

---

### 2. Understand
The system looks at the input and tries to understand:
- Is the customer happy, confused, or frustrated?
- Is usage increasing or dropping?
- Did the rep handle objections well?

This step extracts signals from the data.

---

### 3. Decide
Based on understanding, the system decides:
- Should it suggest something?
- Should it alert a human?
- Or should it do nothing?

Decisions are based on confidence and simple rules.

---

### 4. Suggest to Human
If needed, the system shows a suggestion to a human:
- A sentence to say
- A warning message
- Coaching tips

The human always decides whether to use it or ignore it.

---

### 5. Log Feedback
The system records what happened:
- Was the suggestion used or ignored?
- Did it help?

This is used only for learning and improvement.

---

## Important Rules
- Humans are always in control
- AI never auto-speaks to customers
- AI never takes final decisions
