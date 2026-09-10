from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class DialogSection:
    title: str
    body: str


class _BoolChoice:
    """Small compatibility adapter for old `.remember.get()` call sites."""

    def __init__(self, checkbox: QCheckBox | None = None) -> None:
        self._checkbox = checkbox

    def bind(self, checkbox: QCheckBox) -> None:
        self._checkbox = checkbox

    def get(self) -> bool:
        return bool(self._checkbox and self._checkbox.isChecked())


def _section_card(section: DialogSection) -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    title = QLabel(section.title)
    title.setObjectName("section")
    body = QLabel(section.body)
    body.setObjectName("subtitle")
    body.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(body)
    return card


class GuidedDecisionDialog(QDialog):
    """Qt replacement for the reusable Tk security/decision dialog."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        heading: str,
        intro: str,
        sections: Iterable[DialogSection],
        primary_label: str,
        secondary_label: str = "Abbrechen",
        warning: str = "",
        remember_label: str = "",
        width: int = 760,
        height: int = 640,
        modal: bool = True,
    ) -> None:
        super().__init__(parent)
        self.approved = False
        self.remember = _BoolChoice()
        self.setWindowTitle(title)
        self.resize(width, height)
        self.setMinimumSize(min(620, width), min(480, height))
        self.setModal(modal)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        heading_label = QLabel(heading)
        heading_label.setObjectName("dialogTitle")
        heading_label.setWordWrap(True)
        intro_label = QLabel(intro)
        intro_label.setObjectName("subtitle")
        intro_label.setWordWrap(True)
        outer.addWidget(heading_label)
        outer.addWidget(intro_label)

        if warning:
            warning_box = QFrame()
            warning_box.setObjectName("warningCard")
            warning_layout = QVBoxLayout(warning_box)
            warning_title = QLabel("⚠ Wichtiger Hinweis")
            warning_title.setObjectName("warning")
            warning_body = QLabel(warning)
            warning_body.setWordWrap(True)
            warning_body.setObjectName("subtitle")
            warning_layout.addWidget(warning_title)
            warning_layout.addWidget(warning_body)
            outer.addWidget(warning_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        for section in sections:
            content_layout.addWidget(_section_card(section))
        content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        if remember_label:
            remember = QCheckBox(remember_label)
            self.remember.bind(remember)
            outer.addWidget(remember)

        buttons = QHBoxLayout()
        buttons.addStretch()
        secondary = QPushButton(secondary_label)
        primary = QPushButton(primary_label)
        primary.setObjectName("primary")
        secondary.clicked.connect(self.reject)
        primary.clicked.connect(self._approve)
        buttons.addWidget(secondary)
        buttons.addWidget(primary)
        outer.addLayout(buttons)

    def _approve(self) -> None:
        self.approved = True
        self.accept()

    def wait(self) -> bool:
        if not self.isVisible():
            self.exec()
        return bool(self.approved)


def plugin_permission_dialog(
    parent: QWidget | None,
    summary_text: str,
    approval_status: str,
    *,
    modal: bool = True,
) -> GuidedDecisionDialog:
    status_text = {
        "active": "Eine unveränderte, gültige Freigabe ist gespeichert.",
        "expired": "Die bisherige Freigabe ist wegen einer Plugin- oder Berechtigungsänderung abgelaufen.",
        "revoked": "Die frühere Freigabe wurde widerrufen.",
        "missing": "Für dieses Plugin wurde noch keine Freigabe gespeichert.",
    }.get(approval_status, "Freigabestatus ist unbekannt.")
    return GuidedDecisionDialog(
        parent,
        title="Plugin-Berechtigungen und Freigabe",
        heading="Plugin sicher prüfen und freigeben",
        intro=status_text,
        sections=(
            DialogSection("Berechtigungsübersicht", summary_text),
            DialogSection(
                "Freigabebindung",
                "Die Freigabe wird an Version, signierten Inhalts-Hash, Signaturschlüssel und Berechtigungsprofil gebunden.",
            ),
            DialogSection(
                "Automatischer Widerruf",
                "Sobald sich Plugin-Dateien, Version, Schlüssel, Capability oder Berechtigungen ändern, verfällt die Freigabe automatisch.",
            ),
        ),
        warning="Nur freigeben, wenn Herausgeber, Zweck, Datenzugriff und Aktionen vollständig verständlich sind.",
        primary_label="Sandbox-Test erlauben und freigeben",
        secondary_label="Plugin inaktiv lassen",
        width=840,
        height=720,
        modal=modal,
    )


def update_assistant_dialog(
    parent: QWidget | None,
    version: str,
    file_count: int,
    *,
    modal: bool = True,
) -> GuidedDecisionDialog:
    return GuidedDecisionDialog(
        parent,
        title="Geführtes Update",
        heading=f"Update {version} sicher vorbereiten",
        intro="VideoBatch aktiviert das Update erst, wenn Paket, Kandidat und vollständiger Selbsttest erfolgreich sind.",
        sections=(
            DialogSection(
                "Paketprüfung",
                f"{file_count} deklarierte Datei(en) werden auf sichere Pfade, Hashwerte und Kompatibilität geprüft.",
            ),
            DialogSection(
                "Kandidatenprüfung",
                "Eine vollständige Kandidatenkopie wird erzeugt. Die laufende Installation bleibt unverändert aktiv.",
            ),
            DialogSection(
                "Rückrollschutz",
                "Vor der Aktivierung bleibt eine Sicherung der aktuellen Installation erhalten.",
            ),
        ),
        warning="Die Anwendung muss nach erfolgreicher Installation neu gestartet werden.",
        primary_label="Update-Kandidat erstellen und testen",
        secondary_label="Später aktualisieren",
        width=780,
        height=620,
        modal=modal,
    )


def archive_preview_dialog(
    parent: QWidget | None,
    file_count: int,
    project_dir: str,
    suffix: str,
    *,
    modal: bool = True,
) -> GuidedDecisionDialog:
    return GuidedDecisionDialog(
        parent,
        title="Verwendete Dateien sicher ablegen",
        heading="Dateiablage vor dem Verschieben prüfen",
        intro=f"{file_count} erfolgreich verwendete Quelldatei(en) sind für die sichere Ablage vorgesehen.",
        sections=(
            DialogSection("Ziel", project_dir or "Kein Projektordner ausgewählt"),
            DialogSection("Namenszusatz", suffix),
            DialogSection(
                "Sicherheitsablauf",
                "Kopieren oder atomisch verschieben → Größe und SHA-256 prüfen → Original erst danach entfernen → Manifest aktualisieren.",
            ),
        ),
        warning=(
            "Ein Ablagefehler verändert nicht den Erfolg der bereits erstellten Videos. "
            "Originale bleiben bei jeder ungeklärten Abweichung erhalten."
        ),
        primary_label="Dateien geprüft ablegen",
        secondary_label="Später aufräumen",
        width=760,
        height=600,
        modal=modal,
    )


def recovery_dialog(
    parent: QWidget | None,
    error_code: str,
    *,
    modal: bool = True,
) -> GuidedDecisionDialog:
    return GuidedDecisionDialog(
        parent,
        title="Recovery und sichere Wiederaufnahme",
        heading="VideoBatch hat einen wiederherstellbaren Zustand erkannt",
        intro=f"Fehlercode: {error_code}",
        sections=(
            DialogSection(
                "Was bleibt geschützt?",
                "Originaldateien und bereits bestätigte Ausgaben werden nicht überschrieben.",
            ),
            DialogSection(
                "Sichere Recovery",
                "Letzten geprüften Zustand laden, temporäre Reste isolieren und nur den unvollständigen Schritt wiederholen.",
            ),
            DialogSection(
                "Nachprüfung",
                "Die wiederaufgenommene Ausgabe wird erneut technisch validiert, bevor sie als erfolgreich gilt.",
            ),
        ),
        warning=(
            "Recovery wird höchstens einmal automatisch versucht. "
            "Danach ist eine bewusste Entscheidung erforderlich."
        ),
        primary_label="Sichere Wiederaufnahme starten",
        secondary_label="Vorgang beendet lassen",
        width=780,
        height=610,
        modal=modal,
    )


class PluginPermissionDecisionDialog(QDialog):
    """Qt permission decision with approve/revoke/cancel parity."""

    def __init__(
        self,
        parent: QWidget | None,
        summary_text: str,
        approval_status: str,
        *,
        modal: bool = True,
    ) -> None:
        super().__init__(parent)
        self.decision = "cancel"
        self.setWindowTitle("Plugin-Berechtigungen und Freigabe")
        self.resize(860, 740)
        self.setMinimumSize(700, 580)
        self.setModal(modal)

        status_text = {
            "active": "Eine unveränderte, gültige Freigabe ist gespeichert.",
            "expired": "Die bisherige Freigabe ist nach einer Änderung automatisch abgelaufen.",
            "revoked": "Die frühere Freigabe wurde widerrufen.",
            "missing": "Für dieses Plugin wurde noch keine Freigabe gespeichert.",
        }.get(approval_status, "Freigabestatus ist unbekannt.")

        outer = QVBoxLayout(self)
        heading = QLabel("Plugin sicher prüfen und freigeben")
        heading.setObjectName("dialogTitle")
        outer.addWidget(heading)

        status = QLabel(status_text)
        status.setWordWrap(True)
        status.setObjectName("subtitle")
        outer.addWidget(status)

        viewer = QPlainTextEdit(summary_text)
        viewer.setReadOnly(True)
        outer.addWidget(viewer, 1)

        for section in (
            DialogSection(
                "Freigabebindung",
                "Version, signierter Inhalts-Hash, Signaturschlüssel, Capability und Berechtigungsprofil werden gemeinsam registriert.",
            ),
            DialogSection(
                "Automatischer Ablauf",
                "Ändert sich nur einer dieser Werte, verfällt die Freigabe automatisch und das Plugin bleibt bis zur erneuten Prüfung inaktiv.",
            ),
        ):
            outer.addWidget(_section_card(section))

        warning = QLabel("⚠ Nur freigeben, wenn alle Zugriffe und Aktionen verständlich sind.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        outer.addWidget(warning)

        buttons = QHBoxLayout()
        if approval_status == "active":
            revoke = QPushButton("Freigabe widerrufen")
            revoke.setObjectName("danger")
            revoke.clicked.connect(lambda: self._finish("revoke"))
            buttons.addWidget(revoke)
        buttons.addStretch()
        close = QPushButton("Schließen")
        approve = QPushButton("Sandbox-Test erlauben und freigeben")
        approve.setObjectName("primary")
        close.clicked.connect(lambda: self._finish("cancel"))
        approve.clicked.connect(lambda: self._finish("approve"))
        buttons.addWidget(close)
        buttons.addWidget(approve)
        outer.addLayout(buttons)

    def _finish(self, decision: str) -> None:
        self.decision = decision
        self.accept() if decision != "cancel" else self.reject()

    def wait(self) -> str:
        if not self.isVisible():
            self.exec()
        return self.decision


class VisualApprovalSignDialog(QDialog):
    """Qt replacement for manual visual desktop approval signing."""

    def __init__(
        self,
        parent: QWidget | None,
        build_id: str,
        *,
        default_reviewer: str = "",
        modal: bool = True,
    ) -> None:
        super().__init__(parent)
        self.reviewer = ""
        self.setWindowTitle("Manuelle visuelle Desktop-Freigabe")
        self.resize(760, 540)
        self.setMinimumSize(660, 480)
        self.setModal(modal)

        outer = QVBoxLayout(self)
        heading = QLabel("Visuelle Desktopprüfung signieren")
        heading.setObjectName("dialogTitle")
        outer.addWidget(heading)

        intro = QLabel(
            "Die Abnahme wird an Build, Prüfmanifest und Referenzzustand gebunden. "
            "Signiere nur einen real geprüften Desktop-Zustand."
        )
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        outer.addWidget(
            _section_card(
                DialogSection(
                    f"Build-ID: {build_id}",
                    "Voraussetzung: visuelle Szenarien bestanden, keine offenen Vertragsfehler und unveränderte Prüfdaten.",
                )
            )
        )

        outer.addWidget(QLabel("Prüfername oder Kürzel"))
        self.reviewer_edit = QLineEdit(default_reviewer)
        self.reviewer_edit.setPlaceholderText("Name oder eindeutiges Kürzel")
        outer.addWidget(self.reviewer_edit)

        warning = QLabel(
            "⚠ Mit der Signatur bestätigst du die reale Desktopprüfung. "
            "Der private Signaturschlüssel bleibt außerhalb des Repositorys."
        )
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        outer.addWidget(warning)
        outer.addStretch()

        buttons = QDialogButtonBox()
        cancel = buttons.addButton("Abbrechen", QDialogButtonBox.ButtonRole.RejectRole)
        approve = buttons.addButton("Prüfung signieren", QDialogButtonBox.ButtonRole.AcceptRole)
        approve.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        approve.clicked.connect(self._approve)
        outer.addWidget(buttons)

        self.reviewer_edit.returnPressed.connect(self._approve)

    def _approve(self) -> None:
        value = self.reviewer_edit.text().strip()
        if not value:
            QMessageBox.warning(self, "Prüfername fehlt", "Trage einen Namen oder ein eindeutiges Kürzel ein.")
            return
        self.reviewer = value
        self.accept()

    def wait(self) -> str:
        if not self.isVisible():
            self.exec()
        return self.reviewer
