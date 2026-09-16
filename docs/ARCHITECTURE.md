# Architecture

## Design goal

Hardware is undecided, but the software shouldn't wait on that decision.
Every module that would eventually touch real hardware sits behind a small
interface, with a working non-hardware implementation today:

| Concern | Interface | Today | Real hardware later |
|---|---|---|---|
| Vehicle sensors | `ObdBackend` (`diagnostics/obd_interface.py`) | `SimulatorBackend` | `Elm327Backend` (any standard OBD-II dongle) |
| Speech in | `SpeechToText` (`voice/interfaces.py`) | `TextConsole` (stdin) | Platform STT (Vosk/Whisper on a Pi, Android SpeechRecognizer, iOS Speech) |
| Speech out | `TextToSpeech` | `TextConsole` (stdout) | Platform TTS (Piper/espeak-ng, Android/iOS TTS) |
| Wake word | `WakeWordDetector` | no-op | Porcupine/openWakeWord, or platform assistant hooks |
| AI reasoning | `HybridRouter` | local deterministic tier + Claude API | same, unchanged — the split is a software decision, not a hardware one |

Whatever hardware you land on (Raspberry Pi + mic/speaker wired into the
dash, an Android head unit, or a phone mount talking to the car over a
Bluetooth OBD-II adapter), only the four interfaces above need a new
implementation. The orchestrator, personality, and knowledge layers don't
change.

## Data flow

```
OBD backend --snapshot--> HealthMonitor --DiagnosticEvent--> EmotionEngine
                                                                   |
Driver speech --STT--> Orchestrator --UserInteractionEvent-->-----+
                                                                   |
                                                             EmotionState
                                                                   |
                                          Persona.build_system_prompt()
                                                                   |
                     query -->  HybridRouter  --(sensor Q?)-------> LocalAnswerer
                                     |
                                     +--(technical Q + vehicle set?)--> ManualAnswerer
                                     |                                        |
                                     |                          ManualLibrary.search (FTS5)
                                     |                                  /          \
                                     |                          no hits            hits found
                                     |                             |                   |
                                     |                        refusal          CloudClient (Claude),
                                     |                                         grounded to excerpts only
                                     |
                                     +--(everything else)--> CloudClient (Claude), full persona prompt
                                                                   |
                                                              response --TTS--> driver
```

## Why a hybrid brain, not just "call Claude for everything"

Direct sensor questions ("what's my coolant temp?", "any check engine
codes?") are answered from the live OBD snapshot with zero network calls:
instant, works with no signal, and can never hallucinate a number that
doesn't match the dashboard. Everything that needs judgment, personality,
or general/automotive knowledge — which is most of what makes this feel
like a "living car" rather than a gauge cluster — goes to Claude with a
system prompt assembled from:

1. Static personality traits (`personality/traits.py`)
2. Current mood, computed by `EmotionEngine` from recent diagnostics,
   conversation, and ambient conditions (`personality/emotion_engine.py`)
3. A live diagnostic summary (`HealthMonitor.summarize`)
4. Relevant facts pulled from the local knowledge base by keyword match

## Personality model

`EmotionState` tracks a continuous mood (`valence` -1..1, `arousal` 0..1)
plus named emotion intensities (`contentment`, `worry`, `excitement`,
`grumpiness`, `affection`, `boredom`), each 0..1. Events nudge these
directly:

- A critical diagnostic spikes `worry` (and `grumpiness` if severe) and
  drags `valence` down.
- A positive interaction raises `affection`/`contentment`; a negative one
  raises `grumpiness`.
- Ambient conditions (long idle time, long trip, time of day) make small,
  slower adjustments — mostly to `arousal` and `boredom`.

`EmotionEngine.tick(dt_seconds)` relaxes everything back toward a
baseline over time, so a single bad diagnostic doesn't sour the car's mood
forever, and the current dominant emotion (if any is above a small noise
floor) is what actually gets named in the system prompt — otherwise mood
falls back to a plain valence/arousal description ("content and calm").

## Manual tier: Alldata-style Q&A

The manual tier (`llm/manual_rag.py`, `manuals/`) exists because "torque
specs, procedures, part info" is exactly the kind of thing an LLM will
confidently make up a plausible-sounding wrong answer for — and a wrong
torque spec or wrong step order is worse than no answer. So this tier
never lets the model answer from its own training knowledge:

1. `HybridRouter` runs `looks_technical(query)` — a keyword heuristic
   (`torque`, `spec`, `procedure`, `part number`, `capacity`, `install`,
   ...) — on any query the local sensor tier didn't handle. This only
   fires when a `Vehicle` is configured (`ALEXANDRIA_VEHICLE_*` env vars)
   and a `ManualLibrary` is wired in.
2. If it looks technical, `ManualLibrary.search()` runs a BM25 full-text
   search (SQLite FTS5) over that vehicle's ingested manual chunks.
   - **No hits** → `ManualAnswerer` returns a plain refusal ("I don't
     have anything on that in the service manual...") without calling
     the cloud model at all. This is the hard guarantee: no manual match,
     no answer.
   - **Hits found** → the matched excerpts (with page numbers) go into a
     system prompt that instructs Claude to answer *only* from those
     excerpts, cite the page after each fact, and say plainly if the
     excerpts don't actually cover the question rather than filling the
     gap with outside knowledge. This is the second guard: retrieval
     finding *something* doesn't guarantee it answers the question, so
     the model is told to say so rather than stretch a tangential match.
3. Anything that doesn't look technical (mood, chit-chat, general trivia)
   skips this tier entirely and goes to the normal conversational tier.

`looks_technical` is a heuristic, not a classifier — false negatives just
fall through to normal chat (fine), false positives get manual-searched
and, if nothing matches, refused (also fine — no cost beyond a wasted
local search). Tune the keyword list in `manual_rag.py` as you notice gaps.

### Ingestion pipeline

`manuals/pdf_extract.py` pulls per-page text out of a PDF with `pypdf`.
`manuals/chunking.py` splits each page into ~1000-character chunks with
overlap — chunking *per page* (never merging across a page boundary)
means every chunk can cite an exact page number. `manuals/manual_library.py`
stores chunks in a SQLite FTS5 virtual table keyed by `vehicle.key()`
(e.g. `2015-honda-civic`), so multiple vehicles' manuals can share one
database file without cross-contaminating search results.

No embeddings model or vector database is used — BM25 keyword search is a
strong match for manual lookups, since queries usually contain the exact
distinctive terms (component names, part numbers, DTC codes) that appear
in the source text, and it costs nothing to build or query beyond disk
space. If fuzzy/semantic matching becomes worth the complexity later
(e.g. "the thing that keeps the belt tight" instead of "tensioner"),
swap `ManualLibrary.search()` for an embeddings index without touching
any caller.

### Adding manuals

`python -m alexandria.manuals.ingest_cli <pdf> --year Y --make M --model
Mo --title "..."` ingests one PDF. Run it once per manual (factory
service manual, Haynes/Chilton, a wiring-diagram supplement, TSB
compilations from eManualOnline or similar) — everything accumulates in
the same database and search draws from all of it for that vehicle.

## Growing the knowledge base

`KnowledgeBase` is SQLite-backed (`knowledge/knowledge_base.py`) and loads
`alexandria/knowledge/seed_data/*.json` on first run if empty. Add more
JSON files in the same shape (`topic`, `category`, `content`, `tags`) to
grow what Alexandria knows — pull in your specific vehicle's service
manual intervals, its known common failure points, or just more trivia.
Search is keyword/tag matching, which scales fine into the thousands of
facts; if it ever needs to go further (tens of thousands+), swap the
`search()` method for an embeddings-based index without touching any
caller.

## Open questions / next steps

- **Hardware choice.** Raspberry Pi gives the most control (real GPIO,
  any mic/speaker, full Linux) but means building an enclosure and
  power setup; an Android head unit or phone gets you a screen and
  mic/speaker for free but constrains the runtime.
- **Wake word + STT/TTS** are stubbed pending that hardware choice.
- **Local LLM tier** currently only covers deterministic sensor lookups.
  A true on-device model (for the "hybrid" reasoning tier to fall back to
  when offline, beyond raw sensor values) is a natural next step once
  hardware is picked, since model size/quantization choices depend on
  what it runs on.
- **Manual tier is text-only.** Scanned manual pages with no OCR text
  layer extract as empty strings and simply won't match any search —
  worth running scanned PDFs through OCR before ingesting if that comes up.
- **`looks_technical` is a hand-tuned keyword list**, not a classifier.
  Watch for real queries it misses (falls through to normal chat, which
  will answer from general knowledge rather than refusing) and add
  keywords as gaps show up.
