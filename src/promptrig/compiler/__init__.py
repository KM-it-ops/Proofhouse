"""PromptRig Compiler Core v0.1 — deterministic, offline IR compiler.

Public library surface lives in `promptrig.compiler.api`. This package
contains no live provider calls, network access, or credential handling
(see architecture/compiler-contract-freeze-v0.5/).
"""
from __future__ import annotations

COMPILER_ID = "promptrig-compiler-core"
COMPILER_VERSION = "0.1.0"
IR_CONTRACT_VERSION = "0.1.0"
