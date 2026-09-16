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
                     query -->  HybridRouter  --(sensor Q?)--> LocalAnswerer
                                     |
                                     +--(everything else)--> CloudClient (Claude)
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
