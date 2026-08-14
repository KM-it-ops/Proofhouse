from pathlib import Path


def test_m1_schedule_authorized_not_ui() -> None:
    text = Path("architecture/mission-011-certification/PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md").read_text(encoding="utf-8")
    assert "MUST NOT be the first or only semantic implementation" in text
    assert "plain_language_v0" in text
    assert "MISSION-013" in text
    assert "Simple Mode UI" in text or "M3" in text
    grammar = Path("architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md")
    assert grammar.is_file()
    g = grammar.read_text(encoding="utf-8")
    assert "Goal:" in g and "Requirements:" in g
    assert "no model" in g.lower() or "deterministic" in g.lower()
