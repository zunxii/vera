# VERA — Merchant & Customer Engagement Engine

Vera is magicpin's stateful AI engagement engine built around the core composition contract:

```python
compose(category, merchant, trigger, customer?)
```

It selects the single strongest contextual business signal from available context sources, constructs a deterministic message brief, and generates natural, grounded WhatsApp outreach.

---

## 🏗️ Architecture Overview

```
POST /v1/context ──► ContextStore (Versioned & Idempotent)
                           │
POST /v1/tick ────► ContextResolver ──► TriggerPlanner ──► SignalSelector ──► MessageBrief ──► EngagementService ──► Validator ──► Action
                           │
POST /v1/reply ───► ConversationStore ──► ConversationPolicy ──► ContextResolver ─────────────┘
```

### Key Modules

- **`ContextStore`**: Manages atomic context versioning (`Accepted=True`, stale version `409`, scope validation).
- **`ContextResolver`**: Binds trigger, merchant, category, and optional customer state dynamically per request without caching.
- **`TriggerPlanner`**: Evaluates active triggers against suppression keys, expiry, and recipient scope.
- **`FactProjector`**: Projects relevant facts dynamically across 4 contexts without hardcoded trigger branches.
- **`SignalSelector`**: Ranks fact candidates by relevance, timeliness, actionable cues, and category/family weights to pick ONE primary signal.
- **`EngagementService`**: Unified composition brain shared across `/tick` (proactive) and `/reply` (reactive) flows.
- **`MessageValidator`**: Strictly grounds numerical claims, expands float percentages/currencies, enforces TABOO rules, normalizes CTA enums, and auto-declares used facts.

---

## 🧠 Decision Quality & Composition Rules

1. **Deterministic Signal Selection**: Rather than dumping raw JSON to the LLM, the application determines **WHAT** matters (`SignalSelector`), and the LLM determines **HOW** to express it naturally.
2. **Category Voice Adaptivity**:
   - **Dentists**: Clinical-peer tone, technical terminology allowed, "Dr." honorific used.
   - **Salons**: Warm, practical, service-oriented.
   - **Restaurants**: Operator-to-operator, covers, AOV, delivery radius, offers.
   - **Gyms**: Motivational, evidence-based coaching.
   - **Pharmacies**: Trustworthy, precise, conservative.
3. **Anti-Hallucination & Numerical Grounding**:
   - All numerical claims (percentages, prices, dates) are grounded against supplied facts.
   - Decimal floats (e.g. `-0.4`) are expanded to match natural language variations (e.g. `40%`, `40`).
   - Strict CTA enums (`open_ended`, `binary_yes_no`, `multi_choice_slot`, `action`).

---

## ⚡ Multi-turn Reply & Conversation Handling

- **Commitment Transition**: Direct agreement (e.g. *"Yes, let's do it"*, *"Book it"*) immediately transitions into `ACTION` mode rather than asking redundant qualification questions.
- **Auto-Reply Loop Prevention**: Fingerprints repeated inbound messages and escalates wait durations before gracefully terminating persistent bot loops.
- **Opt-Out / Hostility**: Instantly ends conversations on opt-out signals (*"unsubscribe"*, *"stop messaging"*) or hostile responses.

---

## 🚀 Local Setup & Running

### Requirements
- Python 3.10+
- Google Gemini API Key (`GEMINI_API_KEY`)

### Quickstart

1. **Install Dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   cp .env.example .env
   # Set GEMINI_API_KEY in .env
   ```

3. **Start Bot Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

4. **Run Unit Tests**:
   ```bash
   pytest -q
   ```

5. **Run Official Judge Simulator**:
   ```bash
   BOT_URL=http://localhost:8080 TEST_SCENARIO=all python judge_simulator.py
   ```
