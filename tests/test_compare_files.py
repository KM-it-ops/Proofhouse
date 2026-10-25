"""Compare pre-collected outputs from files: no models, no spend."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

import proofhouse
from proofhouse import cli, compare


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_two_entries_build_side_by_side_page_and_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "answer from cursor")
    _write(b, "answer from codex")
    out = tmp_path / "cmp"
    code = cli.main(
        [
            "compare",
            "Summarise the refund policy.",
            "--entry",
            f"cursor:composer-2.5={a}",
            "--entry",
            f"codex={b}",
            "--score",
            "cursor:composer-2.5=8",
            "--score",
            "codex=9",
            "--note",
            "cursor:composer-2.5=clear but long",
            "--note",
            "codex=shorter",
            "--out",
            str(out),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert "cursor:composer-2.5" in captured.out and "codex" in captured.out
    assert "side-by-side.html" in captured.out
    assert "best on this job: codex" in captured.out

    record = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    assert record["mode"] == "files"
    assert record["job"] == "Summarise the refund policy."
    assert record["proofhouse_version"] == proofhouse.__version__
    assert record["best"] == "codex"
    by_label = {e["label"]: e for e in record["entries"]}
    assert by_label["codex"]["score"] == 9 and by_label["codex"]["note"] == "shorter"
    assert by_label["cursor:composer-2.5"]["bytes"] == len("answer from cursor".encode())
    assert by_label["cursor:composer-2.5"]["sha256"] == hashlib.sha256(b"answer from cursor").hexdigest()

    page = (out / "side-by-side.html").read_text(encoding="utf-8")
    assert "answer from codex" in page and "9/10" in page
    assert "did not call any model" in page.lower() or "no model" in page.lower()
    assert "<script>" not in page
    assert len(list((out / "outputs").iterdir())) == 2


def test_tied_top_scores_mean_no_best(tmp_path: Path) -> None:
    paths = [tmp_path / f"{n}.md" for n in ("x", "y")]
    for p in paths:
        _write(p, "same")
    made = compare.compare_from_files(
        "job",
        [("a", paths[0]), ("b", paths[1])],
        scores={"a": 7, "b": 7},
        out_dir=tmp_path / "c",
    )
    assert made.best is None
    record = json.loads((tmp_path / "c" / "compare.json").read_text(encoding="utf-8"))
    assert record["best"] is None


def test_one_score_only_means_no_best(tmp_path: Path) -> None:
    p1, p2 = tmp_path / "1.md", tmp_path / "2.md"
    _write(p1, "one")
    _write(p2, "two")
    made = compare.compare_from_files("job", [("a", p1), ("b", p2)], scores={"a": 10}, out_dir=tmp_path / "c")
    assert made.best is None


def test_html_escapes_untrusted_output(tmp_path: Path) -> None:
    evil = tmp_path / "e.md"
    _write(evil, '<script>alert(1)</script>')
    good = tmp_path / "g.md"
    _write(good, "ok")
    compare.compare_from_files("job", [("x", evil), ("y", good)], out_dir=tmp_path / "c")
    page = (tmp_path / "c" / "side-by-side.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in page
    assert "<script>alert" not in page


def test_json_flag_on_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "a")
    _write(b, "b")
    out = tmp_path / "out"
    assert (
        cli.main(
            [
                "compare",
                "job",
                "--entry",
                f"L1={a}",
                "--entry",
                f"L2={b}",
                "--out",
                str(out),
                "--json",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "files" and data["best"] is None
    assert len(data["entries"]) == 2


@pytest.mark.parametrize(
    "argv,needle",
    [
        (["compare", "job"], "need"),
        (["compare", "job", "--on", "ollama:m", "--entry", "a={b}"], "mutually"),
        (["compare", "job", "--entry", "only={a}"], "at least"),
        (["compare", "job", "--entry", "a=missing.md", "--entry", "b=also-missing.md"], "not found"),
        (["compare", "job", "--entry", "a={a}", "--entry", "a={b}"], "duplicate"),
        (["compare", "job", "--entry", "={x}", "--entry", "b={b}"], "label"),
        (["compare", "job", "--entry", "a=", "--entry", "b={b}"], "label"),
        (["compare", "job", "--score", "nope=5", "--entry", "a={a}", "--entry", "b={b}"], "unknown"),
    ],
)
def test_usage_errors_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str], argv: list[str], needle: str) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    x = tmp_path / "x.md"
    _write(a, "a")
    _write(b, "b")
    _write(x, "x")
    formatted = [part.format(a=a, b=b, x=x) for part in argv]
    code = cli.main(formatted)
    err = capsys.readouterr().err.strip()
    assert code == 2
    assert err.startswith("error:")
    assert needle.lower() in err.lower()


def test_empty_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "ok")
    b.write_bytes(b"")
    assert cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"b={b}", "--out", str(tmp_path / "o")]) == 2
    assert "empty" in capsys.readouterr().err.lower()


def test_non_utf8_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "ok")
    b.write_bytes(b"\xff\xfe")
    assert cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"b={b}", "--out", str(tmp_path / "o")]) == 2
    assert "utf" in capsys.readouterr().err.lower()


def test_file_over_one_megabyte_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "ok")
    b.write_bytes(b"x" * (1_000_000 + 1))
    assert cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"b={b}", "--out", str(tmp_path / "o")]) == 2
    err = capsys.readouterr().err.lower()
    assert "1 mb" in err


def test_symlink_entry_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "link.md"
    _write(a, "ok")
    try:
        b.symlink_to(a)
    except OSError:
        pytest.skip("symlinks not supported")
    assert cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"link={b}", "--out", str(tmp_path / "o")]) == 2
    assert "symlink" in capsys.readouterr().err.lower() or "link" in capsys.readouterr().err.lower()


def test_score_out_of_range_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "a")
    _write(b, "b")
    assert cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"b={b}", "--score", "a=11", "--out", str(tmp_path / "o")]) == 2


def test_out_must_be_new_or_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "a")
    _write(b, "b")
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "leftover.txt").write_text("x", encoding="utf-8")
    assert cli.main(["compare", "job", "--entry", f"a={a}", "--entry", f"b={b}", "--out", str(blocked)]) == 2


def test_files_mode_does_not_load_providers(tmp_path: Path) -> None:
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    _write(a, "a")
    _write(b, "b")
    mods = set(sys.modules)
    compare.compare_from_files("job", [("a", a), ("b", b)], out_dir=tmp_path / "fresh")
    assert "proofhouse.providers" not in set(sys.modules) - mods
