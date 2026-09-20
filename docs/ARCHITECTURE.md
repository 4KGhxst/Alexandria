# Architecture

## Design goal

The software was built hardware-agnostic from the start, behind small
interfaces with a working non-hardware implementation for each — that's
now paying off as real hardware (a dedicated Windows mini PC) comes online:

| Concern | Interface | Non-hardware fallback | Real implementation |
|---|---|---|---|
| Vehicle sensors | `ObdBackend` (`diagnostics/obd_interface.py`) | `SimulatorBackend` | `Elm327Backend` — any standard ELM327 OBD-II dongle |
| Speech in | `SpeechToText` (`voice/interfaces.py`) | `TextConsole` (stdin) | `MicrophoneVoice` — `SpeechRecognition` (Google Web Speech API) |
| Speech out | `TextToSpeech` | `TextConsole` (stdout) | `MicrophoneVoice` — `pyttsx3` (offline, OS voices) |
| Wake word | `WakeWordDetector` | no-op | still a no-op — see below |
| AI reasoning | `HybridRouter` | local deterministic tier + Claude API | same, unchanged — the split is a software decision, not a hardware one |

`voice/factory.py` picks `TextConsole` or `MicrophoneVoice` from
`ALEXANDRIA_VOICE_MODE`, so the orchestrator never hardcodes which one is
active. Swapping OBD backends is the same pattern via
`ALEXANDRIA_OBD_BACKEND`. The orchestrator, personality, and knowledge
layers don't change either way.

## Voice I/O

`MicrophoneVoice` (`voice/microphone_voice.py`) is real but intentionally
minimal — it's meant to prove the end-to-end loop works on real hardware,
not to be the final voice stack:

- **STT**: `SpeechRecognition`'s default Google Web Speech recognizer.
  Free, no API key, but needs internet and sends audio to Google — a
  local engine (Vosk, whisper.cpp) is the natural upgrade once the setup
  is proven out, especially for in-car use with unreliable connectivity.
- **TTS**: `pyttsx3`, fully offline, driving whatever voices are already
  installed on the OS (SAPI5 on Windows). Fine for testing; a
  higher-quality/more personality-fitting voice (Piper, ElevenLabs, etc.)
  is a later upgrade, not a blocker.
- **Wake word**: still a no-op — `listen()` is always active whenever the
  main loop calls it, so *any* speech near the mic gets transcribed and
  sent to the router, not just speech directed at Alexandria. That's a
  real limitation for actual in-car use (passengers talking to each other
  would get treated as commands) and the next thing worth building once
  the rest of the loop is confirmed working: Porcupine or openWakeWord
  gate `listen()` behind an actual wake phrase.

## GUI front end

`gui/app.py` (`AlexandriaApp`, tkinter) is a third front end alongside the
terminal (`TextConsole`) and voice (`MicrophoneVoice`) — a real window for
the mini PC instead of a bare shell prompt. It's built directly against
`Orchestrator`, not through the `SpeechToText`/`TextToSpeech` interfaces:
those model a blocking, synchronous loop (`listen()` blocks until speech,
then `speak()`), which doesn't fit a GUI's event-driven model where the
window has to stay responsive while a cloud call is in flight. Two
consequences of that:

- **Cloud calls run on a background thread** (`_answer_in_background`),
  with the result handed back through a `queue.Queue` that the main
  thread drains on a timer (`_drain_responses`, via `root.after`) — the
  standard safe pattern for tkinter, since widgets aren't safe to touch
  directly from a non-main thread.
- **Sensor polling runs on its own timer** (`_background_tick`, every
  `BACKGROUND_TICK_MS`) instead of "once per blocking `listen()` call"
  like the terminal loop's `tick()`-per-turn does — the GUI has no
  equivalent blocking point to hang polling off of.

`gui/formatting.py` holds the pure display-formatting logic (speaker
name, window title, status line, `mood_color()`) with no tkinter import,
specifically so it stays unit-testable on any machine — including this
project's dev sandbox, which has no tkinter or display at all. `gui/theme.py`
holds the color palette and a `ttk.Style` setup (dark background, teal
accent, "clam" as the base ttk theme since it's the one that actually
respects color overrides on Windows — the default theme mostly ignores
them in favor of native chrome). Both are separate from `gui/app.py`
itself, which can only really be verified on a real machine with a
display; if `import tkinter` fails there, Python was installed without
the "tcl/tk and IDLE" option (the python.org Windows installer includes
it by default unless that box gets unchecked during a custom install).

The chat log fakes "bubbles" with `Text` widget tag styling rather than a
custom-drawn canvas: each message is inserted with a small-caps name tag
(no background) followed by a body tag with a colored `background`,
asymmetric left/right margins (`lmargin1/lmargin2/rmargin`) to keep the
bubble from spanning the full width, and `justify` set right for the
driver's messages and left for hers — enough to read as distinct chat
bubbles without needing canvas-based rounded-rectangle drawing.
`mood_color()` feeds the status label's text color, using the same
valence thresholds `EmotionState.mood_description()` already uses (>0.3
good, <-0.3 bad, otherwise neutral) so the color and the text it's
describing never disagree — verified directly in
`test_mood_color_matches_description_thresholds`.

Closing the window (`_on_close`) calls `Orchestrator.end_session()`, the
same shutdown path `run_forever()` hits on `quit` — so the daily memory
note and PDF report get saved the same way regardless of which front end
is running.

## Running persistently

`scripts/windows/run_alexandria.ps1` is a restart-on-exit wrapper: it
loads `.env`, activates the venv, and relaunches `python -m
alexandria.main` if it ever exits, with a `STOP` sentinel file as a manual
kill switch. Registered as a Windows Scheduled Task (trigger: at logon),
this is what makes her survive a crash or a reboot without you opening a
terminal — see the README for the exact Task Scheduler steps. This is
Windows-specific by design, matching the mini PC actually in use; a Linux
box would use systemd instead (a `.service` unit with `Restart=always`
is the equivalent) if that ever comes up.

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
   conversation, and ambient conditions (`personality/emotion_engine.py`),
   translated into concrete delivery instructions by `speech_style.py`
3. Long-term rapport (`personality/relationship.py`) — how familiar she
   is with this driver, persisted across restarts
4. A live diagnostic summary (`HealthMonitor.summarize`)
5. Relevant facts from the local knowledge base *and* the ingested
   service manual, both by keyword match (`Orchestrator._gather_knowledge_snippets`)
6. Recent conversation history (`core/conversation.py`), for within-session
   continuity

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

### Speech style: mood → concrete delivery instructions

A bare mood label ("worry (valence=-0.31, arousal=0.62)") is something an
LLM has to *interpret* into a speaking style, and it'll do that
inconsistently turn to turn. `personality/speech_style.py` closes that gap:
it maps the dominant emotion (or, when nothing's dominant, the raw
valence/arousal quadrant) to an explicit instruction — "shorter, more
clipped sentences" for worry, "terser... a bit short-tempered" for
grumpiness, "warmer and more familiar" for affection, and so on. This is
injected into the system prompt alongside the mood label itself, so the
model has something concrete to act on rather than just a number to guess
a tone from.

### Three kinds of memory, kept deliberately separate

- **`core/conversation.py` (`ConversationMemory`)** — the last ~10
  exchanges, included in every general-conversation cloud call so replies
  have continuity ("what I just said a moment ago"). Cleared on restart;
  this is about a single conversation feeling coherent, not about her
  remembering you tomorrow. Deliberately *not* passed into the manual
  tier's cloud call — that tier's "answer only from these excerpts, or
  refuse" contract stays hermetic, uncontaminated by prior chat.
- **`personality/relationship.py` (`RelationshipTracker`)** — survives
  restarts (a small JSON file), and is the *only* place counting things
  over the long run — total interactions, positive/negative sentiment
  counts, first/last-seen timestamps. Feeds a `familiarity_description()`
  into every system prompt ("just met" through "old friends") — the
  *shape* of the relationship, not its content. Delete the JSON file to
  reset it.
- **`personality/memory_log.py` (`MemoryLog`)** — the *content* of the
  relationship: a short LLM-written summary per day (`llm/session_summary.py`
  generates it at session end from that day's `ConversationMemory`), so
  she can say something like "you mentioned the brakes felt soft
  yesterday" instead of just knowing an abstract familiarity level. The
  last few days' summaries (excluding today's own still-in-progress one)
  get pulled into every system prompt as "what you remember from recent
  days." Deliberately summaries, not raw transcripts — cheap to store and
  re-inject indefinitely, and a summarization pass naturally drops routine
  chit-chat (the model is told to respond `NOTHING NOTABLE` when a day had
  nothing worth keeping, which `summarize_session` turns into `None` —
  no empty or filler entries pile up).

## Daily logging + PDF reports

`diagnostics/daily_log.py` (`DailyLog`) records every OBD snapshot and
diagnostic event to SQLite, grouped by calendar day — this happens
automatically in `Orchestrator.tick()` regardless of whether anyone asks
for it, so a full day's data is always there by the time a report gets
requested. It's the shared backbone for two things: `MemoryLog`-style
recall of vehicle-specific history, and `diagnostics/report_pdf.py`, which
renders a day's `DailyStats` (min/max/avg per metric) and diagnostic
events into a PDF with reportlab — deterministically, no LLM involved, so
the numbers always match exactly what was logged and it works with zero
API key.

A report can be produced three ways, all calling the same
`Orchestrator.generate_daily_report()`:

1. **On demand** — `Orchestrator._maybe_handle_report_command()` matches
   "report" or "pdf" anywhere in what the driver says and handles it
   directly, before the request ever reaches the router. This mirrors the
   local sensor tier's philosophy: a clearly-scoped, deterministic request
   doesn't need to go through conversation at all.
2. **At session end** (`Orchestrator.end_session()`) — makes sure a
   report exists for the day even if nobody explicitly asked, which
   matters since most sessions today start and end well within one
   calendar day rather than running past midnight.
3. **On day rollover** (`Orchestrator._roll_over_day_if_needed()`, called
   from `tick()`) — if she's ever running continuously across midnight,
   the outgoing day gets finalized into a report before logging starts
   for the new one.

All three are best-effort around a missing `reportlab` install (an
optional dependency, `pip install -e ".[reports]"`) — `report_pdf.py`
raises a `RuntimeError` with an actionable message rather than a bare
`ImportError`, `_maybe_handle_report_command` surfaces that message to the
driver, and the two automatic paths (session-end, rollover) just skip
silently rather than crashing the main loop over an optional feature.

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

This strict gate is *only* for the technical tier. `Orchestrator._gather_knowledge_snippets`
separately does an ungated manual search on every query (when a vehicle
is configured) and folds any hits into the general conversational
prompt's knowledge snippets — so a casual question can still pull color
from the manual, it's just flavor for a normal reply rather than a
cited, refuse-if-absent lookup. The two paths intentionally have
different honesty contracts for the same underlying index.

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

- **Hardware choice: resolved** — a dedicated Windows mini PC. Real
  voice I/O and a real OBD-II backend now build against that.
- **Wake word** is still a no-op (see Voice I/O above) — the main
  remaining gap between "works on a test bench" and "usable with other
  people in the car."
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
- **The report command's keyword match ("report"/"pdf") is the same kind
  of hand-tuned heuristic** that caused the "trouble"/"in trouble" false
  trigger earlier — watch for casual sentences that happen to contain
  "report" or "pdf" without meaning to ask for one, and tighten the
  match if that shows up in practice.
- **Day-rollover report generation only fires if the process stays alive
  across midnight.** Given the current operating pattern (restart on exit
  via `run_alexandria.ps1`, not a single long-lived process), `end_session()`
  firing at every shutdown is what actually produces most days' reports in
  practice — the rollover path mainly matters once she's running truly
  continuously.
