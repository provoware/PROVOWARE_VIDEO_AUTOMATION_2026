from __future__ import annotations

from tkinter import StringVar, ttk

from .canonical_shell_contract import CANONICAL_THEME_LABELS, FONT_PROFILES


def build_dashboard_scheduler_card(owner, parent):
    """Build the scheduler card without changing dashboard state semantics."""
    card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
    ttk.Label(card, text="Startzeituhr", style="SectionHeader.TLabel").pack(anchor="w")
    owner._dashboard_scheduler_summary = StringVar(
        value="Deaktiviert bis Checkpoint 5 · kein automatischer Start"
    )
    scheduler = ttk.Label(
        card,
        textvariable=owner._dashboard_scheduler_summary,
        style="Hint.TLabel",
        justify="left",
    )
    scheduler.pack(anchor="w", fill="x", pady=(7, 8))
    scheduler.bind(
        "<Configure>",
        lambda event: scheduler.configure(wraplength=max(180, event.width - 4)),
        add="+",
    )
    ttk.Button(
        card,
        text="◷ Startzeituhr · Checkpoint 5",
        state="disabled",
    ).pack(fill="x")
    return card


def build_dashboard_appearance_card(owner, parent):
    """Build appearance controls while delegating state changes to the owner."""
    card = ttk.Frame(parent, style="ShellCard.TFrame", padding=(14, 12))
    card.columnconfigure(0, weight=1)
    ttk.Label(card, text="Darstellung", style="SectionHeader.TLabel").grid(
        row=0,
        column=0,
        sticky="w",
    )
    appearance_hint = ttk.Label(
        card,
        text="Theme und Schrift wirken sofort und werden gespeichert.",
        style="Hint.TLabel",
    )
    appearance_hint.grid(row=1, column=0, sticky="ew", pady=(3, 6))
    owner._dashboard_appearance_hint = appearance_hint
    appearance_hint.bind(
        "<Configure>",
        lambda event: appearance_hint.configure(wraplength=max(180, event.width - 4)),
        add="+",
    )

    theme_reverse = {label: key for key, label in CANONICAL_THEME_LABELS.items()}
    controls = ttk.Frame(card, style="ShellCard.TFrame")
    controls.grid(row=2, column=0, sticky="ew")
    controls.columnconfigure(0, weight=1)
    controls.columnconfigure(1, weight=1)
    ttk.Label(controls, text="Theme", style="Hint.TLabel").grid(
        row=0, column=0, sticky="w", padx=(0, 4)
    )
    ttk.Label(controls, text="Schrift", style="Hint.TLabel").grid(
        row=0, column=1, sticky="w", padx=(4, 0)
    )
    owner.shell_theme_combo = ttk.Combobox(
        controls,
        values=list(theme_reverse),
        state="readonly",
    )
    owner.shell_theme_combo.set(
        CANONICAL_THEME_LABELS.get(owner.theme_name.get(), "Midnight Blue")
    )
    owner.shell_theme_combo.grid(row=1, column=0, sticky="ew", padx=(0, 4))
    owner.shell_theme_combo.bind(
        "<<ComboboxSelected>>",
        lambda _event: owner._set_canonical_theme(
            theme_reverse[owner.shell_theme_combo.get()]
        ),
    )

    owner.shell_font_combo = ttk.Combobox(
        controls,
        values=list(FONT_PROFILES),
        state="readonly",
    )
    owner.shell_font_combo.set(owner._font_profile_for_scale(owner.global_font_scale.get()))
    owner.shell_font_combo.grid(row=1, column=1, sticky="ew", padx=(4, 0))
    owner.shell_font_combo.bind(
        "<<ComboboxSelected>>",
        lambda _event: owner._set_global_zoom(
            FONT_PROFILES[owner.shell_font_combo.get()]
        ),
    )
    return card
