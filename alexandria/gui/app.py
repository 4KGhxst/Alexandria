"""A real desktop window for Alexandria, instead of a bare PowerShell/terminal.

Built directly against the Orchestrator rather than through the
SpeechToText/TextToSpeech interfaces: those model a blocking, synchronous
loop (call listen(), block until speech, call speak()), which doesn't fit
a GUI's event-driven model. Background sensor polling also needs to run
on a timer here instead of "once per blocking listen() call" like the
terminal loop does.

Uses tkinter because it ships with the standard python.org Windows
installer by default — no extra dependency needed for the window itself.
If `import tkinter` fails, the Python install was likely done without the
"tcl/tk and IDLE" feature checked; reinstall Python with that box checked.

Cloud calls happen on a background thread so the window never freezes
while waiting on a response — results come back through a thread-safe
queue, drained on the main thread via `root.after`, which is the standard
safe pattern for updating tkinter widgets from work done off the main
thread (tkinter widgets themselves are not thread-safe to touch directly).
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator
from alexandria.gui.formatting import speaker_name, status_text, window_title
from alexandria.voice.interfaces import TextConsole

BACKGROUND_TICK_MS = 10_000
QUEUE_POLL_MS = 200


class AlexandriaApp:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator
        self._responses: queue.Queue[str] = queue.Queue()

        self.root = tk.Tk()
        self.root.title(window_title(orchestrator.traits))
        self.root.geometry("640x720")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_label = tk.Label(self.root, text="", anchor="w", fg="#555555")
        self.status_label.pack(fill="x", padx=10, pady=(10, 0))

        self.log = scrolledtext.ScrolledText(self.root, state="disabled", wrap="word", font=("Segoe UI", 10))
        self.log.pack(fill="both", expand=True, padx=10, pady=10)
        self.log.tag_config("user", foreground="#1a4d8f")
        self.log.tag_config("assistant", foreground="#222222")

        entry_frame = tk.Frame(self.root)
        entry_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.entry = tk.Entry(entry_frame, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", lambda _event: self._on_send())
        self.entry.focus_set()
        self.send_button = tk.Button(entry_frame, text="Send", command=self._on_send)
        self.send_button.pack(side="left", padx=(8, 0))

    def run(self) -> None:
        self.orchestrator.start()
        self.orchestrator.tick()
        self._append(speaker_name(self.orchestrator.traits), f"{window_title(self.orchestrator.traits)} is online.")
        self._refresh_status()
        self.root.after(BACKGROUND_TICK_MS, self._background_tick)
        self.root.after(QUEUE_POLL_MS, self._drain_responses)
        self.root.mainloop()

    def _on_send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._append("You", text)
        self.send_button.config(state="disabled")
        threading.Thread(target=self._answer_in_background, args=(text,), daemon=True).start()

    def _answer_in_background(self, text: str) -> None:
        response = self.orchestrator.handle_user_text(text)
        self._responses.put(response)

    def _drain_responses(self) -> None:
        try:
            while True:
                response = self._responses.get_nowait()
                self._append(speaker_name(self.orchestrator.traits), response)
                self.send_button.config(state="normal")
                self._refresh_status()
        except queue.Empty:
            pass
        self.root.after(QUEUE_POLL_MS, self._drain_responses)

    def _background_tick(self) -> None:
        self.orchestrator.tick()
        self._refresh_status()
        self.root.after(BACKGROUND_TICK_MS, self._background_tick)

    def _append(self, speaker: str, text: str) -> None:
        tag = "user" if speaker == "You" else "assistant"
        self.log.config(state="normal")
        self.log.insert("end", f"{speaker}: {text}\n\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _refresh_status(self) -> None:
        self.status_label.config(text=status_text(self.orchestrator))

    def _on_close(self) -> None:
        self.orchestrator.end_session()
        self.root.destroy()


def main() -> None:
    config = Config.from_env()
    # Force text mode regardless of ALEXANDRIA_VOICE_MODE: the GUI is its
    # own input/output surface (typed text in a window), and shouldn't
    # trigger microphone hardware init as a side effect of construction.
    orchestrator = Orchestrator(config, voice=TextConsole())
    AlexandriaApp(orchestrator).run()


if __name__ == "__main__":
    main()
