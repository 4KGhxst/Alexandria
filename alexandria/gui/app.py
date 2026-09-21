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

Each chat message is its own Label widget rather than a run of tagged
text in a single Text widget — a Text widget's tag background fills the
entire wrapped line width regardless of how short the text is, which
makes "bubbles" that just span the window instead of hugging the message.
A Label sizes itself to its own content (up to `wraplength`), so its
background naturally wraps tightly around just that message.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator
from alexandria.gui import theme
from alexandria.gui.formatting import mood_color, speaker_name, status_text, window_title
from alexandria.gui.logo import SpinningLogo
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
        header.pack(fill="x", padx=16, pady=(10, 6))

        self.logo = SpinningLogo(header)
        self.logo.pack()

        self.status_label = tk.Label(
            header,
            text="",
            bg=theme.BG,
            fg=theme.STATUS_DEFAULT,
            font=(theme.FONT_FAMILY, 9),
            anchor="center",
        )
        self.status_label.pack(fill="x", pady=(2, 0))

        log_frame = tk.Frame(self.root, bg=theme.PANEL_BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=10)

        self.log_canvas = tk.Canvas(log_frame, bg=theme.PANEL_BG, borderwidth=0, highlightthickness=0)
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_canvas.yview)
        self.log_canvas.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side="right", fill="y")
        self.log_canvas.pack(side="left", fill="both", expand=True)

        self.messages_frame = tk.Frame(self.log_canvas, bg=theme.PANEL_BG)
        self._messages_window = self.log_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.messages_frame.bind("<Configure>", self._on_messages_frame_resize)
        self.log_canvas.bind("<Configure>", self._on_canvas_resize)
        self.log_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

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

    def _on_messages_frame_resize(self, _event: object) -> None:
        self.log_canvas.configure(scrollregion=self.log_canvas.bbox("all"))

    def _on_canvas_resize(self, event: object) -> None:
        self.log_canvas.itemconfig(self._messages_window, width=event.width)

    def _on_mousewheel(self, event: object) -> None:
        self.log_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def run(self) -> None:
        self.orchestrator.start()
        self.orchestrator.tick()
        self._append_bubble(
            "assistant",
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
        self._append_bubble("user", "You", text)
        self.send_button.config(state="disabled")
        threading.Thread(target=self._answer_in_background, args=(text,), daemon=True).start()

    def _answer_in_background(self, text: str) -> None:
        response = self.orchestrator.handle_user_text(text)
        self._responses.put(response)

    def _drain_responses(self) -> None:
        try:
            while True:
                response = self._responses.get_nowait()
                self._append_bubble("assistant", speaker_name(self.orchestrator.traits), response)
                self.send_button.config(state="normal")
                self._refresh_status()
        except queue.Empty:
            pass
        self.root.after(QUEUE_POLL_MS, self._drain_responses)

    def _background_tick(self) -> None:
        self.orchestrator.tick()
        self._refresh_status()
        self.root.after(BACKGROUND_TICK_MS, self._background_tick)

    def _append_bubble(self, role: str, speaker: str, text: str) -> None:
        is_user = role == "user"
        side = "e" if is_user else "w"

        row = tk.Frame(self.messages_frame, bg=theme.PANEL_BG)
        row.pack(fill="x", padx=6, pady=(8, 0))

        column = tk.Frame(row, bg=theme.PANEL_BG)
        column.pack(anchor=side)

        name_label = tk.Label(
            column,
            text=speaker,
            bg=theme.PANEL_BG,
            fg=theme.NAME_LABEL,
            font=(theme.FONT_FAMILY, 8, "bold"),
        )
        name_label.pack(anchor=side)

        bubble = tk.Label(
            column,
            text=text,
            bg=theme.USER_BUBBLE_BG if is_user else theme.ASSISTANT_BUBBLE_BG,
            fg=theme.USER_TEXT if is_user else theme.ASSISTANT_TEXT,
            font=(theme.FONT_FAMILY, 10),
            justify="left",
            wraplength=theme.BUBBLE_MAX_WIDTH,
            padx=10,
            pady=8,
        )
        bubble.pack(anchor=side, pady=(2, 0))

        # Force geometry to recompute now so the scrollregion/auto-scroll
        # below account for this message's actual size immediately,
        # rather than on the next idle cycle.
        self.messages_frame.update_idletasks()
        self.log_canvas.configure(scrollregion=self.log_canvas.bbox("all"))
        self.log_canvas.yview_moveto(1.0)

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
