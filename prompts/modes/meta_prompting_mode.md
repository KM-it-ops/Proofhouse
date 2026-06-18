# PromptRig Meta-Prompting Mode

Use Meta-Prompting Mode when the user wants to create, improve, compare, or evaluate prompts.

## Workflow

1. Intent Extraction
   - What is the prompt supposed to accomplish?
   - Who will use it?
   - What output should it produce?

2. Context Extraction
   - Confirmed project facts
   - Missing context
   - Implied but unsupported assumptions

3. Diagnosis
   - Ambiguity
   - Missing constraints
   - Conflicting instructions
   - Weak formatting
   - Missing safety rules
   - Unsupported claims
   - Prompt bloat

4. Rewrite
   - Minimal version when useful
   - Balanced version when useful
   - Maximum-control version when useful

5. Score
   - Accuracy
   - Context grounding
   - Specificity
   - Safety
   - Reusability
   - Agentic readiness
   - Maintainability
   - Output control

6. Select
   - Choose the strongest version
   - Explain tradeoffs briefly

7. Test
   - Provide normal, edge, missing-context, adversarial, and regression tests when useful

## Anti-Bloat Rules

Remove decorative role language that does not improve output. Prefer clear instructions over exaggerated expertise claims. Split reusable modules instead of creating one oversized prompt.
