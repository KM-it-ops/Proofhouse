"""Regression checks from the adversarial review. No provider calls or real secrets."""
import builtins
import json
import threading
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from proofhouse import agent_server, live, loop, make, media, sitecheck


def test_bridge_rejects_cross_origin_unauthenticated_form_request(monkeypatch):
    monkeypatch.setenv(agent_server.TOKEN_ENV, "synthetic-test-token")
    calls = []
    server = agent_server.make_server("codex", port=0, runner=lambda *args: calls.append(args) or "synthetic answer")
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        body = json.dumps({"messages": [{"role": "user", "content": "synthetic instruction"}]}).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/chat/completions", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://untrusted.invalid"})
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request, timeout=5)
        assert exc.value.code == 401
        assert not calls
        request.add_header("Authorization", "Bearer synthetic-test-token")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request, timeout=5)
        assert exc.value.code == 403
        assert not calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_stdlib_fallback_does_not_forward_dummy_bearer_to_redirect_destination(monkeypatch):
    captured = []
    class Destination(BaseHTTPRequestHandler):
        def do_GET(self):
            captured.append(self.headers.get("Authorization"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')
        def log_message(self, *args):
            pass
    destination = ThreadingHTTPServer(("127.0.0.1", 0), Destination)
    class Source(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{destination.server_port}/capture")
            self.end_headers()
        def log_message(self, *args):
            pass
    source = ThreadingHTTPServer(("127.0.0.1", 0), Source)
    threads = [threading.Thread(target=s.serve_forever) for s in (source, destination)]
    for thread in threads:
        thread.start()
    original = builtins.__import__
    def without_httpx(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("simulate default installation without optional httpx")
        return original(name, *args, **kwargs)
    try:
        monkeypatch.setattr(builtins, "__import__", without_httpx)
        response = live._httpx_post(live.Request(f"http://127.0.0.1:{source.server_port}/chat/completions",
            {"Authorization": "Bearer SYNTHETIC-REVIEW-KEY"}, {}, b'{}'))
        assert response.status_code == 302
        assert captured == []
    finally:
        for server in (source, destination):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join()


_PAGE = '<html lang="en"><head><title>Review</title><meta name="viewport" content="width=device-width"></head><body>{body}</body></html>'
_BROKEN = _PAGE.format(body='<a href="missing.html">Broken</a>')
_SOUND = _PAGE.format(body="<h1>Review</h1><p>Welcome.</p>")


def _site_model(pages, scores):
    """A stand-in model: page N for the Nth write or revise, score N for the Nth judging."""
    made, judged = [], []
    def model(request):
        text = json.loads(request.body_bytes)["messages"][0]["content"]
        if text.startswith("You judge AI work"):
            judged.append(1)
            content = json.dumps({"score": scores[len(judged) - 1], "missing": [], "fix": ""})
        else:
            made.append(1)
            content = json.dumps({"files": {"index.html": pages[min(len(made), len(pages)) - 1]}})
        return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    return model


def test_high_judge_score_cannot_stop_early_on_a_site_with_a_known_broken_link(tmp_path, monkeypatch):
    # 108: draft 106 also delivered nothing here. A failed check now blocks the early stop and loses to any version
    # that passes, but when every version has one the best is still handed over, with the failure on record.
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sitecheck, "find_browser", lambda: None)
    made = make.make("a usable website", provider_id="ollama", model="synthetic", kind="site", rounds=3,
                     out_dir=tmp_path / "result", transport=_site_model([_BROKEN], [10, 10, 10]))
    checks = json.loads((made.folder / "v1" / "checks.json").read_text())
    assert any(c["ok"] is False for c in checks)
    assert len(made.rounds) == 3 and made.stopped == "rounds used up"
    assert made.best_version == 3 and (made.folder / "site" / "index.html").is_file()


def test_a_version_that_passes_its_checks_beats_a_higher_scored_one_that_does_not(tmp_path, monkeypatch):
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sitecheck, "find_browser", lambda: None)
    made = make.make("a usable website", provider_id="ollama", model="synthetic", kind="site", rounds=2, target=11,
                     out_dir=tmp_path / "result", transport=_site_model([_BROKEN, _SOUND], [10, 6]))
    assert [r.score for r in made.rounds] == [10, 6]
    assert made.best_version == 2
    assert "missing.html" not in (made.folder / "site" / "index.html").read_text(encoding="utf-8")


def test_loop_cannot_read_dotenv_into_next_prompt(tmp_path):
    (tmp_path / ".env").write_text("INTERNAL_PASSWORD=SYNTHETIC-UNREGISTERED-PASSWORD")
    outcome = loop._act({"read": ".env"}, tmp_path.resolve(), False, 1, [])
    step = loop.Step(1, "review", sent=True, actions=[outcome])
    state = loop._state(tmp_path.resolve(), [step], None, None)
    assert outcome["ok"] is False
    assert "SYNTHETIC-UNREGISTERED-PASSWORD" not in state


def test_loop_cannot_write_git_hook_without_allow_commands(tmp_path):
    outcome = loop._act({"write": ".git/hooks/pre-commit", "text": "synthetic inert hook"},
                        tmp_path.resolve(), False, 1, [])
    assert outcome["ok"] is False
    assert not (tmp_path / ".git").exists()


def test_site_writer_rejects_case_collisions_before_writing(tmp_path):
    with pytest.raises(sitecheck.SiteError, match="letter case"):
        sitecheck.write_site({"index.html": "good version", "INDEX.HTML": "overwritten version"}, tmp_path / "site")
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize("name", ["CON.html", "folder/NUL.txt", "file.", "folder/.npmrc"])
def test_site_writer_rejects_nonportable_or_sensitive_names(tmp_path, name):
    with pytest.raises(sitecheck.SiteError):
        sitecheck.write_site({"index.html": "x", name: "y"}, tmp_path / "site")
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize("name", [".env", ".env.production", ".git/config", ".ssh/id_rsa", "auth.json", "private.pem",
    ".git./hooks/pre-commit", ".git /hooks/pre-commit", ".env.", ".env:stream"])
def test_sensitive_paths_cannot_be_read_or_written_by_loop(tmp_path, name):
    for action in ({"read": name}, {"write": name, "text": "synthetic"}):
        assert loop._act(action, tmp_path.resolve(), False, 1, [])["ok"] is False


def test_bridge_never_listens_without_a_token(monkeypatch, tmp_path):
    # 108: with no token named, the bridge makes a private one and saves it; it never runs open.
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    monkeypatch.delenv(agent_server.TOKEN_ENV, raising=False)
    server = agent_server.make_server("codex", port=0, runner=lambda *args: "unused")
    try:
        assert server.token and (tmp_path / agent_server.TOKEN_FILE).read_text(encoding="utf-8").strip() == server.token
    finally:
        server.server_close()


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_media_does_not_replay_requests_or_forward_custom_keys(monkeypatch, method):
    import httpx

    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(307, headers={"Location": "https://second.invalid/replayed"})
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs))
    url, headers = "https://first.invalid/generate", {"X-Api-Key": "SYNTHETIC-MEDIA-KEY"}
    response = media._httpx_post(media.MediaRequest(url, headers, {}, b'{}')) if method == "POST" \
        else media._httpx_get(url, headers)
    assert response.status_code == 307 and len(seen) == 1
