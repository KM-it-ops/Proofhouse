#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
p=Path(sys.argv[1])
h=hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
print(h.hexdigest())
