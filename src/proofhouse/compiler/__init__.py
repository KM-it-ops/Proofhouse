"""Proofhouse Compiler Core v0.1 — deterministic, offline IR compiler.

Public library surface lives in `proofhouse.compiler.api`. Default
compile/validate/closed-loop paths contain no live provider calls, network
access, or credential handling. Opt-in live OpenAI execution lives in
`execution.py` (fail-closed, DEFERRED-to-opt-in, not CERTIFIED).
"""
from __future__ import annotations

COMPILER_ID = "proofhouse-compiler-core"
COMPILER_VERSION = "0.1.0"
IR_CONTRACT_VERSION = "0.1.0"
