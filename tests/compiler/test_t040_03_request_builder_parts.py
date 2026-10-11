"""T-040-03: the four request builders as registered parts (MISSION-040 SPEC §2.4).

Each request builder part wraps its compiler adapter unchanged. These are the
part conformance checks for the four of them: an unsupported job is refused,
never handed to another part; output is fingerprinted; ``not_measured`` is
present; the network is off; and the part's output is the adapter's, byte for
byte.
"""
from __future__ import annotations

import hashlib

import pytest

from proofhouse import parts
from proofhouse.compiler.adapters import get_adapter

from .fixtures.ir_fixtures import ir_with_capabilities, minimal_valid_ir

REQUEST_BUILDERS = ("fake", "openai", "anthropic", "gemini")
UNKNOWN_CAPABILITY = "nonexistent.capability@1"


def test_request_builders_are_the_four_adapters_in_registry_order() -> None:
    assert parts.part_ids(parts.ROLE_REQUEST_BUILDER) == REQUEST_BUILDERS


@pytest.mark.parametrize("part_id", REQUEST_BUILDERS)
def test_descriptor_is_the_adapters_own_description(part_id: str, diagnostic_factory) -> None:
    d = parts.get_part(part_id).describe()
    adapter = get_adapter(part_id, diagnostic_factory).describe()
    assert d.role == parts.ROLE_REQUEST_BUILDER
    assert (d.part_id, d.part_version) == (adapter.adapter_id, adapter.adapter_version)
    assert d.manifest_digest == adapter.capability_manifest_digest
    assert d.kinds_in == (f"ir@{adapter.supported_ir_range}",)
    assert d.kinds_out == adapter.artifact_kinds
    assert d.conformance_suite_version == adapter.conformance_suite_version
    assert d.status == parts.RECORDED_STATUS[part_id]
    assert d.reproducibility == parts.DETERMINISTIC
    assert d.network == parts.NETWORK_NONE
    assert d.not_measured


@pytest.mark.parametrize("part_id", REQUEST_BUILDERS)
def test_part_output_is_the_adapters_output_byte_for_byte(part_id: str, diagnostic_factory) -> None:
    ir = minimal_valid_ir()
    adapter = get_adapter(part_id, diagnostic_factory)
    expected = adapter.lower(ir, adapter.check_capabilities(ir))
    part = parts.get_part(part_id)
    request = {"ir": ir, "diagnostics": diagnostic_factory}

    assert part.check(request).answer == parts.SUPPORTED
    result = parts.perform(part, request)

    assert result.status == expected.status == "success"
    assert [(a.kind, a.digest, a.payload, a.media_type) for a in result.artifacts] == [
        (a.name, a.sha256, a.data, a.media_type) for a in expected.artifacts
    ]


@pytest.mark.parametrize("part_id", REQUEST_BUILDERS)
def test_output_is_fingerprinted_with_provenance(part_id: str, diagnostic_factory) -> None:
    part = parts.get_part(part_id)
    d = part.describe()
    result = part.do({"ir": minimal_valid_ir(), "diagnostics": diagnostic_factory})
    assert result.artifacts
    for artifact in result.artifacts:
        assert hashlib.sha256(artifact.payload).hexdigest() == artifact.digest
        assert artifact.provenance == {
            "part_id": d.part_id,
            "part_version": d.part_version,
            "manifest_digest": d.manifest_digest,
        }
    assert result.not_measured == d.not_measured
    assert result.cost is None
    assert result.contract_version == parts.PART_CONTRACT_VERSION


@pytest.mark.parametrize("part_id", REQUEST_BUILDERS)
def test_unsupported_required_capability_is_refused_not_substituted(part_id: str, diagnostic_factory) -> None:
    ir = ir_with_capabilities(required=[UNKNOWN_CAPABILITY])
    part = parts.get_part(part_id)
    request = {"ir": ir, "diagnostics": diagnostic_factory}

    answer = part.check(request)
    assert answer.answer == parts.UNSUPPORTED
    assert any(item["need"] == UNKNOWN_CAPABILITY and item["resolution"] == parts.UNSUPPORTED for item in answer.items)
    with pytest.raises(parts.PartRefusedError, match="no other part was tried"):
        parts.perform(part, request)

    # Asked directly, the part fails with the adapter's coded diagnostic and builds nothing.
    result = part.do(request)
    assert result.status == "failure"
    assert result.artifacts == ()
    assert any(d["code"] == "PRG-CAPABILITY-0001" for d in result.diagnostics)


@pytest.mark.parametrize("part_id", REQUEST_BUILDERS)
def test_unsupported_optional_capability_does_not_block_the_build(part_id: str, diagnostic_factory) -> None:
    request = {"ir": ir_with_capabilities(optional=[UNKNOWN_CAPABILITY]), "diagnostics": diagnostic_factory}
    part = parts.get_part(part_id)
    assert part.check(request).answer == parts.SUPPORTED
    assert parts.perform(part, request).status == "success"
