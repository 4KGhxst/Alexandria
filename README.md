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

General conversation also loosely draws on the manual (once a vehicle is
configured) — a casual "tell me about your anti-theft system" can pull
color from the manual too, not just exact spec lookups. This path isn't
refuse-gated like the technical tier; it's flavor for a normal reply, not
a cited, guaranteed-accurate answer.

### Personality that persists and grows

- **Conversation memory** — the last ~10 exchanges are included in every
  cloud reply, so she has continuity within a session ("what I just said")
  instead of answering each turn cold.
- **Emotion-driven speech style** — her current mood doesn't just get
  named in the prompt, it comes with concrete delivery instructions
  (shorter/clipped when worried, warmer when affectionate, terser when
  grumpy, etc. — see `personality/speech_style.py`).
- **Rapport that survives restarts** — `alexandria_relationship.json`
  tracks how many times you've talked and how those interactions have
  gone, across every run, and it's fed into her system prompt as a
  familiarity level ("just met" → "old friends"). Delete the file to
  reset the relationship.

### Real voice (mic + speaker)

```bash
pip install -e ".[voice]"
```
```
ALEXANDRIA_VOICE_MODE=microphone
```
Then `python -m alexandria.main` talks and listens through your default
microphone/speaker instead of the terminal. Speech-to-text is Google's
free Web Speech API via the `SpeechRecognition` package (needs internet);
text-to-speech is `pyttsx3`, fully offline (drives the OS's own voices —
SAPI5 on Windows). No wake word yet — it's "always listening" while
running, so anything said near the mic gets transcribed and sent onward.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#voice-io) for the wake-word
roadmap. On Windows, `PyAudio` (needed for microphone access) occasionally
fails to build from source on `pip install`; if so, install a prebuilt
wheel matching your Python version instead.

### Real OBD-II hardware

Plug an ELM327 dongle into the car's OBD-II port (under the dash, near
the steering column on virtually any car from 1996+), pair it in Windows
first if it's Bluetooth, then find which port it landed on:

```bash
pip install -e ".[obd]"
python scripts/list_serial_ports.py
```

Sanity-check the connection on its own before running the full app:

```bash
python scripts/test_obd_connection.py COM3
```

Then point Alexandria at it:

```
ALEXANDRIA_OBD_BACKEND=elm327
ALEXANDRIA_OBD_PORT=COM3
```

### Running persistently (Windows)

`scripts/windows/run_alexandria.ps1` loads `.env`, activates the venv,
and restarts Alexandria if she exits. Register it as a Windows Scheduled
Task so she starts on login without a terminal window:

1. Task Scheduler → **Create Task** (not "Basic Task")
2. **General**: name it "Alexandria"
3. **Triggers** → New → *Begin the task: At log on*
4. **Actions** → New → *Start a program*
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\Alexandria\scripts\windows\run_alexandria.ps1"`
5. **Settings**: check *"If the task fails, restart every: 1 minute"*, and
   uncheck *"Stop the task if it runs longer than..."*

To pause her without touching Task Scheduler, create an empty file named
`STOP` in the repo root — she exits after the current run and won't
restart until you delete it.

## What's here

- **Diagnostics** (`alexandria/diagnostics/`) — an OBD-II abstraction with
  a simulator backend (default, no hardware needed) and an ELM327 backend
  (real dongle, `pip install -e ".[obd]"`), plus a health monitor that
  turns raw readings into events (new trouble code, overheating, low
  fuel, ...).
- **Personality** (`alexandria/personality/`) — an emotion engine with a
  mood (valence/arousal) and named emotions (worry, affection, grumpiness,
  ...) that diagnostics, conversation, and ambient events nudge, and that
  decays back toward baseline over time; `speech_style.py` turns the
  current mood into concrete delivery instructions; `relationship.py`
  persists rapport (interaction count, sentiment history) across restarts;
  static traits and a system prompt builder tie it all into an actual voice.
- **Conversation memory** (`alexandria/core/conversation.py`) — a rolling
  window of recent turns included in cloud replies for within-session
  continuity. Session-only by design; long-term memory is `relationship.py`.
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
- **Voice** (`alexandria/voice/`) — abstract STT/TTS/wake-word interfaces.
  `TextConsole` (default) runs everything from a terminal; `MicrophoneVoice`
  (`ALEXANDRIA_VOICE_MODE=microphone`, `pip install -e ".[voice]"`) uses a
  real mic/speaker. `factory.py` picks between them from config.
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
| `ALEXANDRIA_RELATIONSHIP_PATH` | `alexandria_relationship.json` | JSON file tracking rapport across restarts |
| `ALEXANDRIA_VEHICLE_YEAR` / `_MAKE` / `_MODEL` / `_TRIM` | none | Which vehicle's manual to search (must match what you passed to `ingest_cli.py`) |
| `ALEXANDRIA_VOICE_MODE` | `text` | `text` or `microphone` |
