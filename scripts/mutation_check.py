"""Targeted mutation checks on the trust boundaries.

Each mutation disables one safeguard; the named tests must then fail. Files are
restored after every mutation (in a finally block). Run from the repo root with a
clean working tree:  python scripts/mutation_check.py   (about two minutes; not run in CI).
"""
import subprocess
import sys
from pathlib import Path

MUTATIONS = [
    ("coverage check removed", "src/proofhouse/compiler/eval_product.py",
     'if common["requirement_coverage"]["missing"]:', "if False:",
     ["tests/compiler/test_t03_eval_integrity.py"]),
    ("duplicate case_id check removed", "src/proofhouse/compiler/eval_dataset.py",
     "if case.case_id in seen:", "if False:",
     ["tests/compiler/test_t03_eval_integrity.py"]),
    ("duplicate scores overwrite (string keys)", "src/proofhouse/compiler/eval_product.py",
     "merged[(case.case_id, criterion_id)] = value", 'merged[f"{case.case_id}:{criterion_id}"] = value',
     ["tests/compiler/test_t03_eval_integrity.py"]),
    ("revision digest comparison bypassed", "src/proofhouse/optimize/case.py",
     "if actual != revision.sha256:", "if False:",
     ["tests/optimize/test_t04_revision_integrity.py"]),
    ("verdict digest binding bypassed", "src/proofhouse/optimize/checks.py",
     "            return (item[\"result\"], False) if bound else (None, True)",
     "            return (item[\"result\"], False)",
     ["tests/optimize/test_t04_revision_integrity.py"]),
    ("constraints ignored by overall", "src/proofhouse/optimize/checks.py",
     'and all(c["status"] == "satisfied" for c in constraint_rows)', "",
     ["tests/optimize/test_t09_t12_workflow.py"]),
    ("run output digest bypassed", "src/proofhouse/optimize/workflow.py",
     'if sha256_text(text) != record.get("output_sha256"):', "if False:",
     ["tests/optimize/test_t09_t12_workflow.py"]),
    ("import digest check bypassed", "src/proofhouse/optimize/workflow.py",
     "if hashlib.sha256(blob).hexdigest() != expected:", "if False:",
     ["tests/optimize/test_t09_t12_workflow.py"]),
    ("requirements dropped from live request", "src/proofhouse/compiler/runtime_context.py",
     'section("Requirements", requirement_lines)', "pass",
     ["tests/compiler/test_t02_runtime_semantics.py"]),
    ("unsupported semantics not blocked", "src/proofhouse/compiler/execution.py",
     "    if runtime.unsupported:\n", "    if False:\n",
     ["tests/compiler/test_t02_runtime_semantics.py"]),
    ("install verifies after swap (old behavior)", "src/proofhouse/optimize/install_skill.py",
     "                verify_skill_md(staged / SKILL_FILE)\n", "                pass\n",
     ["tests/optimize/test_t06_install_transaction.py"]),
    ("notes file labeled researched again", "src/proofhouse/optimize/case.py",
     "        source=SOURCE_USER_SUPPLIED,\n", '        source="researched",\n',
     ["tests/optimize/test_t07_notes_provenance.py"]),
    ("intake shape validation skipped", "src/proofhouse/compiler/closed_loop.py",
     "    if shape_errors:\n", "    if False:\n",
     ["tests/compiler/test_t01_intake_validation.py"]),
    ("repair-unsupported terminal reason dropped", "src/proofhouse/compiler/closed_loop.py",
     "                            extra_diagnostics.append(REPAIR_UNSUPPORTED)\n", "                            pass\n",
     ["tests/compiler/test_t03_eval_integrity.py"]),
    ("hidden answers reach compilation (artifact)", "apps/proofhouse.jsx",
     "if (isVisible(q, answers, byId) && hasAnswer(answers[q.id])) out[q.id] = answers[q.id];",
     "if (hasAnswer(answers[q.id])) out[q.id] = answers[q.id];",
     ["tests/test_artifact_validators.py::test_hidden_answers_never_reach_compilation"]),
]

results = []
for name, path, old, new, tests in MUTATIONS:
    target = Path(path)
    original = target.read_bytes()
    text = original.decode("utf-8")
    if text.count(old) != 1:
        results.append((name, "MUTATION NOT APPLIED (pattern count %d)" % text.count(old)))
        continue
    target.write_bytes(text.replace(old, new).encode("utf-8"))
    try:
        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", *tests],
                             capture_output=True, text=True, check=False)
        killed = run.returncode != 0
        results.append((name, "killed" if killed else "SURVIVED"))
    finally:
        target.write_bytes(original)

width = max(len(n) for n, _ in results)
for name, outcome in results:
    print(f"{name:<{width}}  {outcome}")
survivors = [n for n, o in results if o != "killed"]
print(f"\n{len(results) - len(survivors)}/{len(results)} mutations killed")
sys.exit(1 if survivors else 0)
