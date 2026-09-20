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
Orchestrator itself is safe to call from that background thread too —
see the lock in core/orchestrator.py.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator
from alexandria.gui import theme
from alexandria.gui.formatting import mood_color, speaker_name, status_text, window_title
from alexandria.voice.interfaces import TextConsole

BACKGROUND_TICK_MS = 10_000
QUEUE_POLL_MS = 200


class AlexandriaApp:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator
        self._responses: queue.Queue[str] = queue.Queue()

        self.root = tk.Tk()
        self.root.title(window_title(orchestrator.traits))
        self.root.geometry("640x760")
        self.root.minsize(420, 480)
        self.root.configure(bg=theme.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        theme.apply_ttk_style(self.root)

        self._build_widgets()

    def _build_widgets(self) -> None:
        header = tk.Frame(self.root, bg=theme.BG)
        header.pack(fill="x", padx=16, pady=(14, 6))

        title = tk.Label(
            header,
            text=window_title(self.orchestrator.traits),
            bg=theme.BG,
            fg=theme.ENTRY_TEXT,
            font=(theme.FONT_FAMILY, 14, "bold"),
            anchor="w",
        )
        title.pack(fill="x")

        self.status_label = tk.Label(
            header,
            text="",
            bg=theme.BG,
            fg=theme.STATUS_DEFAULT,
            font=(theme.FONT_FAMILY, 9),
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(2, 0))

        log_frame = tk.Frame(self.root, bg=theme.PANEL_BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=10)

        self.log = scrolledtext.ScrolledText(
            log_frame,
            state="disabled",
            wrap="word",
            font=(theme.FONT_FAMILY, 10),
            bg=theme.PANEL_BG,
            fg=theme.ASSISTANT_TEXT,
            insertbackground=theme.ASSISTANT_TEXT,
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.log.pack(fill="both", expand=True)
        self._configure_log_tags()

        entry_frame = tk.Frame(self.root, bg=theme.BG)
        entry_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.entry = ttk.Entry(entry_frame, style="Alexandria.TEntry", font=(theme.FONT_FAMILY, 10))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda _event: self._on_send())
        self.entry.focus_set()

        self.send_button = ttk.Button(
            entry_frame, text="Send", style="Alexandria.TButton", command=self._on_send
        )
        self.send_button.pack(side="left", padx=(10, 0))

    def _configure_log_tags(self) -> None:
        name_font = (theme.FONT_FAMILY, 8, "bold")
        bubble_font = (theme.FONT_FAMILY, 10)

        self.log.tag_configure(
            "user_name",
            foreground=theme.NAME_LABEL,
            font=name_font,
            justify="right",
            rmargin=10,
            spacing1=10,
        )
        self.log.tag_configure(
            "user_bubble",
            background=theme.USER_BUBBLE_BG,
            foreground=theme.USER_TEXT,
            font=bubble_font,
            justify="right",
            lmargin1=80,
            lmargin2=80,
            rmargin=10,
            spacing3=6,
        )
        self.log.tag_configure(
            "assistant_name",
            foreground=theme.NAME_LABEL,
            font=name_font,
            justify="left",
            lmargin1=10,
            lmargin2=10,
            spacing1=10,
        )
        self.log.tag_configure(
            "assistant_bubble",
            background=theme.ASSISTANT_BUBBLE_BG,
            foreground=theme.ASSISTANT_TEXT,
            font=bubble_font,
            justify="left",
            lmargin1=10,
            lmargin2=10,
            rmargin=80,
            spacing3=6,
        )

    def run(self) -> None:
        self.orchestrator.start()
        self.orchestrator.tick()
        self._append_assistant(
            speaker_name(self.orchestrator.traits),
            "Online. Say something, or just close the window when you're done.",
        )
        self._refresh_status()
        self.root.after(BACKGROUND_TICK_MS, self._background_tick)
        self.root.after(QUEUE_POLL_MS, self._drain_responses)
        self.root.mainloop()

    def _on_send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._append_user(text)
        self.send_button.config(state="disabled")
        threading.Thread(target=self._answer_in_background, args=(text,), daemon=True).start()

    def _answer_in_background(self, text: str) -> None:
        response = self.orchestrator.handle_user_text(text)
        self._responses.put(response)

    def _drain_responses(self) -> None:
        try:
            while True:
                response = self._responses.get_nowait()
                self._append_assistant(speaker_name(self.orchestrator.traits), response)
                self.send_button.config(state="normal")
                self._refresh_status()
        except queue.Empty:
            pass
        self.root.after(QUEUE_POLL_MS, self._drain_responses)

    def _background_tick(self) -> None:
        self.orchestrator.tick()
        self._refresh_status()
        self.root.after(BACKGROUND_TICK_MS, self._background_tick)

    def _append_user(self, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", "You\n", "user_name")
        self.log.insert("end", f"{text}\n\n", "user_bubble")
        self.log.see("end")
        self.log.config(state="disabled")

    def _append_assistant(self, speaker: str, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", f"{speaker}\n", "assistant_name")
        self.log.insert("end", f"{text}\n\n", "assistant_bubble")
        self.log.see("end")
        self.log.config(state="disabled")

    def _refresh_status(self) -> None:
        self.status_label.config(
            text=status_text(self.orchestrator),
            fg=mood_color(self.orchestrator.emotion_engine.state),
        )

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
