#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from videobatch_fast.artifact_signing import create_keypair
p=argparse.ArgumentParser(); p.add_argument('--private',type=Path,required=True); p.add_argument('--public',type=Path,required=True); a=p.parse_args()
print('RELEASE_KEY_ID='+create_keypair(a.private,a.public))
