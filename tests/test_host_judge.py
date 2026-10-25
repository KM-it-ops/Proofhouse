"""Independent judge on host record and compare file mode."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from proofhouse import cli, host

def _site_blurb() -> str:
    return " ".join(f"fresh loaf {i}" for i in range(1, 28)) + " Baked at 5 AM daily."


SITE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Corner Bakery</title></head>'
    f'<body><h1>Corner Bakery</h1><p>{_site_blurb()}</p><a href="menu.html">Menu</a></body></html>'
)
MENU = SITE.replace("Corner Bakery</title>", "Menu</title>").replace('<a href="menu.html">Menu</a>', "<p>Bread</p>")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("host judge tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(Path("no-such-browser")))
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def site(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(SITE, encoding="utf-8")
    (folder / "menu.html").write_text(MENU, encoding="utf-8")
    return folder


def record(tmp_path: Path, source: Path, *extra: str, agent: str = "cursor") -> int:
    return cli.main(
        [
            "record",
            "site",
            str(source),
            "--out",
            str(tmp_path / "out"),
            "--request",
            "bakery",
            "--agent",
            agent,
            *extra,
        ]
    )


def saved(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "out" / "record.json").read_text(encoding="utf-8"))


def test_judge_and_judge_score_must_come_together(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = site(tmp_path / "s")
    assert record(tmp_path, s, "--score", "7", "--judge", "codex") == 2
    assert "judge" in capsys.readouterr().err.lower()
    assert record(tmp_path, s, "--score", "7", "--judge-score", "8") == 2
    assert "judge" in capsys.readouterr().err.lower()


def test_judge_must_differ_from_agent_case_insensitive_and_model_suffix(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    s = site(tmp_path / "s")
    for agent, judge in (
        ("cursor", "cursor"),
        ("cursor", "CURSOR"),
        ("cursor:composer", "cursor"),
        ("cursor", "cursor:composer-2.5"),
    ):
        code = record(tmp_path, s, "--score", "7", "--judge", judge, "--judge-score", "8", agent=agent)
        assert code == 2
        err = capsys.readouterr().err.lower()
        assert "judge" in err and "agent" in err


def test_round_stores_judge_fields_and_omits_when_absent(tmp_path: Path) -> None:
    assert record(tmp_path, site(tmp_path / "s1"), "--score", "6") == 0
    r0 = saved(tmp_path)["rounds"][0]
    assert "judge" not in r0 and "judge_score" not in r0 and "judge_note" not in r0

    assert (
        record(
            tmp_path,
            site(tmp_path / "s2"),
            "--score",
            "5",
            "--judge",
            "codex",
            "--judge-score",
            "8",
            "--judge-note",
            "Clear layout.",
        )
        == 0
    )
    r1 = saved(tmp_path)["rounds"][1]
    assert r1["judge"] == "codex" and r1["judge_score"] == 8 and r1["judge_note"] == "Clear layout."


def test_best_passing_version_prefers_judge_score_over_self_score(tmp_path: Path) -> None:
    assert record(tmp_path, site(tmp_path / "s1"), "--score", "9") == 0
    assert record(tmp_path, site(tmp_path / "s2"), "--score", "6", "--judge", "codex", "--judge-score", "7") == 0
    assert record(tmp_path, site(tmp_path / "s3"), "--score", "8", "--judge", "codex", "--judge-score", "9") == 0
    data = saved(tmp_path)
    assert data["best_version"] == 3


def test_judged_round_beats_higher_self_score_without_judge(tmp_path: Path) -> None:
    assert record(tmp_path, site(tmp_path / "s1"), "--score", "10") == 0
    assert record(tmp_path, site(tmp_path / "s2"), "--score", "3", "--judge", "codex", "--judge-score", "5") == 0
    data = saved(tmp_path)
    assert data["best_version"] == 2


def test_record_json_judge_note_and_top_level_when_best_has_judge(tmp_path: Path) -> None:
    assert record(tmp_path, site(tmp_path / "s"), "--score", "6", "--judge", "codex", "--judge-score", "8") == 0
    data = saved(tmp_path)
    assert data["judge"] == "codex" and data["judge_score"] == 8
    assert "codex" in data["judge_note"] and "cursor" in data["judge_note"] and "advice" in data["judge_note"]
    assert data["judge_note"] != host.JUDGE_NOTE


def test_record_json_self_judge_note_when_no_judge_on_best(tmp_path: Path) -> None:
    assert record(tmp_path, site(tmp_path / "s"), "--score", "7") == 0
    data = saved(tmp_path)
    assert data["judge_note"] == host.JUDGE_NOTE
    assert "judge" not in data or data.get("judge") is None


def test_compare_files_with_judge_shows_scores_by_name(tmp_path: Path) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    out = tmp_path / "cmp"
    assert (
        cli.main(
            [
                "compare",
                "job",
                "--entry",
                f"cursor={a}",
                "--entry",
                f"codex={b}",
                "--score",
                "cursor=6",
                "--score",
                "codex=9",
                "--judge",
                "grok",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    record = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    assert record.get("judge") == "grok"
    assert "Scores by grok" in record.get("note", "")
    page = (out / "side-by-side.html").read_text(encoding="utf-8")
    assert "Scores by grok" in page


def test_compare_files_self_scores_line_only_when_scored_without_judge(tmp_path: Path) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    out = tmp_path / "cmp"
    cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"b={b}", "--out", str(out)])
    record = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    assert "writers' own advice" not in record.get("note", "").lower()

    out2 = tmp_path / "cmp2"
    cli.main(
        [
            "compare",
            "job",
            "--entry",
            f"a={a}",
            "--entry",
            f"b={b}",
            "--score",
            "a=5",
            "--out",
            str(out2),
        ]
    )
    record2 = json.loads((out2 / "compare.json").read_text(encoding="utf-8"))
    assert "writers' own advice" in record2.get("note", "").lower()


def test_compare_files_refuses_judge_same_as_entry_label(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    code = cli.main(
        [
            "compare",
            "job",
            "--entry",
            f"cursor:composer={a}",
            "--entry",
            f"codex={b}",
            "--judge",
            "cursor",
            "--out",
            str(tmp_path / "o"),
        ]
    )
    assert code == 2
    assert "judge" in capsys.readouterr().err.lower()
