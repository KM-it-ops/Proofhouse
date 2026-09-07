"""Caller-controlled artifact sink.

Compiler Core never decides where artifacts are persisted; it writes only
through a sink supplied by the caller and never writes outside it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .contracts import Artifact


class ArtifactSink(Protocol):
    def write(self, artifact: Artifact) -> Artifact:
        """Persist `artifact` and return the Artifact record describing where
        it now lives (or the same in-memory record, for in-memory sinks)."""
        ...


class InMemorySink:
    """Default sink: artifacts are returned exactly as produced, with their
    bytes held in memory. Nothing is written to disk."""

    def write(self, artifact: Artifact) -> Artifact:
        return artifact


class DirectorySink:
    """Writes each artifact's bytes to `directory/<name>`, returning an
    Artifact whose `path` refers to that location. Refuses to write outside
    `directory`, even if an artifact name were to contain path segments."""

    def __init__(self, directory: Path | str):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def write(self, artifact: Artifact) -> Artifact:
        if artifact.data is None:
            raise ValueError(f"artifact {artifact.name!r} has no in-memory bytes to write")

        resolved_dir = self._directory.resolve()
        target = (self._directory / artifact.name).resolve()
        if target != resolved_dir and resolved_dir not in target.parents:
            raise ValueError(f"refusing to write artifact {artifact.name!r} outside sink directory")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(artifact.data)
        return Artifact(
            name=artifact.name,
            media_type=artifact.media_type,
            sha256=artifact.sha256,
            path=str(target),
            provenance=artifact.provenance,
        )
