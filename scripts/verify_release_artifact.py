#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from videobatch_fast.artifact_signing import verify_file
p=argparse.ArgumentParser(); p.add_argument('file',type=Path); p.add_argument('--signature',type=Path); p.add_argument('--public-key',type=Path,required=True); a=p.parse_args()
sig=a.signature or a.file.with_name(a.file.name+'.sig.json'); r=verify_file(a.file,sig,a.public_key)
print(('SIGNATURE_OK' if r.valid else 'SIGNATURE_FAILED')+': '+r.message); raise SystemExit(0 if r.valid else 1)
