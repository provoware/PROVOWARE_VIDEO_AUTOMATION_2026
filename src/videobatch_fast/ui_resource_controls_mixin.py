from __future__ import annotations

from pathlib import Path
from tkinter import BooleanVar, StringVar, ttk

from .execution_control import RAM_LIMIT_PRESETS_GB
from .system_resources import SystemResourceMonitor, format_bytes
from .text_resources import text


class UiResourceControlsMixin:
    """Compact process controls and honest Linux system-load telemetry."""

    def _build_resource_process_panel(self, parent, *, row: int) -> None:
        panel = ttk.Frame(parent, style="ShellCard.TFrame", padding=(0, 10, 0, 0))
        panel.grid(row=row, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)
        self._resource_monitor = SystemResourceMonitor()
        self._resource_vars = {
            key: StringVar(value=text("ui.resources.metric_pending", label=label))
            for key, label in (
                ("cpu", text("ui.resources.label_cpu")),
                ("ram", text("ui.resources.label_ram")),
                ("swap", text("ui.resources.label_swap")),
                ("zram", text("ui.resources.label_zram")),
                ("disk", text("ui.resources.label_disk_free")),
            )
        }
        self._process_progress_text = StringVar(value=text("ui.resources.progress_initial"))
        self._process_control_text = StringVar(value=text("ui.resources.status_ready"))
        self._cpu_limit_50_var = BooleanVar(value=bool(self.config.get("cpu_limit_50", False)))
        configured_ram = float(self.config.get("ram_limit_gb", 0) or 0)
        self._ram_limit_vars = {
            value: BooleanVar(value=configured_ram == value) for value in RAM_LIMIT_PRESETS_GB
        }
        self._configured_ram_limit = configured_ram if configured_ram in RAM_LIMIT_PRESETS_GB else None
        self._build_progress_strip(panel)
        self._build_load_strip(panel)
        self._build_limit_strip(panel)
        self.root.after(50, self._apply_initial_resource_limits)
        self.root.after(250, self._poll_resource_process_panel)

    def _build_progress_strip(self, parent) -> None:
        progress = ttk.Frame(parent, style="ShellCard.TFrame")
        progress.grid(row=0, column=0, sticky="ew")
        progress.columnconfigure(0, weight=1)
        progress.columnconfigure(1, weight=1)
        ttk.Label(
            progress,
            text=text("ui.resources.process_header"),
            style="SectionHeader.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(progress, textvariable=self._process_control_text, style="Hint.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        ttk.Label(
            progress,
            text=text("ui.resources.total"),
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Label(
            progress,
            text=text("ui.resources.current_job"),
            style="Hint.TLabel",
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(5, 0))
        ttk.Progressbar(progress, variable=self.total_progress, maximum=100).grid(
            row=2, column=0, sticky="ew", padx=(0, 4), pady=(2, 2)
        )
        ttk.Progressbar(progress, variable=self.job_progress, maximum=100).grid(
            row=2, column=1, sticky="ew", padx=(4, 0), pady=(2, 2)
        )
        ttk.Label(progress, textvariable=self._process_progress_text, style="Hint.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

    def _build_load_strip(self, parent) -> None:
        section = ttk.Frame(parent, style="ShellCard.TFrame")
        section.grid(row=1, column=0, sticky="ew", pady=(10, 5))
        ttk.Label(
            section,
            text=text("ui.resources.system_load"),
            style="SectionHeader.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 3))
        for column in range(3):
            section.columnconfigure(column, weight=1)
        placements = {
            "cpu": (1, 0),
            "ram": (1, 1),
            "disk": (1, 2),
            "swap": (2, 0),
            "zram": (2, 1),
        }
        for key, (grid_row, column) in placements.items():
            ttk.Label(section, textvariable=self._resource_vars[key], style="Hint.TLabel").grid(
                row=grid_row,
                column=column,
                sticky="w",
                padx=(0 if column == 0 else 8, 0),
                pady=1,
            )

    @staticmethod
    def _ram_label(value: float) -> str:
        display = str(value).replace(".", ",") if value % 1 else str(int(value))
        return text("ui.resources.ram_limit", value=display)

    def _build_limit_strip(self, parent) -> None:
        section = ttk.Frame(parent, style="ShellCard.TFrame")
        section.grid(row=2, column=0, sticky="ew", pady=(7, 0))
        section.columnconfigure(0, weight=1)
        ttk.Label(
            section,
            text=text("ui.resources.resource_limits"),
            style="SectionHeader.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 3))
        limits = ttk.Frame(section, style="ShellCard.TFrame")
        limits.grid(row=1, column=0, sticky="ew")
        ttk.Checkbutton(
            limits,
            text=text("ui.resources.cpu_limit_50"),
            variable=self._cpu_limit_50_var,
            command=self._toggle_cpu_limit,
        ).pack(side="left", padx=(0, 10))
        for value in RAM_LIMIT_PRESETS_GB:
            ttk.Checkbutton(
                limits,
                text=self._ram_label(value),
                variable=self._ram_limit_vars[value],
                command=lambda selected=value: self._toggle_ram_limit(selected),
            ).pack(side="left", padx=(0, 6))
        transport = ttk.Frame(section, style="ShellCard.TFrame")
        transport.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(
            transport,
            text=text("ui.resources.pause_help"),
            style="Hint.TLabel",
        ).pack(side="left")
        self._resume_render_button = ttk.Button(
            transport,
            text=text("ui.resources.resume"),
            command=self._resume_render,
            state="disabled",
        )
        self._resume_render_button.pack(side="right")
        self._pause_render_button = ttk.Button(
            transport,
            text=text("ui.resources.pause"),
            command=self._pause_render,
            state="disabled",
        )
        self._pause_render_button.pack(side="right", padx=(0, 6))

    def _apply_initial_resource_limits(self) -> None:
        self.runner.set_cpu_limit_50(bool(self._cpu_limit_50_var.get()))
        self.runner.set_memory_limit_gb(self._configured_ram_limit)

    def _toggle_cpu_limit(self) -> None:
        enabled = bool(self._cpu_limit_50_var.get())
        self.runner.set_cpu_limit_50(enabled)
        self.config["cpu_limit_50"] = enabled
        self._persist_resource_settings()

    def _toggle_ram_limit(self, selected: float) -> None:
        enabled = bool(self._ram_limit_vars[selected].get())
        for value, variable in self._ram_limit_vars.items():
            if value != selected:
                variable.set(False)
        limit = selected if enabled else None
        self.runner.set_memory_limit_gb(limit)
        self.config["ram_limit_gb"] = limit or 0
        self._persist_resource_settings()

    def _persist_resource_settings(self) -> None:
        save = getattr(self, "_save_settings", None)
        if callable(save):
            save()

    def _pause_render(self) -> None:
        if self.runner.running:
            self.runner.pause()
            self._process_control_text.set(text("ui.resources.status_paused"))

    def _resume_render(self) -> None:
        self.runner.resume()
        self._process_control_text.set(text("ui.resources.status_resumed"))

    def _poll_resource_process_panel(self) -> None:
        if not hasattr(self, "_resource_monitor"):
            return
        try:
            path = Path(self.output_dir.get()).expanduser()
            snapshot = self._resource_monitor.sample(path)
            self._update_resource_labels(snapshot)
            self._update_process_labels()
        finally:
            self.root.after(1000, self._poll_resource_process_panel)

    def _update_resource_labels(self, snapshot) -> None:
        self._resource_vars["cpu"].set(
            text("ui.resources.metric_cpu", percent=f"{snapshot.cpu_percent:.0f}")
        )
        self._resource_vars["ram"].set(
            text(
                "ui.resources.metric_usage",
                label=text("ui.resources.label_ram"),
                used=format_bytes(snapshot.ram_used),
                total=format_bytes(snapshot.ram_total),
            )
        )
        self._resource_vars["swap"].set(
            text(
                "ui.resources.metric_usage",
                label=text("ui.resources.label_swap"),
                used=format_bytes(snapshot.swap_used),
                total=format_bytes(snapshot.swap_total),
            )
        )
        self._resource_vars["zram"].set(
            text(
                "ui.resources.metric_usage",
                label=text("ui.resources.label_zram"),
                used=format_bytes(snapshot.zram_used),
                total=format_bytes(snapshot.zram_total),
            )
        )
        self._resource_vars["disk"].set(
            text("ui.resources.metric_disk_free", free=format_bytes(snapshot.disk_free))
        )

    def _update_process_labels(self) -> None:
        total = float(self.total_progress.get())
        job = float(self.job_progress.get())
        self._process_progress_text.set(
            text(
                "ui.resources.progress",
                total=f"{total:.1f}",
                job=f"{job:.1f}",
                phase=self.phase.get(),
                eta=self.eta.get(),
            )
        )
        running = bool(self.runner.running)
        paused = bool(self.runner.paused)
        self._pause_render_button.configure(state="normal" if running and not paused else "disabled")
        self._resume_render_button.configure(state="normal" if running and paused else "disabled")
        if not running:
            self._process_control_text.set(text("ui.resources.status_ready"))
        elif paused:
            self._process_control_text.set(text("ui.resources.status_paused"))
        else:
            self._process_control_text.set(text("ui.resources.status_active"))
