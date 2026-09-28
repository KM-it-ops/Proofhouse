"""The README may only say import refuses "any altered byte" if a re-hashed bundle is refused."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from proofhouse.compiler import cli_compiler

REPO = Path(__file__).resolve().parents[1]


def test_import_refuses_altered_bundle_as_readme_claims(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    work = tmp_path / "w"
    subprocess.run([sys.executable, str(REPO / "scripts" / "reference_workflow.py"), "--quiet", "--workspace", str(work)],
                   check=True, capture_output=True)
    with zipfile.ZipFile(work / "advisory-case.zip") as z:
        data = {n: z.read(n) for n in z.namelist()}
    old = data["checks/verdicts.json"]
    new = old.replace(b"claims active exploitation", b"claims ACTIVE exploitation")
    assert new != old
    data["checks/verdicts.json"] = new
    data["manifest.json"] = data["manifest.json"].replace(
        hashlib.sha256(old).hexdigest().encode(), hashlib.sha256(new).hexdigest().encode())
    bundle = tmp_path / "altered.zip"
    with zipfile.ZipFile(bundle, "w") as z:
        for name, blob in data.items():
            z.writestr(name, blob)
    code = cli_compiler.main(["optimize", "import", "--bundle", str(bundle), "--case", str(tmp_path / "imported")])
    capsys.readouterr()
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    if code == 0:
        assert "any altered byte" not in readme, (
            "import accepted a bundle with an edited file and a re-hashed manifest, "
            "but the README says import refuses any altered byte")
