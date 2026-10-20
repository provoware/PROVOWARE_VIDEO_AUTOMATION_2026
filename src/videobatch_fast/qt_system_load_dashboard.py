from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QWidget

from .system_load import SystemLoadSampler


class SystemLoadDashboard:
    """Compact read-only CPU/RAM/SWAP dashboard kept outside the main Qt window."""

    def __init__(self, parent: QWidget) -> None:
        self.sampler = SystemLoadSampler()
        self.bars: dict[str, QProgressBar] = {}
        self.frame = QFrame(parent)
        self.frame.setObjectName("loadDashboard")
        row = QHBoxLayout(self.frame)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(5)
        for key, label in (("cpu", "CPU"), ("ram", "RAM"), ("swap", "SWAP")):
            caption = QLabel(label)
            caption.setObjectName("loadLabel")
            caption.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            bar = QProgressBar()
            bar.setObjectName("loadMeter")
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("—")
            bar.setTextVisible(True)
            bar.setFixedWidth(58)
            bar.setAccessibleName(f"{label}-Auslastung")
            self.bars[key] = bar
            row.addWidget(caption)
            row.addWidget(bar)
        self.timer = QTimer(parent)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    @staticmethod
    def memory_text(used_bytes: int, total_bytes: int) -> str:
        gib = float(1024 ** 3)
        if total_bytes <= 0:
            return "aus"
        return f"{used_bytes / gib:.1f}/{total_bytes / gib:.1f} GiB"

    def _set_bar(self, key: str, percent: float | None, tooltip: str) -> None:
        bar = self.bars[key]
        if percent is None:
            bar.setValue(0)
            bar.setFormat("—")
        else:
            value = max(0, min(100, int(round(percent))))
            bar.setValue(value)
            bar.setFormat(f"{value}%")
        bar.setToolTip(tooltip)
        bar.setAccessibleDescription(tooltip)

    def refresh(self) -> None:
        sample = self.sampler.sample()
        self._set_bar("cpu", sample.cpu_percent, "CPU-Auslastung seit der letzten Messung.")
        self._set_bar(
            "ram",
            sample.ram_percent,
            f"RAM: {self.memory_text(sample.ram_used_bytes, sample.ram_total_bytes)}",
        )
        self._set_bar(
            "swap",
            sample.swap_percent,
            f"SWAP: {self.memory_text(sample.swap_used_bytes, sample.swap_total_bytes)}",
        )
