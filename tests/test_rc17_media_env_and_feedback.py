from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_no_global_foreign_ld_library_path():
    source=(ROOT/'scripts/build_portable_bundle.py').read_text(encoding='utf-8')
    assert 'export LD_LIBRARY_PATH=' not in source
    assert 'env -u LD_LIBRARY_PATH PYTHONHOME=' in source
    assert 'run_media \\\"$APPDIR/usr/media/bin/ffmpeg\\\"' in source

def test_compact_feedback_contract():
    source=(ROOT/'scripts/ab_installer.py').read_text(encoding='utf-8')
    assert '--feedback-mode' in source
    assert 'INSTALLATION GESTOPPT' in source
    assert 'Der bestätigte aktive Slot blieb unverändert' in source
