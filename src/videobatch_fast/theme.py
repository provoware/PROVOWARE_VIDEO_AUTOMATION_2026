from __future__ import annotations

from pathlib import Path
from tkinter import ttk

from .registry import load_json

THEME_LABELS = {
    "neon_gravity": "Midnight Blue",
    "acid_paper": "Emerald Tech",
    "toxic_candy": "Violet Pulse",
    "ultraviolet": "Amber Graphite",
}


def _hex_rgb(value: str) -> tuple[float, float, float]:
    raw = value.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return 0.0, 0.0, 0.0
    return tuple(int(raw[index:index + 2], 16) / 255.0 for index in (0, 2, 4))


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(value: str) -> float:
    red, green, blue = _hex_rgb(value)
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def best_text_color(background: str, *, dark: str = "#111318", light: str = "#FAFCFF") -> str:
    """Return the readable foreground for arbitrary field backgrounds."""
    return dark if contrast_ratio(background, dark) >= contrast_ratio(background, light) else light


def safe_text_color(background: str, preferred: str, minimum: float = 4.5) -> str:
    """Keep theme intent when readable, otherwise force a contrast-safe color."""
    return preferred if contrast_ratio(background, preferred) >= minimum else best_text_color(background)


def available_themes() -> dict[str, str]:
    return dict(THEME_LABELS)


def _load_theme(name: str) -> dict:
    selected = name if name in THEME_LABELS else "neon_gravity"
    return load_json(f"resources/themes/{selected}.json")


def _palette(theme: dict) -> dict[str, str]:
    values = theme["colors"]
    return {
        "bg": values["background_main"],
        "panel": values["background_surface"],
        "panel2": values["background_elevated"],
        "preview": values["background_preview"],
        "toolbar": values.get("background_toolbar", values["background_surface"]),
        "border": values["border_default"],
        "border_subtle": values.get("border_subtle", values["border_default"]),
        "text": values["text_primary"],
        "muted": values["text_secondary"],
        "text_muted": values.get("text_muted", values["text_secondary"]),
        "accent": values["action_primary"],
        "accent_text": values["action_primary_text"],
        "secondary": values.get("action_secondary", values["background_elevated"]),
        "accent2": values["status_information"],
        "active": values["status_active"],
        "success": values["status_success"],
        "warning": values["status_warning"],
        "attention": values["status_attention"],
        "danger": values["status_error"],
        "selection": values["state_selected"],
        "hover": values["state_hover"],
        "disabled": values["state_disabled"],
        "tile_gold": values["tile_gold"],
        "tile_magenta": values["tile_magenta"],
        "tile_green": values["tile_green"],
        "tile_blue": values["tile_blue"],
    }


_THEME = _load_theme("neon_gravity")
COLORS = _palette(_THEME)
ACTIVE_THEME = "neon_gravity"


def _activate_theme(name: str) -> None:
    global _THEME, ACTIVE_THEME
    selected = name if name in THEME_LABELS else "neon_gravity"
    _THEME = _load_theme(selected)
    COLORS.clear()
    COLORS.update(_palette(_THEME))
    ACTIVE_THEME = selected


def apply_theme(root, scale_percent: int = 100, theme_name: str = "neon_gravity") -> None:
    _activate_theme(theme_name)
    metrics = _THEME.get("metrics", {})
    factor = max(0.8, min(2.0, scale_percent / 100.0))
    root.configure(bg=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    base = max(10, round(int(metrics.get("base_font", 11)) * factor))
    title = max(18, round(int(metrics.get("title_font", 25)) * factor))
    section = max(13, round(int(metrics.get("section_font", 15)) * factor))
    row_height = max(29, round(int(metrics.get("row_height", 32)) * factor))
    px = max(8, round(int(metrics.get("button_padding_x", 12)) * factor))
    py = max(6, round(int(metrics.get("button_padding_y", 8)) * factor))

    field_text = safe_text_color(COLORS["panel2"], COLORS["text"])
    panel_text = safe_text_color(COLORS["panel"], COLORS["text"])
    selected_text = safe_text_color(COLORS["selection"], COLORS["text"])
    heading_text = safe_text_color(COLORS["panel2"], COLORS["muted"])
    toolbar_text = safe_text_color(COLORS["toolbar"], COLORS["text"])
    toolbar_muted = safe_text_color(COLORS["toolbar"], COLORS["muted"])
    panel_muted = safe_text_color(COLORS["panel"], COLORS["muted"])

    root.option_add("*Font", ("DejaVu Sans", base))
    root.option_add("*TCombobox*Listbox.background", COLORS["panel2"])
    root.option_add("*TCombobox*Listbox.foreground", field_text)
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
    root.option_add("*TCombobox*Listbox.selectForeground", selected_text)
    root.option_add("*Entry.background", COLORS["panel2"])
    root.option_add("*Entry.foreground", field_text)
    root.option_add("*Entry.insertBackground", field_text)
    root.option_add("*Listbox.background", COLORS["panel2"])
    root.option_add("*Listbox.foreground", field_text)
    root.option_add("*Listbox.selectBackground", COLORS["selection"])
    root.option_add("*Listbox.selectForeground", selected_text)
    root.option_add("*Text.background", COLORS["panel2"])
    root.option_add("*Text.foreground", field_text)
    root.option_add("*Text.insertBackground", field_text)

    style.configure(
        ".",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["panel2"],
        bordercolor=COLORS["border_subtle"],
        lightcolor=COLORS["border_subtle"],
        darkcolor=COLORS["border_subtle"],
        padding=5,
    )
    style.configure("Card.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1, bordercolor=COLORS["border_subtle"])
    style.configure("GoldCard.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1, bordercolor=COLORS["accent"])
    style.configure("Header.TFrame", background=COLORS["toolbar"], relief="solid", borderwidth=1, bordercolor=COLORS["border_subtle"])
    style.configure("Toolbar.TFrame", background=COLORS["toolbar"])
    style.configure("Preview.TFrame", background=COLORS["preview"], relief="solid", borderwidth=1, bordercolor=COLORS["border"])
    style.configure("WorkflowCard.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1, bordercolor=COLORS["border_subtle"])
    style.configure("WorkflowTitle.TLabel", background=COLORS["panel"], foreground=safe_text_color(COLORS["panel"], COLORS["accent2"]), font=("DejaVu Sans", section, "bold"))
    style.configure("WorkflowHint.TLabel", background=COLORS["panel"], foreground=panel_muted, font=("DejaVu Sans", max(10, base - 1)))

    style.configure("Title.TLabel", background=COLORS["toolbar"], foreground=toolbar_text, font=("DejaVu Sans", title, "bold"))
    style.configure("HeaderTitle.TLabel", background=COLORS["toolbar"], foreground=toolbar_text, font=("DejaVu Sans", max(15, section + 1), "bold"))
    style.configure("HeaderHint.TLabel", background=COLORS["toolbar"], foreground=toolbar_muted, font=("DejaVu Sans", max(10, base - 1)))
    style.configure("HeaderValue.TLabel", background=COLORS["selection"], foreground=selected_text, padding=(7, 5), font=("DejaVu Sans", base, "bold"))
    style.configure("DialogTitle.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("DejaVu Sans", max(17, title - 5), "bold"))
    style.configure("Subtitle.TLabel", background=COLORS["toolbar"], foreground=toolbar_muted)
    style.configure("Section.TLabel", background=COLORS["panel"], foreground=panel_text, font=("DejaVu Sans", section, "bold"))
    style.configure("SectionHeader.TLabel", background=COLORS["panel"], foreground=safe_text_color(COLORS["panel"], COLORS["accent2"]), font=("DejaVu Sans", section, "bold"))
    style.configure("Hint.TLabel", background=COLORS["panel"], foreground=panel_muted)
    style.configure("Muted.TLabel", background=COLORS["panel"], foreground=safe_text_color(COLORS["panel"], COLORS["text_muted"]))
    style.configure("Status.TLabel", background=COLORS["toolbar"], foreground=safe_text_color(COLORS["toolbar"], COLORS["accent2"]), padding=(8, 5), font=("DejaVu Sans", base, "bold"))
    style.configure("VersionBadge.TLabel", background=COLORS["accent"], foreground=COLORS["accent_text"], padding=(9, 4), font=("DejaVu Sans", max(10, base - 1), "bold"))
    style.configure("StatusPill.TLabel", background=COLORS["selection"], foreground=selected_text, padding=(9, 4), font=("DejaVu Sans", max(10, base - 1), "bold"))
    style.configure("Success.TLabel", background=COLORS["panel"], foreground=COLORS["success"], font=("DejaVu Sans", base, "bold"))
    style.configure("Warning.TLabel", background=COLORS["panel"], foreground=COLORS["warning"], font=("DejaVu Sans", base, "bold"))
    style.configure("Error.TLabel", background=COLORS["panel"], foreground=COLORS["danger"], font=("DejaVu Sans", base, "bold"))

    style.configure("TButton", background=COLORS["secondary"], foreground=best_text_color(COLORS["secondary"]), padding=(px, py), borderwidth=1, relief="flat")
    style.configure("HeaderControl.TButton", background=COLORS["panel2"], foreground=field_text, padding=(9, 5), font=("DejaVu Sans", base, "bold"), borderwidth=1)
    style.map("HeaderControl.TButton", background=[("active", COLORS["selection"]), ("focus", COLORS["accent2"])], foreground=[("focus", best_text_color(COLORS["accent2"]))])
    style.map("TButton", background=[("active", COLORS["hover"]), ("focus", COLORS["selection"]), ("disabled", COLORS["disabled"])], foreground=[("active", best_text_color(COLORS["hover"])), ("focus", selected_text), ("disabled", best_text_color(COLORS["disabled"]))], bordercolor=[("focus", COLORS["accent2"])])
    style.configure("Accent.TButton", background=COLORS["accent"], foreground=COLORS["accent_text"], padding=(px + 2, py + 1), font=("DejaVu Sans", base, "bold"), borderwidth=1, bordercolor=COLORS["accent"])
    style.map("Accent.TButton", background=[("active", COLORS["selection"]), ("focus", COLORS["accent2"]), ("disabled", COLORS["disabled"])], foreground=[("active", best_text_color(COLORS["selection"])), ("focus", best_text_color(COLORS["accent2"])), ("disabled", best_text_color(COLORS["disabled"]))], bordercolor=[("focus", COLORS["accent2"])])
    style.configure("Ghost.TButton", background=COLORS["panel2"], foreground=field_text, padding=(px, py), font=("DejaVu Sans", base, "bold"), borderwidth=1, bordercolor=COLORS["border"])
    style.configure("Danger.TButton", background=COLORS["danger"], foreground=best_text_color(COLORS["danger"]), padding=(px, py), font=("DejaVu Sans", base, "bold"))
    style.configure("Success.TButton", background=COLORS["success"], foreground=best_text_color(COLORS["success"]), padding=(px, py), font=("DejaVu Sans", base, "bold"))

    tile_font = ("DejaVu Sans", base + 1, "bold")
    for name, color in (
        ("TileGold.TButton", COLORS["tile_gold"]),
        ("TilePink.TButton", COLORS["tile_magenta"]),
        ("TileGreen.TButton", COLORS["tile_green"]),
        ("TileBlue.TButton", COLORS["tile_blue"]),
    ):
        fg = best_text_color(color)
        style.configure(name, background=color, foreground=fg, padding=(15, 18), font=tile_font, borderwidth=0, anchor="center")
        style.map(name, background=[("active", color)], relief=[("pressed", "sunken")])

    calendar_font = ("DejaVu Sans", max(9, base - 1))
    calendar_styles = {
        "CalendarNone": COLORS["panel2"],
        "CalendarSuccess": COLORS["success"],
        "CalendarWarning": COLORS["warning"],
        "CalendarError": COLORS["danger"],
        "CalendarInfo": COLORS["accent2"],
        "CalendarActive": COLORS["active"],
    }
    for prefix, bg in calendar_styles.items():
        fg = best_text_color(bg)
        style.configure(prefix + ".TButton", background=bg, foreground=fg, padding=(1, 1), font=calendar_font)
        style.configure(prefix + ".TLabel", background=bg, foreground=fg, padding=(1, 1), anchor="center", font=calendar_font)

    style.configure("ChoiceCard.TFrame", background=COLORS["panel2"], relief="solid", borderwidth=2, bordercolor=COLORS["accent2"])
    style.configure("ChoiceTitle.TLabel", background=COLORS["panel2"], foreground=field_text, font=("DejaVu Sans", section, "bold"))
    style.configure("ChoiceHint.TLabel", background=COLORS["panel2"], foreground=safe_text_color(COLORS["panel2"], COLORS["muted"]))
    style.configure("ChoiceStatus.TLabel", background=COLORS["panel2"], foreground=safe_text_color(COLORS["panel2"], COLORS["accent2"]), font=("DejaVu Sans", base, "bold"))
    style.configure("Recommended.TLabel", background=COLORS["accent"], foreground=COLORS["accent_text"], padding=(8, 4), font=("DejaVu Sans", max(9, base - 2), "bold"))
    style.configure("Choice.TRadiobutton", background=COLORS["panel"], foreground=panel_text, padding=(12, 12), font=("DejaVu Sans", base, "bold"), indicatorcolor=COLORS["panel2"], borderwidth=1)
    style.map("Choice.TRadiobutton", background=[("active", COLORS["hover"]), ("selected", COLORS["selection"])], foreground=[("selected", selected_text)], indicatorcolor=[("selected", COLORS["accent2"])])

    style.configure("QuickMode.TButton", background=COLORS["panel2"], foreground=field_text, padding=(9, 10), anchor="center", font=("DejaVu Sans", base, "bold"), borderwidth=1)
    style.map("QuickMode.TButton", background=[("active", COLORS["hover"])])
    style.configure("QuickModeSelected.TButton", background=COLORS["selection"], foreground=selected_text, padding=(9, 10), anchor="center", font=("DejaVu Sans", base, "bold"), borderwidth=1, bordercolor=COLORS["accent2"])
    style.map("QuickModeSelected.TButton", background=[("active", COLORS["hover"]), ("focus", COLORS["selection"])], bordercolor=[("focus", COLORS["accent2"])])

    style.configure("TEntry", fieldbackground=COLORS["panel2"], foreground=field_text, insertcolor=field_text, bordercolor=COLORS["border_subtle"], padding=(8, 7))
    style.map("TEntry", bordercolor=[("focus", COLORS["accent2"])])
    style.configure("TCombobox", fieldbackground=COLORS["panel2"], foreground=field_text, arrowcolor=COLORS["accent2"], bordercolor=COLORS["border_subtle"], padding=(7, 6))
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["panel2"]), ("disabled", COLORS["disabled"])],
        foreground=[("readonly", field_text), ("disabled", best_text_color(COLORS["disabled"]))],
        selectbackground=[("readonly", COLORS["selection"])],
        selectforeground=[("readonly", selected_text)],
    )
    style.configure("TCheckbutton", background=COLORS["panel"], foreground=panel_text)

    style.configure("TSeparator", background=COLORS["border_subtle"])
    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=panel_text, rowheight=row_height, borderwidth=0)
    style.map("Treeview", background=[("selected", COLORS["selection"])], foreground=[("selected", selected_text)])
    style.configure("Treeview.Heading", background=COLORS["panel2"], foreground=heading_text, font=("DejaVu Sans", base, "bold"), padding=(8, 7), relief="flat")
    style.map("Treeview.Heading", background=[("active", COLORS["hover"])], foreground=[("active", best_text_color(COLORS["hover"]))])

    style.configure("MediaDialog.TFrame", background=COLORS["bg"])
    style.configure("MediaToolbar.TFrame", background=COLORS["toolbar"], relief="solid", borderwidth=1, bordercolor=COLORS["border_subtle"])
    style.configure("MediaCard.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1, bordercolor=COLORS["border_subtle"])
    style.configure("MediaPreview.TFrame", background=COLORS["preview"], relief="solid", borderwidth=2, bordercolor=COLORS["accent2"])
    style.configure("MediaPreview.TLabel", background=COLORS["preview"], foreground=best_text_color(COLORS["preview"]), font=("DejaVu Sans", base, "bold"))
    style.configure("MediaMode.TButton", background=COLORS["panel2"], foreground=field_text, padding=(12, 7), font=("DejaVu Sans", base, "bold"))
    style.configure("MediaModeSelected.TButton", background=COLORS["accent2"], foreground=best_text_color(COLORS["accent2"]), padding=(12, 7), font=("DejaVu Sans", base, "bold"))

    style.configure("Horizontal.TProgressbar", background=COLORS["active"], troughcolor=COLORS["panel2"], bordercolor=COLORS["border_subtle"], lightcolor=COLORS["active"], darkcolor=COLORS["active"], thickness=max(12, round(14 * factor)))
    style.configure("Job.Horizontal.TProgressbar", background=COLORS["accent2"], troughcolor=COLORS["panel2"], thickness=max(12, round(14 * factor)))
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=COLORS["panel2"], foreground=COLORS["muted"], padding=(16, 10), borderwidth=1, font=("DejaVu Sans", base, "bold"))
    style.map("TNotebook.Tab", background=[("selected", COLORS["selection"]), ("active", COLORS["hover"])], foreground=[("selected", selected_text), ("active", best_text_color(COLORS["hover"]))], bordercolor=[("selected", COLORS["accent2"]), ("active", COLORS["border_subtle"])])
    style.configure("TPanedwindow", background=COLORS["border_subtle"], sashwidth=max(6, round(7 * factor)))
