from pathlib import Path


def test_m2_schedule_authorized_not_live_not_ui() -> None:
    text = Path("architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md").read_text(
        encoding="utf-8"
    )
    assert "MUST NOT be the first or only semantic implementation" in text
    assert "MISSION-014" in text
    assert "fake-suggester-v0" in text
    assert "Simple Mode UI" in text or "M3" in text
    note = Path("architecture/mission-014-certification/FAKE_SUGGESTER.md")
    assert note.is_file()
    body = note.read_text(encoding="utf-8")
    assert "fake-suggester-v0" in body
    assert "not a live" in body.lower() or "no live" in body.lower()
    assert "proposed" in body.lower()
    assert "model_suggested" in body
