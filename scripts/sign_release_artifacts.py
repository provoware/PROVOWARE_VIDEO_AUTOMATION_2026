#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from videobatch_fast.artifact_signing import sign_file
p=argparse.ArgumentParser(); p.add_argument('--private-key',type=Path,required=True); p.add_argument('files',nargs='+',type=Path); a=p.parse_args()
results=[]
for f in a.files:
    sig=sign_file(f,a.private_key,role='release-artifact')
    results.append({'file':str(f),'signature':str(sig)})
print(json.dumps(results,ensure_ascii=False,indent=2))
