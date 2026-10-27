# ticket-handoff

You are preparing an internal handoff note for the next support agent. Read the ticket thread below and write a note the agent can scan in about 30 seconds and act on. Address the agent, not the customer. Use plain language, short bullets, and only facts supported by the thread. Keep the most recent customer request and the latest confirmed status clear. If earlier messages conflict with later ones, use the latest supported information and flag any unresolved conflict.

Inputs:

- Ticket thread: {{ticket_thread}}
- Customer tier, if supplied: {{customer_tier}}
- Product area, if supplied: {{product_area}}

Output exactly these five Markdown sections, in this order. Use the headings as written, with no title, introduction, closing, or extra sections. Each bullet must be one sentence. Limits include all words in that section.

## Issue
One bullet, at most 30 words: the customer's problem and desired outcome. Include tier or product area only when supplied and useful.

## Current status
One or two bullets, at most 35 words total: what is confirmed now, including any customer-facing commitment actually made.

## Work done
Up to three bullets, at most 45 words total: relevant checks, changes, replies, and their results. If none are recorded, write `- No work recorded.`

## Next action
One or two bullets, at most 35 words total: the specific next check or response for the next agent, with any dependency.

## Open questions
Up to two bullets, at most 25 words total: missing facts needed to proceed. If none, write `- None.`

When a detail is absent, say `not stated` if it matters to the next action; otherwise omit it. Do not guess order numbers, dates, refund amounts or status, deadlines, or promises. Distinguish a customer request from an agent commitment. Do not include payment details, passwords, government IDs, or unrelated personal data, even when they appear in the thread. Do not copy long message excerpts.

Example input:

> Customer: The export button fails on my reports page. Can you send the file?
> Agent: I reproduced the error and sent it to the reports team. I will update you when they respond.
> Customer: It still fails today. I need the report for a meeting.

Example handoff note:

## Issue
- Customer cannot export a report and wants the file for a meeting.

## Current status
- Export still fails according to the customer; the reports team response is not stated.
- Agent promised an update when the team responds.

## Work done
- Prior agent reproduced the error and sent it to the reports team.

## Next action
- Check the reports team's response, then update the customer; ask which report and format they need if a file can be sent.

## Open questions
- Meeting time and required report are not stated.
