# PromptRig Product & UX Architecture Independent Review Executive Report

## 1. Reviewer Identity & Specialist Mandate

- **Reviewer Identity:** Google Gemini Product & UX Architecture Specialist (`google-gemini`)
- **Model Identifier:** `Gemini 3.5 Flash (High)` (Observed: `gemini-3.5-flash`)
- **Specialist Mandate:** Nontechnical UX, accessibility (WCAG 2.2 AA), information architecture, progressive disclosure, error recovery, user consent boundaries, confidence communication, and Simple Mode vs. Developer Mode state/schema integrity.
- **Corpus Version:** `v0.4` (`promptrig-review-corpus-v0.4.zip`)
- **Corpus SHA-256:** `a0bd3c1a6d91bb2330cd41d8933a723d94fc01ea40cfe824aca707a4666902e2`

---

## 2. Executive Verdict

**Verdict:** `Approve with Conditions`

**Rationale:**  
PromptRig's core vision—compiling plain-language intent into testable, provider-neutral, provider-aware AI systems while maintaining one unified IR model across Simple and Developer modes—is product-sound and architecturally well-conceived. However, material UX contradictions, schema-to-intake misalignments, missing nontechnical data lowering specifications, and unadjudicated consent boundaries for external tools exist in the current v0.4 candidate specification. These issues threaten nontechnical user comprehension, accessibility compliance (WCAG 2.2 AA), and safe system operation. Architecture freeze must be conditioned on resolving the four High-severity findings identified below.

---

## 3. Blocking Findings (High Severity)

### [REV-GEMINI-HIGH-001] Contradiction between UX intake mode options ("Flexible/Balanced/Strict") and canonical IR schema `project.mode` enum ("balanced/creative/enterprise")
- **Affected Sources:** [`04-specification/UX_SPEC.md#L31`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L31), [`schemas/PROMPTRIG_IR.schema.json#L31-L37`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L31-L37), [`01-vision/PROMPTRIG_MASTER_SCOPE.md#L54-L59`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/01-vision/PROMPTRIG_MASTER_SCOPE.md#L54-L59)
- **Finding:** The UX Intake specification defines precision/rigor options as `"Flexible / Balanced / Strict"` ([`UX_SPEC.md:L31`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L31)), whereas [`PROMPTRIG_IR.schema.json`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L31-L37) restricts `project.mode` strictly to `["balanced", "creative", "enterprise"]`, and [`PROMPTRIG_MASTER_SCOPE.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/01-vision/PROMPTRIG_MASTER_SCOPE.md#L54-L59) lists `Balanced`, `Creative`, `Enterprise`. Because Simple Mode intake maps nontechnical choices directly into canonical IR, a user selection of "Flexible" or "Strict" in the UI will fail JSON Schema validation against the canonical IR schema.
- **Impact:** System failure during intake serialization for nontechnical users selecting valid UI options.

### [REV-GEMINI-HIGH-002] Absence of nontechnical data representation specification for complex JSON Schemas (`input_contracts` / `output_contracts`) in Simple Mode
- **Affected Sources:** [`04-specification/UX_SPEC.md#L35-L45`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L35-L45), [`04-specification/ACCEPTANCE_CRITERIA.md#L51`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/ACCEPTANCE_CRITERIA.md#L51), [`schemas/PROMPTRIG_IR.schema.json#L82-L93`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L82-L93)
- **Finding:** Acceptance criteria mandate that *"No developer terminology is required to finish [Simple Mode] flow"* ([`ACCEPTANCE_CRITERIA.md:L51`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/ACCEPTANCE_CRITERIA.md#L51)). However, [`UX_SPEC.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L41) requires displaying *"What it will accept and produce"* in the Compilation Summary without specifying how complex structured JSON Schemas (defined in IR `input_contracts` and `output_contracts`) are lowered into nontechnical, plain-language visual summaries.
- **Impact:** Risk of developer terminology and raw JSON leaking into Simple Mode, confusing nontechnical users.

### [REV-GEMINI-HIGH-003] Missing UI interaction contract and consent boundary for external tool actions in Interactive Sample Runner ("Try It")
- **Affected Sources:** [`04-specification/UX_SPEC.md#L15`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L15), [`04-specification/UX_SPEC.md#L84`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L84), [`01-vision/PRODUCT_CONSTITUTION.md#L26`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/01-vision/PRODUCT_CONSTITUTION.md#L26), [`07-verification/SECURITY_THREAT_MODEL.md#L50-L54`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/07-verification/SECURITY_THREAT_MODEL.md#L50-L54)
- **Finding:** Product Constitution and Security Threat Model mandate that consequential external actions require explicit user approval at the action boundary. However, [`UX_SPEC.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L84) Screen 9 ("Interactive sample runner / Try It") fails to specify the UX interaction contract, modal dialogs, or confirmation UI for intercepting, previewing, and approving tool executions during sample interactions.
- **Impact:** Potential execution of side-effecting tools during testing without user consent, or broken execution flows.

### [REV-GEMINI-HIGH-004] Contradiction between schema constraint and specification for evaluation `repair_limit` maximum bounds
- **Affected Sources:** [`schemas/PROMPTRIG_IR.schema.json#L162-L165`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L162-L165), [`01-vision/PROMPTRIG_MASTER_SCOPE.md#L105`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/01-vision/PROMPTRIG_MASTER_SCOPE.md#L105), [`04-specification/ACCEPTANCE_CRITERIA.md#L60`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/ACCEPTANCE_CRITERIA.md#L60)
- **Finding:** [`PROMPTRIG_IR.schema.json`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L162-L165) sets `"maximum": 5` for `evaluation.repair_limit`. However, [`PROMPTRIG_MASTER_SCOPE.md:L105`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/01-vision/PROMPTRIG_MASTER_SCOPE.md#L105) explicitly defines repair limit as *"configurable to zero through two"*, and [`ACCEPTANCE_CRITERIA.md:L60`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/ACCEPTANCE_CRITERIA.md#L60) states *"configure zero to two repair passes"*.
- **Impact:** Validation disparity between developer IR edits and compiler enforcement.

---

## 4. Nonblocking Findings (Medium & Low Severity)

- **[REV-GEMINI-MEDIUM-005] Lack of nontechnical error recovery and plain-language troubleshooting guidance when bounded repair fails** ([`UX_SPEC.md#L47-L56`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L47-L56)): No plain-language troubleshooting guidance for nontechnical users when repair loops terminate with unresolved defects.
- **[REV-GEMINI-MEDIUM-006] Missing screen reader live-region accessibility specifications for asynchronous compilation and evaluation progress** ([`UX_SPEC.md#L89-L105`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L89-L105)): Lacks WAI-ARIA `aria-live` and role requirements for screen reader updates during long-running compilation stages.
- **[REV-GEMINI-MEDIUM-007] Ambiguity in communicating model-graded evaluation confidence vs deterministic test pass rates in Simple Mode** ([`UX_SPEC.md#L55`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L55)): Simple Mode results lack distinct visual representation separating hard deterministic test passes from probabilistic LLM judge confidence scores.
- **[REV-GEMINI-LOW-008] Undefined UI mechanism for disclosing and adjusting automatically selected Compilation Level in Simple Mode** ([`UX_SPEC.md#L35-L45`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L35-L45)): No plain-language UI component for displaying or overriding the auto-selected compilation level in Simple Mode.

---

## 5. Contradictions Identified

1. **Intake Rigor Vocabulary Contradiction:** [`UX_SPEC.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L31) specifies `"Flexible / Balanced / Strict"`, whereas [`PROMPTRIG_IR.schema.json`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L31-L37) restricts `project.mode` to `["balanced", "creative", "enterprise"]`.
2. **Repair Limit Upper Bound Contradiction:** [`PROMPTRIG_IR.schema.json`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/schemas/PROMPTRIG_IR.schema.json#L162-L165) sets `repair_limit` max to `5`, whereas [`PROMPTRIG_MASTER_SCOPE.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/01-vision/PROMPTRIG_MASTER_SCOPE.md#L105) and [`ACCEPTANCE_CRITERIA.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/ACCEPTANCE_CRITERIA.md#L60) cap it at `2`.

---

## 6. Missing Evidence & Specifications

1. **Natural-Language Schema Lowering:** Missing specification for converting JSON Schema contracts into plain-language representations for Simple Mode users.
2. **WAI-ARIA Dynamic Region Guidelines:** Missing explicit `aria-live` polite/assertive regions and focus management specifications for dynamic compilation updates in [`UX_SPEC.md`](file:///c:/Users/alkur/Downloads/promptrig-review-launch-v0.4/04-specification/UX_SPEC.md#L89-L105).
3. **Action Consent UI Specifications:** Missing UI wireframe/contract for intercepting tool execution calls in Interactive Sample Runner ("Try It").

---

## 7. Assumptions Rejected

1. **Rejected Assumption:** Nontechnical users can intuitively differentiate between hard deterministic schema validation passes and subjective LLM-graded evaluation scores without explicit dual-indicator UI design.
2. **Rejected Assumption:** Raw JSON Schema definitions in IR input/output contracts can be rendered in Simple Mode without a dedicated lowering transform.

---

## 8. Proposed ADR / RFC / Schema Changes

1. **`schemas/PROMPTRIG_IR.schema.json`:**
   - Update `evaluation.repair_limit.maximum` from `5` to `2` to align with Master Scope.
   - Update `project.mode` enum to support both intake modes and system modes, or establish an explicit mapping schema in RFC-001.
2. **`04-specification/UX_SPEC.md`:**
   - Add Screen 9 tool-call consent boundary specification (Action Consent Modal/Card).
   - Add WAI-ARIA live region requirements (`aria-live="polite"` / `role="status"`) for Screen 6 (Compilation Progress).
   - Add "Schema Humanizer" requirement for Compilation Summary.
   - Add dual-indicator display requirement for Result Summary (Deterministic Pass vs LLM Judgment Confidence).

---

## 9. Validation Plan

1. **Automated Schema & Contract Testing:** Run schema validation tests on all intake-generated IR instances across all selectable intake options.
2. **Accessibility Audit:** Execute automated axe-core scans and manual screen-reader traversals (NVDA/VoiceOver) across all 12 required UX screens.
3. **Nontechnical Comprehension Benchmark:** Test 20 nontechnical users on intake, compilation summary review, and sample runner interactions to verify >=80% task completion without developer intervention.

---

## 10. Residual Risks & Confidence

- **Residual Risk:** Nontechnical users may still over-rely on probabilistic AI suggestions if LLM judge uncertainty is not visually prominent.
- **Confidence Level:** `0.95` (Very High confidence based on complete canonical corpus inspection and strict spec traceability).
