from pathlib import Path
import json

def test_installer_contract_has_fixed_root():
 root=Path(__file__).resolve().parents[1]; data=json.loads((root/'config/contracts/INSTALLER_SYSTEM_CONTRACT.json').read_text())
 assert data['default_install_root'].endswith('/VideoBatchFast'); assert 'rc14' not in data['default_install_root']
 assert data['maximum_part_bytes']==30*1024*1024; assert data['transaction']['automatic_rollback'] is True

def test_autoinstall_is_noninteractive_and_signed():
 root=Path(__file__).resolve().parents[1]; text=(root/'scripts/install/autoinstall.sh').read_text()
 assert '[j/N]' not in text and 'read -p' not in text; assert 'openssl pkeyutl -verify' in text
 assert 'rollback' in text and 'portable-smoke-test' in text


def test_multipart_builder_uses_migrated_installer_resources():
    root = Path(__file__).resolve().parents[1]
    builder = (root / "scripts/build_multipart_installer.py").read_text(encoding="utf-8")
    assert (root / "scripts/install/autoinstall.sh").is_file()
    assert (root / "docs/start/AUTOINSTALLATION_save_.md").is_file()
    assert 'source_root / "scripts/install" / name' in builder
    assert 'source_root / "docs/start/AUTOINSTALLATION_save_.md"' in builder
