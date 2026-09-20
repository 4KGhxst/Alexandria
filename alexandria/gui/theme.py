"""Color palette and ttk styling for the desktop window — a dark,
dashboard-like look instead of stock tkinter gray. Needs a real tkinter
install/display, same as app.py; kept as its own module so app.py stays
focused on layout and behavior rather than color constants.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONT_FAMILY = "Segoe UI"

BG = "#101215"
PANEL_BG = "#1c1f24"

ASSISTANT_BUBBLE_BG = "#262b33"
ASSISTANT_TEXT = "#e5e7eb"

USER_BUBBLE_BG = "#2dd4bf"
USER_TEXT = "#0d1a18"

NAME_LABEL = "#8b93a1"
STATUS_DEFAULT = "#a7adb8"

ENTRY_BG = "#1c1f24"
ENTRY_TEXT = "#e5e7eb"

ACCENT = "#2dd4bf"
ACCENT_ACTIVE = "#5eead4"
BUTTON_TEXT = "#0d1a18"
BUTTON_DISABLED_BG = "#3a3f47"
BUTTON_DISABLED_TEXT = "#6b7280"


def apply_ttk_style(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    # "clam" is the base ttk theme that actually respects background/
    # foreground color overrides on Windows — the default "vista" theme
    # ignores most of them in favor of native widget chrome.
    style.theme_use("clam")

    style.configure(
        "Alexandria.TEntry",
        fieldbackground=ENTRY_BG,
        foreground=ENTRY_TEXT,
        insertcolor=ENTRY_TEXT,
        bordercolor=PANEL_BG,
        borderwidth=1,
        padding=8,
    )

    style.configure(
        "Alexandria.TButton",
        background=ACCENT,
        foreground=BUTTON_TEXT,
        borderwidth=0,
        padding=(16, 8),
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Alexandria.TButton",
        background=[("disabled", BUTTON_DISABLED_BG), ("active", ACCENT_ACTIVE)],
        foreground=[("disabled", BUTTON_DISABLED_TEXT)],
    )

    return style
