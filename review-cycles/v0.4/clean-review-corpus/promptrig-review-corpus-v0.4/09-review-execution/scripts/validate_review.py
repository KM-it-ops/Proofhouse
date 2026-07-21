#!/usr/bin/env python3
"""Validate PromptRig review findings and run manifest with jsonschema."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
try:
    import jsonschema
except ImportError:
    print("Install dependency: python -m pip install jsonschema", file=sys.stderr)
    raise SystemExit(2)

def load(path: Path):
    with path.open(encoding="utf-8") as f: return json.load(f)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("findings", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args=ap.parse_args()
    schema=load(args.root/'03-architecture/REVIEW_FINDING_SCHEMA.json')
    findings=load(args.findings)
    if not isinstance(findings,list):
        print("FINDINGS must be a JSON array",file=sys.stderr); return 1
    errors=[]
    validator=jsonschema.Draft202012Validator(schema)
    ids=set()
    for i,item in enumerate(findings):
        for err in validator.iter_errors(item): errors.append(f"finding[{i}] {err.json_path}: {err.message}")
        fid=item.get('id') or item.get('finding_id')
        if fid in ids: errors.append(f"duplicate finding ID: {fid}")
        ids.add(fid)
    manifest=load(args.manifest)
    required=['review_id','reviewer_id','corpus','execution','outputs','reviewer_declaration']
    for k in required:
        if k not in manifest: errors.append(f"manifest missing: {k}")
    if errors:
        print("INVALID REVIEW")
        for e in errors: print(f"- {e}")
        return 1
    print(f"VALID REVIEW: {len(findings)} findings")
    return 0
if __name__=='__main__': raise SystemExit(main())
