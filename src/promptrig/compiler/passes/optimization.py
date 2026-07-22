"""Optimization pass: v0.1 is a traced no-op.

Any future optimization must be a provably intent-preserving transform that
never changes objective, requirements, contracts, constraints, policies, or
required capabilities (Compiler Invariant #5).
"""
from __future__ import annotations

from ..contracts import Diagnostic
from .base import CompilationState


class OptimizationPass:
    name = "optimization"

    def run(self, state: CompilationState) -> tuple[CompilationState, tuple[Diagnostic, ...]]:
        return state, ()
