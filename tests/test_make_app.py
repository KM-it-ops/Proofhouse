"""Offline end-to-end app rounds, platform data, and contained builds."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from proofhouse import cli, live, make


WEB = {"index.html": '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width"><title>App</title></head><body><h1>App</h1><script src="script.js"></script></body></html>',
       "script.js": "document.title = 'App';"}
PWA = {"index.html": WEB["index.html"].replace("</head>", '<link rel="manifest" href="manifest.webmanifest"></head>'),
       "script.js": "navigator.serviceWorker.register('service-worker.js');",
       "manifest.webmanifest": json.dumps({"name": "App", "start_url": ".", "display": "standalone", "icons": [{"src": "icon.svg", "sizes": "192x192"}]}),
       "service-worker.js": "self.addEventListener('fetch', () => {});",
       "icon.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192"></svg>'}


class Model:
    def __init__(self, files: list[dict[str, str]], scores: list[int] | None = None) -> None:
        self.files = list(files)
        self.scores = list(scores or [9] * len(files))
        self.prompts: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        prompt = " ".join(message["content"] for message in json.loads(request.body_bytes)["messages"])
        self.prompts.append(prompt)
        content = json.dumps({"score": self.scores.pop(0), "missing": [], "fix": "repair"}) if prompt.startswith("You judge AI work") else json.dumps({"files": self.files.pop(0)})
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


def run(tmp_path: Path, model: Model, platforms: list[str], **kwargs: object) -> make.MakeResult:
    return make.make("a useful app", provider_id="ollama", model="m", kind="app", platforms=platforms,
                     out_dir=tmp_path / "out", transport=model, **kwargs)


def checks(result: make.MakeResult, version: int = 1) -> list[dict[str, object]]:
    return json.loads((result.folder / f"v{version}" / "checks.json").read_text(encoding="utf-8"))


def test_pwa_passes_and_is_delivered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "missing-browser"))
    result = run(tmp_path, Model([WEB, PWA]), ["pwa"])
    assert all(c["ok"] is not False for c in checks(result))
    assert (result.folder / "pwa" / "manifest.webmanifest").is_file()
    assert "## Installable web app" in (result.folder / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("missing", ["manifest.webmanifest", "service-worker.js"])
def test_missing_pwa_file_reaches_next_round(tmp_path: Path, missing: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "missing-browser"))
    model = Model([WEB, {k: v for k, v in PWA.items() if k != missing}, WEB, PWA], [4, 9])
    result = run(tmp_path, model, ["pwa"], rounds=2)
    assert any(c["ok"] is False and missing in str(c["detail"]) for c in checks(result))
    assert any(missing in prompt and "CHECK FAILURES" in prompt for prompt in model.prompts)
    writes = [prompt for prompt in model.prompts if prompt.startswith("Build the ")]
    assert "FAILED LAST ROUND" not in writes[0]
    assert f"- pwa file {missing}:" in writes[1] and "YOUR FILES LAST ROUND" in writes[1]
    assert result.best_version == 2


def _custom(tmp_path: Path, platform_id: str, tool: str, hosts: list[str], command: list[str], hint: str) -> None:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    entry = {"id": platform_id, "name": "Custom", "shell": "Custom app shell", "write": "Write setup.json",
             "checks": {"files": ["setup.json"], "json": {"setup.json": ["name"]}},
             "build": {"tool": tool, "install": hint, "command": command, "output": "built.txt", "timeout": 10},
             "host_os": hosts}
    (home / "app_platforms.json").write_text(json.dumps({"schema": "proofhouse.app-platforms/v1", "platforms": [entry]}), encoding="utf-8")


def test_missing_tool_and_wrong_os_are_not_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _custom(tmp_path, "custom", "tool-that-does-not-exist", ["windows", "macos", "linux"], ["tool-that-does-not-exist"], "install custom")
    result = run(tmp_path, Model([WEB, {"setup.json": '{"name":"x"}'}]), ["custom"], allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is None and "not built: tool-that-does-not-exist not found (install: install custom)" == build["detail"]
    assert (result.folder / "custom" / "setup.json").is_file()
    other = "macos" if sys.platform != "darwin" else "windows"
    _custom(tmp_path, "custom", "python", [other], ["python", "build.py"], "install python")
    result = make.make("another app", provider_id="ollama", model="m", kind="app", platforms=["custom"],
                       out_dir=tmp_path / "other", transport=Model([WEB, {"setup.json": '{"name":"x"}'}]), allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is None and build["detail"] == f"not built: needs {other}"


def test_user_platform_build_runs_with_limited_environment_only_when_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("FAKE_SECRET_KEY", "do-not-pass")
    tools = tmp_path / "tools"
    tools.mkdir()
    tool = "fakebuild.cmd" if os.name == "nt" else "fakebuild"
    executable = tools / tool
    if os.name == "nt":
        executable.write_text(f'@echo off\r\n"{sys.executable}" %*\r\n', encoding="utf-8")
    else:
        executable.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tools) + os.pathsep + os.environ["PATH"])
    _custom(tmp_path, "custom", tool, ["windows", "macos", "linux"], [tool, "build.py"], "install fakebuild")
    script = "import os, pathlib\npathlib.Path('built.txt').write_text('leaked' if 'FAKE_SECRET_KEY' in os.environ else 'clean')\n"
    payload = {"setup.json": '{"name":"x"}', "build.py": script}
    result = run(tmp_path, Model([WEB, payload]), ["custom"], allow_commands=True)
    assert (result.folder / "v1" / "custom" / "built.txt").read_text(encoding="utf-8") == "clean"
    assert next(c for c in checks(result) if c["check"] == "custom build")["ok"] is True
    assert not (result.folder / "custom" / "built.txt").exists()
    assert (result.folder / "custom" / "build.py").is_file()
    assert "Built output: `v1/custom/built.txt`" in (result.folder / "README.md").read_text(encoding="utf-8")
    result = make.make("second app", provider_id="ollama", model="m", kind="app", platforms=["custom"],
                       out_dir=tmp_path / "not-allowed", transport=Model([WEB, payload]))
    assert not (result.folder / "v1" / "custom" / "built.txt").exists()
    assert next(c for c in checks(result) if c["check"] == "custom build")["ok"] is None


def test_unknown_platform_lists_known_ids(tmp_path: Path) -> None:
    with pytest.raises(make.MakeError, match="unknown platform: nowhere; known: .*pwa"):
        run(tmp_path, Model([]), ["nowhere"])


def test_cli_unknown_platform_lists_known_ids(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["make", "an app", "--kind", "app", "--platform", "nowhere", "--provider", "ollama",
                     "--model", "m", "--out", str(tmp_path / "out")])
    assert code != 0
    assert "unknown platform: nowhere" in capsys.readouterr().err


def _platform_file(tmp_path: Path, entry: dict[str, object]) -> None:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    (home / "app_platforms.json").write_text(json.dumps({"schema": "proofhouse.app-platforms/v1", "platforms": [entry]}), encoding="utf-8")


def _python_entry(build: dict[str, object], **extra: object) -> dict[str, object]:
    return {"id": "custom", "name": "Custom", "shell": "Custom app shell", "write": "Write setup.json",
            "checks": {"files": ["setup.json"], "json": {}},
            "build": {"tool": "python", "install": "install python", "output": "", "timeout": 30, **build},
            "host_os": ["windows", "macos", "linux"], **extra}


def test_setup_steps_run_in_order_and_a_failing_step_stops_the_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"before": [["python", "step.py", "one"], ["python", "step.py", "two"]],
                                            "command": ["python", "step.py", "build"], "output": "log.txt"}))
    step = "import pathlib, sys\nlog = pathlib.Path('log.txt')\nlog.write_text((log.read_text() if log.exists() else '') + sys.argv[1] + ' ')\n"
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "step.py": step}]), ["custom"], allow_commands=True)
    assert (result.folder / "v1" / "custom" / "log.txt").read_text(encoding="utf-8") == "one two build "
    assert next(c for c in checks(result) if c["check"] == "custom build")["ok"] is True
    failing = "import sys\nsys.exit(3 if sys.argv[1] == 'two' else 0)\n"
    result = make.make("another app", provider_id="ollama", model="m", kind="app", platforms=["custom"],
                       out_dir=tmp_path / "failing", transport=Model([WEB, {"setup.json": "{}", "step.py": failing}]),
                       allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is False and build["detail"] == "setup step `python step.py two` failed: exit code 3"


def test_missing_build_output_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"], "output": "dist/app.bin"}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n"}]), ["custom"], allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is False and build["detail"] == "build finished but dist/app.bin is missing"


def test_build_gets_named_tool_locations_but_not_other_variables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("FAKE_TOOL_DIR", "/opt/tool")
    monkeypatch.setenv("UNLISTED_DIR", "/opt/other")
    monkeypatch.delenv("FAKE_TOOL_HOME", raising=False)
    _platform_file(tmp_path, _python_entry({"command": ["python", "env.py"], "output": "env.json",
                                            "env": ["FAKE_TOOL_DIR"], "home_env": {"FAKE_TOOL_HOME": ".faketool"}}))
    script = ("import json, os\nopen('env.json', 'w').write(json.dumps({k: os.environ.get(k) for k in "
              "('FAKE_TOOL_DIR', 'UNLISTED_DIR', 'FAKE_TOOL_HOME')}))\n")
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "env.py": script}]), ["custom"], allow_commands=True)
    seen = json.loads((result.folder / "v1" / "custom" / "env.json").read_text(encoding="utf-8"))
    assert seen == {"FAKE_TOOL_DIR": "/opt/tool", "UNLISTED_DIR": None, "FAKE_TOOL_HOME": str(Path.home() / ".faketool")}


@pytest.mark.parametrize("field", ["env", "home_env"])
@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "GITHUB_TOKEN", "DB_PASSWORD", "MY_SECRET"])
def test_secret_looking_variables_cannot_be_passed_to_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, field: str) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "x.py"], field: [name] if field == "env" else {name: ".tool"}}))
    with pytest.raises(make.MakeError, match="invalid build data"):
        run(tmp_path, Model([]), ["custom"])


def test_web_dir_and_install_checks_come_from_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "missing-browser"))
    entry = _python_entry({"command": []}, web_dir="www")
    entry["id"] = "kiosk"
    entry["checks"] = {"files": ["www/index.html"], "json": {},
                       "web_install": {"manifest": "manifest.webmanifest", "service_worker": "service-worker.js"}}
    _platform_file(tmp_path, entry)
    model = Model([WEB, {f"www/{name}": text for name, text in PWA.items()}])
    result = run(tmp_path, model, ["kiosk"])
    found = {c["check"]: c["ok"] for c in checks(result)}
    assert found["kiosk file www/index.html"] is True
    assert found["kiosk manifest linked"] is True and found["kiosk service worker registered"] is True
    assert "copied into `www/`" in model.prompts[1]
    assert (result.folder / "kiosk" / "www" / "manifest.webmanifest").is_file()


def test_shipped_native_builds_are_flagged_and_set_up_first() -> None:
    from proofhouse import app_platforms

    shipped = {entry["id"]: entry for entry in app_platforms._read(app_platforms.SHIPPED)}
    assert {"pwa", "windows", "macos", "linux", "ios", "android"} <= set(shipped)
    for platform_id, entry in shipped.items():
        if entry["build"]["command"]:
            assert entry["build"]["to_check"], platform_id
            # Install scripts in a package.json the model wrote could fake the build output.
            assert entry["build"]["before"][0] == ["npm", "install", "--ignore-scripts"], platform_id
    for platform_id in ("ios", "android"):
        assert not any(name.startswith(platform_id + "/") for name in shipped[platform_id]["checks"]["files"])
        assert ["npx", "--no-install", "cap", "add", platform_id] in shipped[platform_id]["build"]["before"]
    for platform_id, entry in shipped.items():
        if entry["build"]["command"]:
            # npx must never download a package that npm install did not put in node_modules.
            steps = [*entry["build"]["before"], entry["build"]["command"]]
            assert all(step[:2] == ["npx", "--no-install"] for step in steps if step[0] == "npx"), platform_id
            assert entry["build"]["tool_package"] and entry["build"]["tool_bin"], platform_id


def test_install_checks_never_open_paths_outside_the_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import app_platforms

    folder = tmp_path / "app"
    folder.mkdir()
    share = "\\\\attacker.example\\s\\"
    (folder / "index.html").write_text(PWA["index.html"].replace('src="script.js"', f'src="{share}a.js"'), encoding="utf-8")
    (folder / "manifest.webmanifest").write_text(json.dumps({"name": "A", "icons": [{"src": share + "i.png"}, {"src": "../i.png"}]}),
                                                 encoding="utf-8")
    opened: list[str] = []
    for method in ("is_file", "resolve", "read_text"):
        original = getattr(Path, method)
        monkeypatch.setattr(Path, method, lambda self, *a, _o=original, **k: (opened.append(str(self)), _o(self, *a, **k))[1])
    entry = {"id": "pwa", "checks": {"files": [], "json": {},
                                     "web_install": {"manifest": "manifest.webmanifest", "service_worker": "service-worker.js"}}}
    found = {c["check"]: c["ok"] for c in app_platforms.static_checks(folder, entry)}
    assert found["pwa manifest icon"] is False and found["pwa service worker registered"] is False
    assert not any("attacker" in path or path.endswith("i.png") for path in opened)


@pytest.mark.parametrize("fake", ["DIST/app.bin", "dist/./app.bin", "dist//app.bin", "./dist/app.bin"])
def test_model_cannot_write_the_build_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake: str) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"], "output": "dist"}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", fake: "fake"}]), ["custom"],
                 allow_commands=True)
    written = next(c for c in checks(result) if c["check"] == "custom written")
    assert written["ok"] is False and "build output dist" in written["detail"]
    assert not any(c["check"] == "custom build" for c in checks(result))


def test_model_cannot_write_a_build_output_named_in_its_own_tauri_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """f939f95-F5: the output name comes from the model's tauri.conf.json, so the guard must read that name."""
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"], "output": "dist/{mainBinaryName}.bin"}))
    files = {"setup.json": "{}", "noop.py": "pass\n", "src-tauri/tauri.conf.json": json.dumps({"mainBinaryName": "fake"}),
             "dist/fake.bin": "fake"}
    written = _written(run(tmp_path, Model([WEB, files]), ["custom"]))
    assert written["ok"] is False and "build output" in str(written["detail"])


def test_cmd_files_refuse_characters_cmd_exe_would_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["./tool.cmd", "a&calc"]}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "tool.cmd": "@echo off\n"}]), ["custom"], allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is False and "cmd.exe" in build["detail"]


def test_a_build_that_runs_too_long_is_stopped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "slow.py"], "timeout": 2}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "slow.py": "import time\ntime.sleep(60)\n"}]), ["custom"],
                 allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is False and build["detail"] == "build `python slow.py` failed: timed out after 2 seconds"


def test_delivery_skips_links_bad_names_and_missing_files(tmp_path: Path) -> None:
    folder = tmp_path / "made"
    platform = folder / "v1" / "custom"
    platform.mkdir(parents=True)
    (platform / "a.txt").write_text("source", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    names = ["a.txt", "../secret.txt", "gone.txt"]
    try:
        (platform / "link.txt").symlink_to(tmp_path / "secret.txt")
        names.append("link.txt")
    except OSError:
        pass  # Windows without symlink rights: the name and path checks are still covered.
    (folder / "v1" / "checks.json").write_text("[]", encoding="utf-8")
    (folder / "v1" / "written.json").write_text(json.dumps({"custom": names}), encoding="utf-8")
    make._deliver_app(folder, 1, ["custom"], {"custom": _python_entry({"command": []})})
    delivered = sorted(p.relative_to(folder / "custom").as_posix() for p in (folder / "custom").rglob("*") if p.is_file())
    assert delivered == ["a.txt"]
    assert not (folder / "secret.txt").exists()


@pytest.mark.parametrize("field", ["env", "home_env", "set_env"])
@pytest.mark.parametrize("name", ["PATH", "HOME", "TEMP", "userprofile"])
def test_builds_cannot_move_their_own_home_temp_or_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, field: str) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    value = [name] if field == "env" else {name: ".tool"}
    _platform_file(tmp_path, _python_entry({"command": ["python", "x.py"], field: value}))
    with pytest.raises(make.MakeError, match="invalid build data"):
        run(tmp_path, Model([]), ["custom"])


def test_set_env_values_reach_the_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "env.py"], "output": "env.txt",
                                            "set_env": {"GRADLE_OPTS": "-Dorg.gradle.daemon=false"}}))
    script = "import os\nopen('env.txt', 'w').write(os.environ.get('GRADLE_OPTS', ''))\n"
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "env.py": script}]), ["custom"], allow_commands=True)
    assert (result.folder / "v1" / "custom" / "env.txt").read_text(encoding="utf-8") == "-Dorg.gradle.daemon=false"


def test_build_home_and_temp_variables_all_point_inside_the_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    for name in ("TMPDIR", "HOMEDRIVE", "HOMEPATH"):
        monkeypatch.setenv(name, "/real/machine")
    _platform_file(tmp_path, _python_entry({"command": ["python", "env.py"], "output": "env.json"}))
    names = ("HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR", "HOMEDRIVE", "HOMEPATH")
    script = f"import json, os\nopen('env.json', 'w').write(json.dumps({{k: os.environ.get(k) for k in {names!r}}}))\n"
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "env.py": script}]), ["custom"], allow_commands=True)
    seen = json.loads((result.folder / "v1" / "custom" / "env.json").read_text(encoding="utf-8"))
    assert "/real/machine" not in seen.values()
    if seen["HOMEDRIVE"] is not None:
        assert Path(seen["HOMEDRIVE"] + seen["HOMEPATH"]) == Path(seen["HOME"])


def test_a_setup_step_can_make_the_tool_a_later_step_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    tool = "tool.cmd" if os.name == "nt" else "tool"
    body = "@echo off\necho built> out.txt\n" if os.name == "nt" else "#!/bin/sh\necho built > out.txt\n"
    maker = f"import os\nopen({tool!r}, 'w', newline='').write({body!r})\nos.chmod({tool!r}, 0o755)\n"
    _platform_file(tmp_path, _python_entry({"before": [["python", "maker.py"]], "command": [f"./{tool}"], "output": "out.txt"}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "maker.py": maker}]), ["custom"], allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is True, build
    assert (result.folder / "v1" / "custom" / "out.txt").read_text(encoding="utf-8").strip() == "built"


def test_a_helper_left_running_does_not_hold_a_finished_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "build.py"], "timeout": 60}))
    script = "import subprocess, sys\nsubprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\nprint('done')\n"
    started = time.monotonic()
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "build.py": script}]), ["custom"], allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is True and "done" in build["output"]
    assert time.monotonic() - started < 30


def test_a_manifest_link_outside_the_folder_does_not_count(tmp_path: Path) -> None:
    from proofhouse import app_platforms

    folder = tmp_path / "app"
    folder.mkdir()
    for name, text in PWA.items():
        (folder / name).write_text(text, encoding="utf-8")
    (folder / "index.html").write_text(PWA["index.html"].replace('href="manifest.webmanifest"', 'href="../manifest.webmanifest"'),
                                       encoding="utf-8")
    entry = {"id": "pwa", "checks": {"files": [], "json": {},
                                     "web_install": {"manifest": "manifest.webmanifest", "service_worker": "service-worker.js"}}}
    found = {c["check"]: c["ok"] for c in app_platforms.static_checks(folder, entry)}
    assert found["pwa manifest linked"] is False and found["pwa manifest icon"] is True


def test_a_setup_step_cannot_fake_the_build_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    fake = "import pathlib\npathlib.Path('dist').mkdir()\npathlib.Path('dist/app.bin').write_text('fake')\n"
    _platform_file(tmp_path, _python_entry({"before": [["python", "fake.py"]], "command": ["python", "noop.py"],
                                            "output": "dist/app.bin"}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "fake.py": fake, "noop.py": "pass\n"}]), ["custom"],
                 allow_commands=True)
    build = next(c for c in checks(result) if c["check"] == "custom build")
    assert build["ok"] is False and "dist/app.bin" in str(build["detail"]), build


@pytest.mark.parametrize("name", ["src-tauri/.cargo/config.toml", "node_modules/.bin/tauri", "www/.npmrc"])
def test_model_cannot_write_into_dotted_folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", name: "x"}]), ["custom"])
    written = next(c for c in checks(result) if c["check"] == "custom written")
    assert written["ok"] is False and "unsafe file name" in str(written["detail"])


@pytest.mark.parametrize("spec", ["file:./fake", "link:../fake", "../fake", "git+https://example.com/cli.git",
                                  "github:someone/cli", "someone/cli", "https://example.com/cli.tgz", "npm:other-cli@2",
                                  "cli.tar", "x.tgz", "x.tar.gz", "X.TGZ", "x.tgz ", " x.tar ", "..", "1.0 || file:x", "~/cli", "1.0\\fake"])
def test_package_json_dependencies_must_come_from_the_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spec: str) -> None:
    # A local or aliased package can put a fake build tool in node_modules/.bin.
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}))
    package = json.dumps({"name": "app", "devDependencies": {"@tauri-apps/cli": spec}})
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", "package.json": package}]), ["custom"])
    written = next(c for c in checks(result) if c["check"] == "custom written")
    assert written["ok"] is False and "package.json" in str(written["detail"])


def test_registry_versions_in_package_json_are_fine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}))
    package = json.dumps({"name": "app", "devDependencies": {"@tauri-apps/cli": "^2.0.0", "vite": "5.4.1", "x": "latest", "a": "~1.2.3", "b": ">=1 <2", "c": "*", "d": "1.x", "e": "", "f": "^1 || ^2"}})
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", "package.json": package}]), ["custom"])
    assert not any(c["check"] == "custom written" for c in checks(result))


def _written(result: make.MakeResult) -> dict[str, object]:
    return next(c for c in checks(result) if c["check"] == "custom written")


def test_file_names_are_compared_without_regard_to_letter_case(tmp_path: Path) -> None:
    from proofhouse import app_platforms, make_checks

    fake = json.dumps({"devDependencies": {"@tauri-apps/cli": "file:./fake"}})
    for name in ("Package.json", "www/PACKAGE.JSON"):
        with pytest.raises(ValueError, match="registry"):
            app_platforms.check_packages({name: fake})
    for name in ("PACKAGE-LOCK.JSON", "Yarn.lock", "src/Pnpm-Lock.yaml"):
        with pytest.raises(ValueError, match="lockfile"):
            app_platforms.check_packages({name: "{}"})
    with pytest.raises(ValueError, match="letter case"):
        make_checks.write_files({"package.json": "{}", "Package.json": fake}, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("name", ["pnpm-workspace.yaml", "bun.lock", "bun.lockb", "bunfig.toml", "app/Bunfig.toml"])
def test_other_package_manager_files_are_refused(name: str) -> None:
    from proofhouse import app_platforms

    with pytest.raises(ValueError, match="may not write"):
        app_platforms.check_packages({name: "x"})


@pytest.mark.parametrize("pnpm", [{"overrides": {"cli": "file:./fake"}}, {"overrides": {"a": {"b": "link:../x"}}},
                                  {"patchedDependencies": {"cli@1.0.0": "patches/cli.patch"}}])
def test_pnpm_settings_in_package_json_are_checked(pnpm: dict[str, object]) -> None:
    from proofhouse import app_platforms

    with pytest.raises(ValueError, match="package.json"):
        app_platforms.check_packages({"package.json": json.dumps({"name": "app", "pnpm": pnpm})})
    app_platforms.check_packages({"package.json": json.dumps({"name": "app", "pnpm": {"overrides": {"cli": "^2.0.0"}}})})


def test_deeply_nested_package_json_is_refused_not_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import app_platforms

    deep = "[" * 200_000 + "]" * 200_000
    with pytest.raises(ValueError, match="nested too deeply"):
        app_platforms.check_packages({"package.json": deep})
    nested: object = "file:./fake"
    for _ in range(5000):
        nested = [nested]
    assert app_platforms._strings(nested) == ["file:./fake"]
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", "package.json": deep}]), ["custom"])
    assert _written(result)["ok"] is False


@pytest.mark.parametrize("name", ["www/.well-known/assetlinks.json", ".gitignore", "src/.gitignore", ".well-known/apple-app-site-association"])
def test_well_known_folder_and_gitignore_are_allowed(name: str) -> None:
    from proofhouse import make_checks

    assert make_checks.safe_name(name)


@pytest.mark.parametrize("name", [".gitignore/x", ".gitignore/.gitignore", ".well-known", "a/.well-known", ".env", "www/.npmrc",
                                  ".well-known/.env", "x/.git/config", ".gitignore."])
def test_other_dotted_parts_stay_refused(name: str) -> None:
    from proofhouse import make_checks

    assert not make_checks.safe_name(name)


def test_a_legitimate_project_with_well_known_and_gitignore_is_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}))
    files = {"setup.json": "{}", "noop.py": "pass\n", ".gitignore": "node_modules\n", "www/.well-known/assetlinks.json": "[]"}
    result = run(tmp_path, Model([WEB, files]), ["custom"])
    assert not any(c["check"] == "custom written" for c in checks(result))
    assert (result.folder / "v1" / "custom" / "www" / ".well-known" / "assetlinks.json").is_file()


@pytest.mark.parametrize("name", ["capacitor.config.js", "CAPACITOR.CONFIG.JS", "capacitor.config.ts", "sub/capacitor.config.js"])
def test_platform_data_can_refuse_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}, refuse_files=["capacitor.config.js", "Capacitor.Config.TS"]))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", name: "module.exports = {};"}]), ["custom"])
    written = _written(result)
    assert written["ok"] is False and "may not write" in str(written["detail"])


@pytest.mark.parametrize("name", ["src-tauri/tauri.conf.json", "SRC-TAURI/Tauri.Conf.json"])
@pytest.mark.parametrize("config", [{"build": {"runner": "evil"}}, {"build": {"beforeBuildCommand": "evil"}}])
def test_platform_data_can_refuse_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, config: dict[str, object]) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    keys = {"src-tauri/tauri.conf.json": ["build.runner", "build.beforeBuildCommand"]}
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}, refuse_keys=keys))
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", name: json.dumps(config)}]), ["custom"])
    written = _written(result)
    assert written["ok"] is False and "may not set" in str(written["detail"])


def test_a_config_without_the_refused_keys_is_fine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    keys = {"src-tauri/tauri.conf.json": ["build.runner"]}
    _platform_file(tmp_path, _python_entry({"command": ["python", "noop.py"]}, refuse_keys=keys))
    config = json.dumps({"build": {"frontendDist": "../www"}})
    result = run(tmp_path, Model([WEB, {"setup.json": "{}", "noop.py": "pass\n", "src-tauri/tauri.conf.json": config}]), ["custom"])
    assert not any(c["check"] == "custom written" for c in checks(result))


def test_shipped_tauri_and_capacitor_data_refuse_what_the_review_found() -> None:
    from proofhouse import app_platforms

    shipped = app_platforms.all_platforms()
    package = json.dumps({"devDependencies": {"@tauri-apps/cli": "2", "@capacitor/cli": "6"}})
    for platform_id in ("windows", "macos", "linux"):
        for name in ("src-tauri/tauri.windows.conf.json", "src-tauri/tauri.macos.conf.json", "src-tauri/tauri.linux.conf.json",
                     "src-tauri/tauri.android.conf.json", "src-tauri/tauri.ios.conf.json", "src-tauri/tauri.conf.json5", "src-tauri/Tauri.toml"):
            with pytest.raises(ValueError, match="may not write"):
                app_platforms.check_platform({name: "x", "package.json": package}, shipped[platform_id])
        for key in ("runner", "beforeBuildCommand", "beforeBundleCommand", "beforeDevCommand"):
            with pytest.raises(ValueError, match="build." + key):
                app_platforms.check_platform({"src-tauri/tauri.conf.json": json.dumps({"build": {key: "x"}}), "package.json": package},
                                             shipped[platform_id])
    for platform_id in ("ios", "android"):
        for name in ("capacitor.config.js", "capacitor.config.ts", "capacitor.config.mjs", "capacitor.config.cjs"):
            with pytest.raises(ValueError, match="may not write"):
                app_platforms.check_platform({name: "x", "package.json": package}, shipped[platform_id])


def _tool_entry() -> dict[str, object]:
    return _python_entry({"before": [["python", "setup.py"]], "command": ["python", "noop.py"],
                          "tool_package": "@scope/real-cli", "tool_bin": "realtool"})


def _setup(*packages: tuple[str, dict[str, object]]) -> str:
    lines = ["import json, pathlib"]
    for name, manifest in packages:
        lines += [f"d = pathlib.Path('node_modules/{name}')", "d.mkdir(parents=True)",
                  f"(d / 'package.json').write_text(json.dumps({manifest!r}))"]
    return "\n".join(lines) + "\n"


_REAL = ("@scope/real-cli", {"name": "@scope/real-cli", "bin": {"realtool": "cli.js"}})
_LISTED = json.dumps({"name": "app", "devDependencies": {"@scope/real-cli": "^1.0.0"}})


def _tool_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setup: str, package: str = _LISTED) -> list[dict[str, object]]:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _tool_entry())
    files = {"setup.json": "{}", "setup.py": setup, "noop.py": "pass\n", "package.json": package}
    return checks(run(tmp_path, Model([WEB, files]), ["custom"], allow_commands=True))


def _build(found: list[dict[str, object]]) -> dict[str, object]:
    return next(c for c in found if c["check"] == "custom build")


def test_the_build_tool_from_the_expected_package_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = _build(_tool_run(tmp_path, monkeypatch, _setup(_REAL, ("left-pad", {"name": "left-pad", "bin": {"other": "x.js"}}))))
    assert found["ok"] is True, found


@pytest.mark.parametrize("fake", [
    ("fake", {"name": "fake", "bin": {"realtool": "x.js"}}),
    ("realtool", {"name": "realtool", "bin": "x.js"}),
    ("@evil/pkg", {"name": "@evil/pkg", "bin": {"RealTool": "x.js"}}),
])
def test_another_package_may_not_provide_the_build_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake: tuple[str, dict[str, object]]) -> None:
    found = _build(_tool_run(tmp_path, monkeypatch, _setup(_REAL, fake)))
    assert found["ok"] is False and "also provides" in str(found["detail"]), found


def test_the_build_fails_when_the_tool_package_is_not_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = _build(_tool_run(tmp_path, monkeypatch, _setup(("fake", {"name": "fake", "bin": "x.js"}))))
    assert found["ok"] is False and "not installed" in str(found["detail"]), found


def test_package_json_must_list_the_tool_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = _tool_run(tmp_path, monkeypatch, _setup(_REAL), json.dumps({"name": "app", "devDependencies": {"vite": "5"}}))
    written = next(c for c in found if c["check"] == "custom written")
    assert written["ok"] is False and "@scope/real-cli" in str(written["detail"])
    assert not any(c["check"] == "custom build" for c in found)


def test_an_output_that_cannot_be_read_fails_the_build_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import app_platforms

    entry = _python_entry({"command": ["python", "noop.py"], "output": "dist"})
    folder = tmp_path / "app"
    (folder / "dist").mkdir(parents=True)
    (folder / "noop.py").write_text("pass\n", encoding="utf-8")

    def broken(path: Path) -> list[tuple[str, int, int]]:
        raise PermissionError("no access")

    monkeypatch.setattr(app_platforms, "_snapshot", broken)
    found = app_platforms.build_check(folder, entry, True, "app")
    assert found["ok"] is False and "dist" in str(found["detail"])


def test_shipped_data_refuses_other_tauri_configs_and_capacitor_hooks() -> None:
    from proofhouse import app_platforms

    shipped = app_platforms.all_platforms()
    package = {"devDependencies": {"@tauri-apps/cli": "2", "@capacitor/cli": "6"}}
    for platform_id in ("windows", "macos", "linux"):
        for name in ("src-tauri/tauri.windows.conf.json5", "src-tauri/Tauri.Windows.toml", "www/Tauri.toml", "app/tauri.linux.conf.json"):
            with pytest.raises(ValueError, match="may not write"):
                app_platforms.check_platform({name: "x", "package.json": json.dumps(package)}, shipped[platform_id])
        with pytest.raises(ValueError, match="build.runner"):
            app_platforms.check_platform({"www/tauri.conf.json": json.dumps({"build": {"runner": "x"}}), "package.json": json.dumps(package)},
                                         shipped[platform_id])
        app_platforms.check_platform({"src-tauri/tauri.conf.json": json.dumps({"build": {"frontendDist": "../www"}}),
                                      "package.json": json.dumps(package)}, shipped[platform_id])
    for platform_id in ("ios", "android"):
        with pytest.raises(ValueError, match="scripts"):
            app_platforms.check_platform({"package.json": json.dumps({**package, "scripts": {"capacitor:sync:before": "node x.js"}})},
                                         shipped[platform_id])


def test_a_fake_tool_is_caught_before_a_later_setup_step_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    _platform_file(tmp_path, _python_entry({"before": [["python", "setup.py"], ["python", "hide.py"]], "command": ["python", "noop.py"],
                                            "tool_package": "@scope/real-cli", "tool_bin": "realtool"}))
    hide = "import shutil\nshutil.rmtree('node_modules/fake')\n"
    files = {"setup.json": "{}", "setup.py": _setup(_REAL, ("fake", {"name": "fake", "bin": {"realtool": "x.js"}})), "hide.py": hide,
             "noop.py": "pass\n", "package.json": _LISTED}
    found = _build(checks(run(tmp_path, Model([WEB, files]), ["custom"], allow_commands=True)))
    assert found["ok"] is False and "also provides" in str(found["detail"]) and found["command"] == ["python", "hide.py"], found


def test_a_bin_folder_cannot_provide_the_build_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup = _setup(_REAL, ("fake", {"name": "fake", "directories": {"bin": "tools"}}))
    setup += "d = pathlib.Path('node_modules/fake/tools')\nd.mkdir()\n(d / 'realtool').write_text('x')\n"
    found = _build(_tool_run(tmp_path, monkeypatch, setup))
    assert found["ok"] is False and "also provides" in str(found["detail"]), found


def test_a_deeply_nested_installed_manifest_is_not_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup = _setup(_REAL) + "d = pathlib.Path('node_modules/deep')\nd.mkdir()\n(d / 'package.json').write_text('[' * 200000 + ']' * 200000)\n"
    found = _build(_tool_run(tmp_path, monkeypatch, setup))
    assert found["ok"] is True, found


_TICK = 1_700_000_000
# Writes argv[1] to the output and stamps it with one fixed time, as a file system that keeps 2-second times would.
_SAME_TICK = ("import os, pathlib, sys\nout = pathlib.Path(sys.argv[2])\nout.parent.mkdir(parents=True, exist_ok=True)\n"
              f"out.write_text(sys.argv[1])\nos.utime(out, ({_TICK}, {_TICK}))\n")


@pytest.mark.parametrize("output", ["dist/app.bin", "dist"])
def test_a_build_that_rewrites_its_output_in_the_same_clock_tick_passes(tmp_path: Path, output: str) -> None:
    from proofhouse import app_platforms

    entry = _python_entry({"before": [["python", "write.py", "aaaa", "dist/app.bin"]],
                           "command": ["python", "write.py", "bbbb", "dist/app.bin"], "output": output})
    folder = tmp_path / "app"
    folder.mkdir()
    (folder / "write.py").write_text(_SAME_TICK, encoding="utf-8")
    found = app_platforms.build_check(folder, entry, True, "app")
    assert found["ok"] is True, found
    assert (folder / "dist" / "app.bin").read_text(encoding="utf-8") == "bbbb"


def test_preparing_the_output_never_touches_files_outside_the_folder(tmp_path: Path) -> None:
    from proofhouse import app_platforms

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    os.utime(outside / "keep.txt", (_TICK, _TICK))
    folder = tmp_path / "app"
    (folder / "dist").mkdir(parents=True)
    try:
        (folder / "dist" / "linked.txt").symlink_to(outside / "keep.txt")
        (folder / "linked-dist").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("this machine cannot make symbolic links")
    (folder / "noop.py").write_text("pass\n", encoding="utf-8")
    for output in ("dist", "linked-dist"):
        app_platforms.build_check(folder, _python_entry({"command": ["python", "noop.py"], "output": output}), True, "app")
    assert (outside / "keep.txt").stat().st_mtime_ns == _TICK * 1_000_000_000


_LINK_OUT = ("import os, sys\n"
             "try:\n    os.symlink(sys.argv[1], 'out', target_is_directory=True)\n"
             "except OSError:\n    import _winapi\n    _winapi.CreateJunction(sys.argv[1], 'out')\n"
             "open(os.path.join('out', 'app.bin'), 'w').write('built')\n")
_MARK = "open('ran.txt', 'w').write('ran')\n"


@pytest.mark.parametrize("linked_by", ["setup", "build"])
def test_an_output_linked_outside_the_folder_fails_the_build_check(tmp_path: Path, linked_by: str) -> None:
    """f939f95-F4: output that resolves outside the app folder is refused, whether a setup step or the build links it."""
    from proofhouse import app_platforms

    outside, folder = tmp_path / "outside", tmp_path / "app"
    outside.mkdir()
    folder.mkdir()
    (folder / "link.py").write_text(_LINK_OUT, encoding="utf-8")
    (folder / "mark.py").write_text(_MARK, encoding="utf-8")
    link_step, mark_step = ["python", "link.py", str(outside)], ["python", "mark.py"]
    build = {"before": [link_step], "command": mark_step} if linked_by == "setup" else {"command": link_step}
    found = app_platforms.build_check(folder, _python_entry({**build, "output": "out/app.bin"}), True, "app")
    assert found["ok"] is False and "outside the app folder" in found["detail"], found
    if linked_by == "setup":
        assert not (folder / "ran.txt").exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="this system has no named pipes")
def test_the_output_check_does_not_open_a_named_pipe(tmp_path: Path) -> None:
    from proofhouse import app_platforms

    (tmp_path / "dist").mkdir()
    os.mkfifo(tmp_path / "dist" / "pipe")
    # Opening a pipe that nothing writes to blocks forever, past every build time limit.
    found: list[tuple[str, int, int, str]] = []
    reader = threading.Thread(target=lambda: found.extend(app_platforms._snapshot(tmp_path / "dist")), daemon=True)
    reader.start()
    reader.join(10)
    assert not reader.is_alive() and found[0][3].startswith("special:"), found


@pytest.mark.skipif(sys.platform != "win32", reason="directory junctions are a Windows feature")
def test_the_output_check_does_not_walk_into_a_directory_junction(tmp_path: Path) -> None:
    from proofhouse import app_platforms

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.txt").write_text("private", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    junction = tmp_path / "dist" / "junction"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], check=True, capture_output=True)
    found = app_platforms._snapshot(tmp_path / "dist")
    assert [entry[0] for entry in found] == [str(junction)] and found[0][3].startswith("link:"), found


def test_the_output_check_stops_hashing_past_its_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import app_platforms

    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "a.bin").write_bytes(b"a" * 10)
    (tmp_path / "dist" / "b.bin").write_bytes(b"b" * 10)
    monkeypatch.setattr(app_platforms, "_HASH_LIMIT", 15)
    digests = [entry[3] for entry in app_platforms._snapshot(tmp_path / "dist")]
    assert len(digests) == 2 and digests.count("unhashed") == 1, digests


def test_cmd_exe_characters_in_the_tool_path_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import app_platforms, make_checks

    # cmd.exe expands %VAR% and ! in the program path too, even inside quotes.
    monkeypatch.setattr(make_checks, "_command", lambda command, args, folder: [r"C:\tools%PATH%\npm.cmd"])
    monkeypatch.setattr(make_checks, "build", lambda *args: pytest.fail("the build ran"))
    found = app_platforms.build_check(tmp_path, _python_entry({"command": ["npm", "run", "build"]}), True, "app")
    assert found["ok"] is False and "cmd.exe" in str(found["detail"]), found


@pytest.mark.parametrize(("platform_id", "output_type", "unsigned"), [("ios", ".app", "CODE_SIGNING_ALLOWED=NO"),
                                                                      ("android", ".apk", "assembleDebug")])
def test_shipped_mobile_builds_make_an_unsigned_app_and_check_it(platform_id: str, output_type: str, unsigned: str) -> None:
    from proofhouse import app_platforms

    build = {entry["id"]: entry for entry in app_platforms._read(app_platforms.SHIPPED)}[platform_id]["build"]
    # `cap build` signs the app, so it stops without a signing team or keystore on the build machine.
    assert "cap" not in build["command"] and unsigned in build["command"], build["command"]
    assert build["output"].endswith(output_type), build["output"]


def test_an_ios_build_that_exits_cleanly_without_the_app_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import app_platforms, make_checks

    entry = {item["id"]: item for item in app_platforms._read(app_platforms.SHIPPED)}["ios"]
    cap = tmp_path / "app" / "node_modules" / "@capacitor" / "cli"
    cap.mkdir(parents=True)
    (cap / "package.json").write_text(json.dumps({"name": "@capacitor/cli", "bin": {"cap": "bin/capacitor"}}), encoding="utf-8")
    monkeypatch.setattr(app_platforms, "host_os", lambda: "macos")
    # Every tool (npm, npx, xcodebuild) is a stand-in that exits 0 and writes nothing.
    monkeypatch.setattr(make_checks, "_command", lambda command, args, folder: [sys.executable, "-c", "pass"])
    found = app_platforms.build_check(tmp_path / "app", entry, True, "app")
    assert found["ok"] is False and "missing" in str(found["detail"]), found


def test_native_build_notes_do_not_call_proven_builds_unconfirmed() -> None:
    """f939f95-F1: every native build ran in the native-builds workflow, so no note may say it has not."""
    from proofhouse import app_platforms

    for platform_id, entry in {e["id"]: e for e in app_platforms._read(app_platforms.SHIPPED)}.items():
        note = entry["build"].get("to_check", "")
        assert "not yet" not in note, (platform_id, note)
