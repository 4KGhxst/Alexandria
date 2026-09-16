# Alexandria

A personality-driven AI co-pilot for a car: it monitors vehicle health,
knows a growing library of maintenance facts and automotive trivia, and
talks to the driver with a mood that shifts based on what's happening —
diagnostics, conversation, and ambient conditions.

Hardware hasn't been chosen yet, so the software core is built
hardware-agnostic: everything runs today against a built-in OBD-II
simulator and a text console, and swaps to real hardware later by
implementing one interface each (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # add your ANTHROPIC_API_KEY to talk to the cloud brain
export $(cat .env | xargs)

python -m alexandria.main
```

Without an `ANTHROPIC_API_KEY`, direct sensor questions ("what's my
coolant temperature?") still work instantly and offline — only
conversational/knowledge questions need the API key.

Run the tests:

```bash
pytest
```

## What's here

- **Diagnostics** (`alexandria/diagnostics/`) — an OBD-II abstraction with
  a simulator backend (default, no hardware needed) and an ELM327 backend
  (real dongle, `pip install -e ".[obd]"`), plus a health monitor that
  turns raw readings into events (new trouble code, overheating, low
  fuel, ...).
- **Personality** (`alexandria/personality/`) — an emotion engine with a
  mood (valence/arousal) and named emotions (worry, affection, grumpiness,
  ...) that diagnostics, conversation, and ambient events nudge, and that
  decays back toward baseline over time; plus static traits and a system
  prompt builder that turns "current mood" into an actual voice.
- **Knowledge** (`alexandria/knowledge/`) — a local SQLite-backed store of
  maintenance facts, DTC explanations, and trivia. Ships with a small
  seed set (`alexandria/knowledge/seed_data/*.json`) — grow those files
  (or your vehicle's real service manual) to expand what Alexandria knows.
- **LLM** (`alexandria/llm/`) — the hybrid brain. A local deterministic
  tier answers direct sensor questions instantly and offline; everything
  else routes to Claude with a system prompt built from persona + current
  mood + relevant knowledge + live diagnostics.
- **Voice** (`alexandria/voice/`) — abstract STT/TTS/wake-word interfaces
  with a `TextConsole` stand-in so the whole system runs from a terminal
  today.
- **Core** (`alexandria/core/`) — the event types everything else speaks,
  and the orchestrator that wires it all together.

## Configuration

Set via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Enables the cloud LLM tier |
| `ALEXANDRIA_MODEL` | `claude-sonnet-5` | Model for cloud responses |
| `ALEXANDRIA_OBD_BACKEND` | `simulator` | `simulator` or `elm327` |
| `ALEXANDRIA_OBD_PORT` | none | Serial port for a real ELM327 dongle |
