"""`proofhouse models update` keeps the model and workspace lists current from each provider and official pages."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from proofhouse import catalog, cli, hosts, live, make, providers, spend
from proofhouse.optimize import model_notes

SECRET = "xai-test-key-never-shown"
PAGE = "<html><head><script>var x = 1;</script></head><body><h1>Release notes</h1>" + "<p>News.</p>" * 60 + "</body></html>"
READING = {
    "models": [{"id": "zeta-2", "name": "Zeta 2", "maker": "Zeta Labs", "released": "2026-10-16",
                "summary": "Zeta's new coding model. 400k context, $1/$5 per 1M tokens."},
               {"id": "grok-4.7", "name": "Grok 4.7", "maker": "xAI", "summary": "Already known."}],
    "workspaces": [{"name": "Zeta Desk", "maker": "Zeta Labs", "released": "2026-10-16",
                    "summary": "A desktop app where Zeta agents work on your files.", "settings": "~/.zeta/agents"},
                   {"name": "Grok Bot", "maker": "xAI", "summary": "Already known."}],
}


@pytest.fixture(autouse=True)
def no_real_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for profile in providers.all_providers().values():
        if profile.key_env:
            monkeypatch.delenv(profile.key_env, raising=False)


class Web:
    """A stand-in for the internet: answers by address and keeps every request it was sent."""

    def __init__(self, pages: dict[str, tuple[int, str, str]] | None = None) -> None:
        self.pages = pages or {}
        self.sent: list[tuple[str, dict[str, str], bool]] = []

    def __call__(self, url: str, headers: dict[str, str], follow: bool) -> tuple[int, str, str]:
        self.sent.append((url, dict(headers), follow))
        if url in self.pages:
            return self.pages[url]
        if url == "https://api.x.ai/v1/models":
            return 200, url, json.dumps({"data": [{"id": "grok-4.7"}, {"id": "grok-5-preview"}, {"id": "bad id!"}]})
        raise ConnectionError(f"nothing at {url}")


class Reader:
    """A stand-in model that reads a release page and answers with what it found."""

    def __init__(self, reading: dict | str = READING) -> None:
        self.reading = reading if isinstance(reading, str) else json.dumps(reading)
        self.sent: list[str] = []

    def __call__(self, request: live.Request) -> live.Response:
        self.sent.append(json.loads(request.body_bytes)["messages"][0]["content"])
        return live.Response(200, {"choices": [{"message": {"content": self.reading}}],
                                   "usage": {"prompt_tokens": 10, "completion_tokens": 10}})


def _sources(*entries: dict) -> None:
    (providers.proofhouse_home() / "release_sources.json").write_text(
        json.dumps({"schema": catalog.SOURCES_SCHEMA, "sources": list(entries)}), encoding="utf-8")


def _only_zeta_source() -> str:
    url = "https://docs.zeta.example/release-notes"
    _sources({"id": "zeta", "name": "Zeta release notes", "url": url, "covers": ["models", "workspaces"]})
    return url


def test_each_provider_is_listed_with_its_own_key_at_its_own_host_never_redirected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)
    web = Web()
    found = catalog.update(get=web)
    keyed = [(url, headers, follow) for url, headers, follow in web.sent if "Authorization" in headers]
    assert keyed == [("https://api.x.ai/v1/models", {"Accept": "application/json", "Authorization": f"Bearer {SECRET}"}, False)]
    assert all(not follow for _url, _headers, follow in web.sent)  # no page was read: no model was named
    assert found.listed["xai"] == "2 models"  # "bad id!" is not a model id
    assert found.listed["ollama"] == "not listed: could not reach it (ConnectionError)"
    assert "openai" not in found.listed  # no key, not on this machine: not asked
    assert [m["id"] for m in found.new_models] == ["grok-5-preview"]  # grok-4.7 is already known
    assert found.new_models[0]["listed_by"] == ["xai"] and found.new_models[0]["summary"] is None
    assert "--max-cost-usd" in found.note
    saved = json.loads(catalog.catalog_path().read_text(encoding="utf-8"))
    assert saved["checked_at"] == found.checked_at and "grok-5-preview" in saved["models"]

    again = catalog.update(get=Web())
    assert again.new_models == []  # seen once, recorded once


@pytest.mark.parametrize("answer", [
    ConnectionError(f"refused while sending Bearer {SECRET}"),
    (401, "https://api.x.ai/v1/models", f"bad key {SECRET}"),
    (200, "https://api.x.ai/v1/models", f"not json {SECRET}"),
])
def test_the_key_never_shows_in_a_failure(answer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)

    def get(url: str, headers: dict[str, str], follow: bool) -> tuple[int, str, str]:
        if isinstance(answer, Exception):
            raise answer
        return answer

    found = catalog.update(get=get)
    assert found.listed["xai"].startswith("not listed: ")
    assert SECRET not in json.dumps(found.to_dict()) and SECRET not in catalog.catalog_path().read_text(encoding="utf-8")


def test_a_provider_whose_models_address_is_not_its_host_is_not_sent_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)
    monkeypatch.setattr(providers.Provider, "host", property(lambda self: "checked.example"))
    web = Web()
    with pytest.raises(catalog.CatalogError, match="does not match provider xai"):
        catalog.list_provider(providers.find("xai"), web)
    assert web.sent == []


def test_release_pages_are_read_through_the_spend_gate_inside_one_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    url = _only_zeta_source()
    gate: list[str] = []
    real_gate = spend.send_within_ceiling

    def spy(*args, **kwargs):
        gate.append(kwargs["provider"])
        return real_gate(*args, **kwargs)

    monkeypatch.setattr(spend, "send_within_ceiling", spy)
    budgets: list[make.Budget] = []
    real_budget = make.Budget

    def counted(*args, **kwargs):
        budgets.append(real_budget(*args, **kwargs))
        return budgets[-1]

    monkeypatch.setattr(make, "Budget", counted)
    reader = Reader()
    found = catalog.update(provider_id="ollama", model="m", only=["zeta", "openai-api"],
                           get=Web({url: (200, url, PAGE), "https://developers.openai.com/api/docs/changelog":
                                    (200, "https://developers.openai.com/api/docs/changelog", PAGE)}),
                           transport=reader)
    assert len(budgets) == 1 and gate == ["ollama", "ollama"]  # two pages, two gated calls, one limit
    assert len(reader.sent) == 2 and "var x = 1" not in reader.sent[0] and "Release notes" in reader.sent[0]
    assert any(f"Page address: {url}" in sent for sent in reader.sent)
    assert found.read["zeta"] == "2 models, 2 workspaces on the page"
    assert [m["id"] for m in found.new_models] == ["zeta-2"]  # Grok 4.7 is known; the page read second adds nothing new
    first = "https://developers.openai.com/api/docs/changelog"  # shipped sources are read before yours
    assert found.new_models[0]["sources"] == [first] and found.new_models[0]["released"] == "2026-10-16"

    notes = model_notes.resolve_model_notes("zeta-2")
    assert notes.source == model_notes.SOURCE_CACHED
    assert "400k context" in notes.notes and "picked out of the page by ollama/m; not reviewed" in notes.notes
    assert list(notes.sources) == [first]

    assert [w["name"] for w in found.new_workspaces] == ["Zeta Desk"]  # Grok Bot already ships
    desk = found.new_workspaces[0]
    assert desk["settings"] == "~/.zeta/agents" and desk["read_by"] == "ollama/m"
    assert str(providers.proofhouse_home() / "hosts.json") in desk["next"]


def test_a_page_that_moves_to_another_site_is_not_read() -> None:
    url = _only_zeta_source()
    reader = Reader()
    found = catalog.update(provider_id="ollama", model="m", only=["zeta"],
                           get=Web({url: (200, "https://evil.example/zeta", PAGE)}), transport=reader)
    assert found.read["zeta"].startswith("not read: it moved to evil.example, outside docs.zeta.example; "
                                         "if the page really moved, give its new address in ")
    assert reader.sent == [] and found.new_models == []


@pytest.mark.parametrize("final", ["https://zeta.example/notes", "https://www.docs.zeta.example/notes"])
def test_a_page_that_moves_within_its_own_site_is_read(final: str) -> None:
    url = _only_zeta_source()
    found = catalog.update(provider_id="ollama", model="m", only=["zeta"],
                           get=Web({url: (200, final, PAGE)}), transport=Reader())
    assert found.read["zeta"].endswith("on the page")


@pytest.mark.parametrize("source, final", [
    ("https://zeta.github.io/notes", "https://evil.github.io/notes"),  # a neighbour on a shared host is someone else
    ("https://docs.zeta.co.uk/notes", "https://evil.co.uk/notes"),
    ("https://docs.zeta.example/notes", "http://docs.zeta.example/notes"),  # dropped to plain http
    ("https://docs.zeta.example/notes", "https://notzeta.example/docs.zeta.example"),
])
def test_a_page_that_ends_somewhere_it_should_not_is_not_read(source: str, final: str) -> None:
    _sources({"id": "zeta", "name": "Zeta", "url": source, "covers": ["models"]})
    reader = Reader()
    found = catalog.update(provider_id="ollama", model="m", only=["zeta"], get=Web({source: (200, final, PAGE)}),
                           transport=reader)
    assert found.read["zeta"].startswith("not read: it moved to") and reader.sent == []


def test_an_add_on_that_names_another_providers_key_is_not_sent_it(monkeypatch: pytest.MonkeyPatch) -> None:
    from proofhouse import addons

    real = addons.contributions
    borrowed = {"id": "lookalike", "base_url": "https://evil.example/v1", "key_env": "OPENAI_API_KEY"}
    own = {"id": "zeta-cloud", "base_url": "https://api.zeta.example/v1", "key_env": "ZETA_API_KEY"}
    monkeypatch.setattr(addons, "contributions",
                        lambda kind: [("pack", borrowed), ("pack", own)] if kind == "providers" else real(kind))
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("ZETA_API_KEY", "zeta-own-key")
    web = Web({"https://api.openai.com/v1/models": (200, "https://api.openai.com/v1/models", '{"data": []}'),
               "https://api.zeta.example/v1/models": (200, "https://api.zeta.example/v1/models", '{"data": []}')})
    found = catalog.update(get=web)
    assert all(not url.startswith("https://evil.example") for url, _h, _f in web.sent)
    assert found.listed["lookalike"] == ("not listed: it names OPENAI_API_KEY, the key of openai, but runs on "
                                         "evil.example; name it with --provider to use it on purpose")
    assert found.listed["openai"] == "0 models" and found.listed["zeta-cloud"] == "0 models"  # its own key, its own host


def test_page_notes_are_not_put_into_prompts_until_you_review_them(tmp_path: Path) -> None:
    from proofhouse.optimize import packets

    url = _only_zeta_source()
    catalog.update(provider_id="ollama", model="m", only=["zeta"], get=Web({url: (200, url, PAGE)}), transport=Reader())
    picked = model_notes.resolve_model_notes("zeta-2")
    assert picked.verification == model_notes.VERIFICATION_FROM_PAGE and "400k context" in picked.notes
    clarify = packets.clarify_packet("write a haiku", picked, "balanced", False)
    assert "400k context" not in clarify.system
    assert model_notes.prompt_notes(picked) == model_notes.resolve_model_notes("no-such-model-xyz").notes

    model_notes.remember("zeta-2", "Zeta 2: 400k context, checked by hand.", sources=[url])
    mine = model_notes.resolve_model_notes("zeta-2")
    assert mine.verification == model_notes.VERIFICATION_SOURCED
    assert "checked by hand" in packets.clarify_packet("write a haiku", mine, "balanced", False).system


def test_control_characters_from_a_page_are_removed() -> None:
    url = _only_zeta_source()
    reading = {"models": [{"id": "zeta-9", "name": "Zeta\u001b[2J 9", "summary": "Fast.\u0007\u001b]0;owned\u0007"}],
               "workspaces": [{"name": "Desk\u001b[31m", "summary": "x\u0000y"}]}
    found = catalog.update(provider_id="ollama", model="m", only=["zeta"], get=Web({url: (200, url, PAGE)}),
                           transport=Reader(reading))
    model, space = found.new_models[0], found.new_workspaces[0]
    assert model["name"] == "Zeta[2J 9" and model["summary"] == "Fast.]0;owned"
    assert space["name"] == "Desk[31m" and space["summary"] == "xy"


@pytest.mark.parametrize("limit", ["NaN", "-1", "Infinity", "lots"])
def test_a_bad_spending_limit_is_refused_before_anything_is_sent(limit: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)
    web = Web()
    with pytest.raises(catalog.CatalogError, match="--max-cost-usd must be a plain amount"):
        catalog.update(provider_id="openai", model="gpt-6-luna", max_cost_usd=limit, get=web)
    assert web.sent == [] and not catalog.catalog_path().exists()


def test_a_huge_page_is_read_only_up_to_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    httpx = pytest.importorskip("httpx")
    sent: list[int] = []

    def endless(request):
        def body():
            for _ in range(10_000):
                sent.append(1)
                yield b"x" * 65536
        return httpx.Response(200, content=body())

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(endless), **kw))
    status, _final, text = catalog._httpx_get("https://docs.zeta.example/notes", {}, True)
    assert status == 200 and len(text) == catalog.MAX_BYTES
    assert len(sent) < 10_000  # it stopped reading


def test_an_answer_that_is_not_json_is_reported_not_recorded() -> None:
    url = _only_zeta_source()
    found = catalog.update(provider_id="ollama", model="m", only=["zeta"], get=Web({url: (200, url, PAGE)}),
                           transport=Reader("I could not find anything."))
    assert found.read["zeta"] == "not read: the model's answer was not the JSON asked for"
    assert found.new_models == [] and found.new_workspaces == []


def test_a_model_a_provider_listed_gets_notes_once_a_page_describes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)
    catalog.update(get=Web())
    url = _only_zeta_source()
    reading = {"models": [{"id": "grok-5-preview", "name": "Grok 5 Preview", "maker": "xAI",
                           "summary": "A preview of Grok 5 for long agent runs."}], "workspaces": []}
    found = catalog.update(provider_id="ollama", model="m", only=["zeta"], get=Web({url: (200, url, PAGE)}),
                           transport=Reader(reading))
    assert found.new_models == []  # not new: xai listed it before
    entry = catalog.load()["models"]["grok-5-preview"]
    assert entry["summary"].startswith("A preview of Grok 5") and entry["sources"] == [url]
    assert "long agent runs" in model_notes.resolve_model_notes("grok-5-preview").notes


@pytest.mark.parametrize("kwargs, message", [
    ({"provider_id": "ollama"}, "name both --provider and --model"),
    ({"provider_id": "nope", "model": "m"}, "no provider named 'nope'"),
    ({"provider_id": "openai", "model": "gpt-6-luna"}, "--max-cost-usd"),
    ({"only": ["no-such-page"]}, "no release source named no-such-page"),
])
def test_an_update_that_cannot_start_says_why_and_writes_nothing(kwargs: dict, message: str) -> None:
    web = Web()
    with pytest.raises(catalog.CatalogError, match=message.replace("(", r"\(")):
        catalog.update(get=web, **kwargs)
    assert web.sent == [] and not catalog.catalog_path().exists()


def test_due_reminds_when_never_run_or_a_week_old() -> None:
    assert "never been updated" in catalog.due({"checked_at": None})
    assert catalog.due({"checked_at": "2026-10-15T09:00:00Z"}, today=date(2026, 10, 18)) is None
    assert catalog.due({"checked_at": "2026-10-11T09:00:00Z"}, today=date(2026, 10, 18)) == (
        "the model list was last updated 7 days ago; run `proofhouse models update`")


def test_a_broken_catalog_is_kept_aside_and_started_again() -> None:
    path = catalog.catalog_path()
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert catalog.load()["models"] == {}
    kept = list(path.parent.glob("catalog.json.unreadable-*"))
    assert len(kept) == 1 and kept[0].read_text(encoding="utf-8") == "{not json" and not path.exists()


def test_your_sources_file_adds_and_replaces_by_id() -> None:
    shipped = {s.id: s for s in catalog.sources()}
    assert {"openai-api", "anthropic-models", "xai", "google-gemini-api", "cursor"} <= set(shipped)
    assert all(s.url.startswith("https://") for s in shipped.values())
    _sources({"id": "xai", "name": "Mine", "url": "https://x.ai/news"},
             {"id": "zeta", "name": "Zeta", "url": "https://zeta.example/news", "covers": ["workspaces"]})
    mine = {s.id: s for s in catalog.sources()}
    assert len(mine) == len(shipped) + 1
    assert mine["xai"].url == "https://x.ai/news" and mine["xai"].covers == ("models",)
    assert mine["zeta"].covers == ("workspaces",)


@pytest.mark.parametrize("entry", [
    {"id": "plain", "url": "http://zeta.example/news"},
    {"id": "Bad Id", "url": "https://zeta.example/news"},
    {"id": "creds", "url": "https://user:pw@zeta.example/news"},
    {"id": "covers", "url": "https://zeta.example/news", "covers": ["videos"]},
])
def test_a_bad_source_is_refused(entry: dict) -> None:
    _sources(entry)
    with pytest.raises(catalog.CatalogError):
        catalog.sources()


def test_models_update_and_list_through_the_front_door(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("XAI_API_KEY", SECRET)
    monkeypatch.setattr(catalog, "_httpx_get", Web())
    assert cli.main(["models", "update", "--json"], prog="proofhouse") == 0
    data = json.loads(capsys.readouterr().out)["data"]
    assert [m["id"] for m in data["new_models"]] == ["grok-5-preview"] and data["spent_usd_estimated"] == "0"
    assert data["catalog"] == str(catalog.catalog_path())

    assert cli.main(["models", "list", "--json"], prog="proofhouse") == 0
    listed = json.loads(capsys.readouterr().out)["data"]["catalog"]
    assert listed["checked_at"] == data["checked_at"] and listed["due"] is None
    assert "grok-5-preview" in listed["models"]

    assert cli.main(["models", "list"], prog="proofhouse") == 0
    out, err = capsys.readouterr()
    assert "  also offered by your providers, no notes yet: grok-5-preview" in out.splitlines() and err == ""

    assert cli.main(["models", "update", "--provider", "ollama"], prog="proofhouse") == 2
    assert "name both --provider and --model" in capsys.readouterr().err


def test_grok_bot_is_a_known_workspace_that_keeps_nothing_on_your_machine(capsys) -> None:
    assert "grok-bot" in hosts.all_hosts()
    with pytest.raises(hosts.HostError, match=r"^Grok Bot has no place for rules on your machine \(xAI's cloud teammate"):
        hosts.target("grok-bot", "rule", "house-style", None)
    assert cli.main(["hosts", "list"], prog="proofhouse") == 0
    out = capsys.readouterr().out
    assert "Grok Bot" in out and "keeps no settings on your machine" in out
