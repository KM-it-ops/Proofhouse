from __future__ import annotations

import pytest

from promptrig.compiler.contracts import Artifact
from promptrig.compiler.sink import DirectorySink, InMemorySink


def _artifact(name: str = "compiled_prompt") -> Artifact:
    data = b'{"hello": "world"}'
    import hashlib

    return Artifact(name=name, media_type="application/json", sha256=hashlib.sha256(data).hexdigest(), data=data)


def test_in_memory_sink_returns_artifact_unchanged():
    sink = InMemorySink()
    artifact = _artifact()
    result = sink.write(artifact)
    assert result is artifact
    assert result.data is not None
    assert result.path is None


def test_directory_sink_writes_file_and_returns_path(tmp_path):
    sink = DirectorySink(tmp_path)
    artifact = _artifact()
    result = sink.write(artifact)

    assert result.path is not None
    assert result.data is None
    written = tmp_path / "compiled_prompt"
    assert written.exists()
    assert written.read_bytes() == artifact.data


def test_directory_sink_refuses_to_escape_its_directory(tmp_path):
    sink = DirectorySink(tmp_path)
    escaping = Artifact(
        name="../escape.json",
        media_type="application/json",
        sha256="a" * 64,
        data=b"{}",
    )
    with pytest.raises(ValueError):
        sink.write(escaping)


def test_directory_sink_requires_in_memory_data(tmp_path):
    sink = DirectorySink(tmp_path)
    already_written = Artifact(name="x", media_type="application/json", sha256="a" * 64, path="/somewhere/x")
    with pytest.raises(ValueError):
        sink.write(already_written)
