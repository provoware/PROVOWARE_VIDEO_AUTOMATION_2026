#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, zipfile
from pathlib import Path
from videobatch_fast.artifact_signing import canonical_json, load_private_key, public_key_id

p=argparse.ArgumentParser(description='Baut ein offiziell signiertes VideoBatch-Update.')
p.add_argument('--manifest',type=Path,required=True); p.add_argument('--payload-root',type=Path,required=True)
p.add_argument('--private-key',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
manifest=json.loads(a.manifest.read_text(encoding='utf-8')); manifest['official']=True
manifest_bytes=(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
key=load_private_key(a.private_key)
payload={'schema_version':1,'algorithm':'ed25519','role':'update-manifest','sha256':hashlib.sha256(manifest_bytes).hexdigest(),'key_id':public_key_id(key.public_key())}
sig={'payload':payload,'signature_base64':base64.b64encode(key.sign(canonical_json(payload))).decode('ascii')}
a.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    z.writestr('update_manifest.json',manifest_bytes)
    z.writestr('update_signature.json',json.dumps(sig,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    for item in manifest.get('files',[]):
        if item.get('operation')!='delete': z.write(a.payload_root/item['path'],item['path'])
print(a.output)
