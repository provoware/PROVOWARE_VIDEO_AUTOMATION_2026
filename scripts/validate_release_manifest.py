#!/usr/bin/env python3
from __future__ import annotations

from build_release_manifest import main as build_release_manifest_main


def main() -> int:
    """Prüft das Release-Manifest über den kanonischen Manifest-Builder.

    Dadurch gelten für kompaktes und vollständiges Manifest exakt dieselben
    Dateiauswahl-, Hash- und Metadatenregeln wie beim Erzeugen des Manifests.
    """
    return build_release_manifest_main(["--check"])


if __name__ == "__main__":
    raise SystemExit(main())
