from pathlib import Path


def test_mission_015_residual_not_full_4b_not_m3() -> None:
    note = Path("architecture/mission-015-certification/README.md")
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    lower = text.lower()
    assert "clean-install" in lower or "clean install" in lower
    assert "consumer matrix" in lower
    assert "resource" in lower
    assert "not full" in lower
    assert "phase 4b" in lower
    assert "m3" in lower or "simple mode" in lower
    assert "not a live" in lower or "no live" in lower
    assert "benchmark" in lower
    assert "partial" in lower
    assert "oar-009" in lower
