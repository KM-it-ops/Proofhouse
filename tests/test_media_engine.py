"""Images, video, speech and music from any service: templates as data, one paid request through the spend gate."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from proofhouse import cli, media

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"0" * 20


class Service:
    """A stand-in media service: records posts and reads, answers like the real shapes do."""

    def __init__(self, answer: media.MediaResponse, reads: dict[str, list[media.MediaResponse]] | None = None) -> None:
        self.answer = answer
        self.reads = reads or {}
        self.posts: list[media.MediaRequest] = []
        self.gets: list[str] = []

    def post(self, request: media.MediaRequest) -> media.MediaResponse:
        self.posts.append(request)
        return self.answer

    def get(self, url: str, headers: dict) -> media.MediaResponse:
        self.gets.append(url)
        return self.reads[url].pop(0)


def _price(provider: str, model: str, usd: str) -> None:
    assert cli.main(["media", "price", provider, model, "--usd", usd]) == 0


def test_an_image_comes_back_inline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-img-secret")
    _price("openai-images", "gpt-image-1", "0.04")
    svc = Service(media.MediaResponse(200, {"data": [{"b64_json": base64.b64encode(PNG).decode()}]}))
    result = media.generate("image", "openai-images", "gpt-image-1", prompt="a red fox", out=tmp_path / "fox",
                            max_cost_usd="1", transport=svc.post, get=svc.get)
    assert result.status == "success" and Path(result.path).read_bytes() == PNG and result.path.endswith("fox.png")
    (request,) = svc.posts
    assert request.url == "https://api.openai.com/v1/images/generations"
    assert json.loads(request.body_bytes) == {"model": "gpt-image-1", "prompt": "a red fox", "size": "1024x1024", "n": 1}
    assert request.headers["Authorization"] == "Bearer sk-img-secret"
    assert result.admission["price"]["source"] == "declared by you" and result.admission["worst_case_usd"] == "0.04"
    assert "sk-img-secret" not in json.dumps(result.to_dict())


def test_a_video_job_is_waited_for_and_downloaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAL_KEY", "fal-secret")
    _price("fal", "*", "0.50")
    status, done = "https://queue.fal.run/x/status", "https://queue.fal.run/x/result"
    svc = Service(
        media.MediaResponse(200, {"request_id": "1", "status_url": status, "response_url": done}),
        {status: [media.MediaResponse(200, {"status": "IN_PROGRESS"}), media.MediaResponse(200, {"status": "COMPLETED"})],
         done: [media.MediaResponse(200, {"video": {"url": "https://cdn.fal.media/clip.mp4"}})],
         "https://cdn.fal.media/clip.mp4": [media.MediaResponse(200, None, MP4)]},
    )
    result = media.generate("video", "fal", "fal-ai/some-video-model", prompt="a drone shot over a city", out=tmp_path / "clip",
                            max_cost_usd="1", transport=svc.post, get=svc.get, poll_every=0)
    assert result.status == "success" and result.path.endswith("clip.mp4") and Path(result.path).read_bytes() == MP4
    assert svc.posts[0].url == "https://queue.fal.run/fal-ai/some-video-model"
    assert svc.posts[0].headers["Authorization"] == "Key fal-secret"
    assert len(svc.posts) == 1  # waiting and downloading are reads, never a second paid request


def test_speech_comes_back_as_a_file_and_is_priced_per_thousand_characters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-secret")
    _price("elevenlabs", "eleven_multilingual_v2", "0.30")
    svc = Service(media.MediaResponse(200, None, b"ID3" + b"0" * 10))
    words = "Proofhouse makes it. " * 120  # 2,520 characters: 3 units
    result = media.generate("speech", "elevenlabs", "eleven_multilingual_v2", prompt=words, out=tmp_path / "vo",
                            params={"voice": "voice123"}, max_cost_usd="1", transport=svc.post, get=svc.get)
    assert result.status == "success" and result.path.endswith("vo.mp3")
    assert svc.posts[0].url == "https://api.elevenlabs.io/v1/text-to-speech/voice123"
    assert svc.posts[0].headers["xi-api-key"] == "el-secret"
    assert result.admission["price"]["units"] == "3" and result.admission["worst_case_usd"] == "0.90"


def test_over_the_limit_or_without_a_price_nothing_is_sent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r")
    svc = Service(media.MediaResponse(200, {}))
    no_price = media.generate("video", "replicate", "owner/model", prompt="x", out=tmp_path / "a", max_cost_usd="1",
                              transport=svc.post, get=svc.get)
    assert no_price.code == "PHC-COST-0002"
    _price("replicate", "owner/model", "2.00")
    over = media.generate("video", "replicate", "owner/model", prompt="x", out=tmp_path / "b", max_cost_usd="1",
                          transport=svc.post, get=svc.get)
    assert over.code == "PHC-COST-0001" and svc.posts == []


def test_a_job_that_fails_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r")
    _price("replicate", "*", "0.10")
    status = "https://api.replicate.com/v1/predictions/abc"
    svc = Service(media.MediaResponse(201, {"urls": {"get": status}, "status": "starting"}),
                  {status: [media.MediaResponse(200, {"status": "failed"})]})
    result = media.generate("image", "replicate", "owner/model", prompt="x", out=tmp_path / "a", max_cost_usd="1",
                            transport=svc.post, get=svc.get, poll_every=0)
    assert result.code == "PHC-RUN-0006" and "failed" in result.message


def test_wrong_kind_missing_key_and_unknown_service_send_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert media.generate("video", "openai-speech", "m", prompt="x", out=tmp_path / "a", max_cost_usd="1").code == "PHC-RUN-0002"
    assert media.generate("image", "openai-images", "m", prompt="x", out=tmp_path / "a", max_cost_usd="1").code == "PHC-RUN-0003"
    assert media.generate("image", "nope", "m", prompt="x", out=tmp_path / "a", max_cost_usd="1").code == "PHC-RUN-0001"


def test_any_service_is_a_template_away_and_a_local_one_is_free(tmp_path: Path) -> None:
    template = {
        "id": "my-gpu", "name": "My GPU box", "kinds": ["image"], "base_url": "http://localhost:7860", "key_env": None,
        "auth": "none", "unit": "image", "submit": {"path": "/generate", "body": {"prompt": "{prompt}", "steps": 30}},
        "result": {"asset": ["image"], "ext": "png"},
    }
    (tmp_path / "t.json").write_text(json.dumps(template), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "t.json")]) == 0
    svc = Service(media.MediaResponse(200, {"image": base64.b64encode(PNG).decode()}))
    result = media.generate("image", "my-gpu", "sdxl", prompt="a fox", out=tmp_path / "fox", transport=svc.post, get=svc.get)
    assert result.status == "success" and result.admission["price"]["source"] == "on this machine: no charge"
    assert svc.posts[0].url == "http://localhost:7860/generate"


def test_a_template_cannot_send_to_another_host(tmp_path: Path) -> None:
    bad = {"id": "sneaky", "kinds": ["image"], "base_url": "https://api.good.ai", "unit": "request",
           "submit": {"path": "@evil.example/steal", "body": {}}, "result": {"asset": ["x"]}}
    profile = media._parse(bad, "yours")
    with pytest.raises(media.MediaError):
        media.build_request(profile, "m", {"prompt": "x"})
