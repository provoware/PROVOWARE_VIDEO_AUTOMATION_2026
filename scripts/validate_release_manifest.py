#!/usr/bin/env python3
from __future__ import annotations

from build_release_manifest import main as build_release_manifest_main
from release_file_contract import selected_release_files

# Der explizite Import ist Teil des Repository-Architekturvertrags: Builder und
# Validator müssen sichtbar an denselben Dateiauswahlvertrag gebunden bleiben.
# Die eigentliche Prüfung wird weiterhin ausschließlich zentral im Builder
# ausgeführt, damit keine zweite Manifestlogik entsteht.
_FILE_SELECTION_CONTRACT = selected_release_files


def main() -> int:
    """Prüft das Release-Manifest über den kanonischen Manifest-Builder.

    Dadurch gelten für kompaktes und vollständiges Manifest exakt dieselben
    Dateiauswahl-, Hash- und Metadatenregeln wie beim Erzeugen des Manifests.
    """
    return build_release_manifest_main(["--check"])


if __name__ == "__main__":
    raise SystemExit(main())
