from pathlib import Path

from promptrig.loadouts import compile_loadout, load_legendary_loadouts


def test_legendary_loadouts_have_expected_count():
    loadouts = load_legendary_loadouts()
    assert len(loadouts) == 5
    assert {loadout.id for loadout in loadouts} == {
        "ghost-architect",
        "gunsmith-rewriter",
        "firing-range-evaluator",
        "overwatch-agent",
        "blackbox-sentinel",
    }


def test_loadout_source_paths_exist():
    root = Path(__file__).resolve().parents[1]
    for loadout in load_legendary_loadouts(root / "loadouts" / "legendary_loadouts.json"):
        source_paths = [loadout.primary, loadout.mode, *loadout.modules, *loadout.eval_packs, *loadout.rubrics]
        for source_path in source_paths:
            assert (root / source_path).exists(), source_path


def test_compile_loadout_includes_mode_and_modules():
    root = Path(__file__).resolve().parents[1]
    compiled = compile_loadout("overwatch-agent", repo_root=root)
    assert "Overwatch Agent" in compiled
    assert "prompts/modes/agentic_mode.md" in compiled
    assert "prompts/modules/safety_boundary_checker.md" in compiled
