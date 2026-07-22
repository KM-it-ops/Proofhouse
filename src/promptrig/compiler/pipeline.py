"""Ordered pass pipeline runner.

The pipeline runs passes in a fixed order, exposes per-pass input/output
digests and duration as non-semantic telemetry, and stops as soon as any
pass emits an error-severity diagnostic (Compiler Invariant #2, #14).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .canonical import canonical_sha256
from .contracts import Diagnostic, PassTraceEntry
from .passes.base import CompilationState, Pass

PASS_ORDER = (
    "normalization",
    "validation",
    "optimization",
    "capability_resolution",
    "safety",
    "adapter_lowering",
)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    state: CompilationState
    diagnostics: tuple[Diagnostic, ...]
    trace: tuple[PassTraceEntry, ...]


def run_pipeline(initial_state: CompilationState, passes: tuple[Pass, ...]) -> PipelineResult:
    declared_order = [p.name for p in passes]
    expected_prefix = list(PASS_ORDER[: len(declared_order)])
    if declared_order != expected_prefix:
        raise ValueError(
            f"passes must run in the fixed pipeline order {PASS_ORDER}; got {tuple(declared_order)}"
        )

    state = initial_state
    all_diagnostics: list[Diagnostic] = []
    trace: list[PassTraceEntry] = []

    for pass_ in passes:
        if state.stopped:
            break

        input_digest = _digest_state(state)
        start = time.monotonic()
        new_state, diagnostics = pass_.run(state)
        duration = time.monotonic() - start
        output_digest = _digest_state(new_state)

        trace.append(
            PassTraceEntry(
                pass_name=pass_.name,
                input_digest=input_digest,
                output_digest=output_digest,
                duration_seconds=duration,
            )
        )
        all_diagnostics.extend(diagnostics)
        state = new_state

    return PipelineResult(state=state, diagnostics=tuple(all_diagnostics), trace=tuple(trace))


def _digest_state(state: CompilationState) -> str:
    return canonical_sha256(
        {
            "ir_document": state.ir_document,
            "capability_decisions": [d.to_dict() for d in state.capability_decisions],
            "artifact_hashes": sorted(a.sha256 for a in state.artifacts),
        }
    )
