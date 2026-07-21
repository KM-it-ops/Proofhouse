# PromptRig UX Specification

## Design goal

Make AI-system engineering feel like describing a goal to a capable professional. Technical machinery remains available but never blocks ordinary users.

## Information architecture

- Home
- Projects
- New Project
- Project Overview
- Build
- Test Results
- Try It
- Versions
- Export
- Settings

## Simple Mode

### New-project intake

Primary question: **What would you like AI to help you accomplish?**

Optional plain-language fields:

- Who will use it?
- What information will it work with?
- What should it produce or do?
- How careful should it be? Flexible / Balanced / Strict

PromptRig may ask no more than three questions in one clarification round. It proceeds with labeled assumptions unless missing information is truly blocking or consequential.

### Compilation summary

Display:

- What PromptRig understood
- Who the system is for
- What it will accept and produce
- Important assumptions
- Recommended provider and why
- Actions requiring user confirmation

### Results

Use human-language status:

- Ready
- Ready with cautions
- Needs attention
- Could not complete

Display test summary, unresolved risks, sample use, and download action. Do not describe a model-graded result as proof of correctness.

## Developer Mode

Developer Mode is a toggle in project settings and project headers. It reveals:

- IR editor with schema validation
- provider and model configuration
- capability resolution
- generated prompts and instructions
- tool manifests
- structured-output schemas
- memory/retrieval settings
- evaluation dataset and rubric
- traces, tokens, latency, and cost
- artifact manifest and raw export

Changes made in either mode update one versioned project state.

## Required screens

1. marketing/landing placeholder
2. authentication
3. project list
4. new-project intake
5. requirements review
6. compilation progress
7. result summary
8. evaluation detail
9. interactive sample runner
10. version history and diff
11. export center
12. credentials/settings

## State requirements

Every asynchronous operation exposes:

- queued
- running
- completed
- completed with warnings
- failed
- canceled

Progress messaging must describe the current stage without exposing hidden reasoning.

## Accessibility

Target WCAG 2.2 AA for customer-facing flows. Include keyboard operation, visible focus, semantic landmarks, sufficient contrast, descriptive errors, and reduced-motion support.

## Tone

Clear, confident, non-patronizing, and honest. Avoid claims such as flawless, guaranteed, perfect, or optimal.
