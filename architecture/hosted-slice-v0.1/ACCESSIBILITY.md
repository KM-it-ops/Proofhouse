# Accessibility, consent, and presentation

**Status:** Contract only. No UI is implemented.

## Requirements that the future UI must meet

- Simple Mode copy does not require compiler vocabulary. Developer Mode may show IR, traces, diagnostics, cost, latency, and evidence.
- Uncertainty, PARTIAL compiles, and unresolved defects are visible in both modes. They are never restated as SUCCESS.
- Consent and cost/latency figures, when shown, come from compiler evidence, not from invented UI meters.
- Keyboard access, labels, and contrast are gates before any closed-alpha UI is Accepted.
- Empty project state is explicit in both modes (`fixtures/empty_project.json`).

Nontechnical usability evidence is required at implementation time. This package does not claim that evidence exists.
