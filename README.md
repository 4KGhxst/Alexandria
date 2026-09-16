# Alexandria

A personality-driven AI co-pilot for a car: it monitors vehicle health,
knows a growing library of maintenance facts and automotive trivia,
answers Alldata-style technical questions (torque specs, procedures, part
info) straight from your vehicle's own service manual, and talks to the
driver with a mood that shifts based on what's happening — diagnostics,
conversation, and ambient conditions.

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

### Loading service manuals (Alldata-style Q&A)

Download a factory service manual PDF for your vehicle (e.g. from
eManualOnline or similar) and ingest it once:

```bash
python -m alexandria.manuals.ingest_cli \
    ~/Downloads/2015-honda-civic-fsm.pdf \
    --year 2015 --make Honda --model Civic \
    --title "2015 Honda Civic Factory Service Manual"
```

Then tell Alexandria which vehicle it's riding in (also in `.env`):

```bash
ALEXANDRIA_VEHICLE_YEAR=2015
ALEXANDRIA_VEHICLE_MAKE=Honda
ALEXANDRIA_VEHICLE_MODEL=Civic
```

Technical questions ("what's the oil drain plug torque spec?", "how do I
replace the cabin air filter?") now get answered strictly from that
manual, with page citations. If nothing in the manual covers the
question, Alexandria says so explicitly rather than guessing — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#manual-tier-alldata-style-qa)
for why. Ingest as many manuals per vehicle as you want (factory manual,
Haynes, a wiring supplement) — search draws from all of them.

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
- **Manuals** (`alexandria/manuals/`) — an Alldata-style local library:
  ingest a service manual PDF once (`ingest_cli.py`) and get full-text,
  page-cited search over it forever after via SQLite FTS5, entirely
  offline. No embeddings/vector DB or extra API needed to build or query.
- **LLM** (`alexandria/llm/`) — the hybrid brain, three tiers. (1) Local
  deterministic: direct sensor questions, instant and offline. (2)
  Manual: technical/spec/procedure questions, answered strictly from the
  ingested manual or refused if not found there — never a guessed spec.
  (3) Cloud conversational: everything else, routed to Claude with a
  system prompt built from persona + current mood + relevant knowledge +
  live diagnostics.
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
| `ALEXANDRIA_MANUALS_DB` | `alexandria_manuals.db` | SQLite file for the ingested manual library |
| `ALEXANDRIA_VEHICLE_YEAR` / `_MAKE` / `_MODEL` / `_TRIM` | none | Which vehicle's manual to search (must match what you passed to `ingest_cli.py`) |
