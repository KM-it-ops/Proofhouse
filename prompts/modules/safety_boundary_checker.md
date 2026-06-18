# Module — Safety Boundary Checker

Use this module before finalizing prompts involving sensitive domains.

## Check

- Does the prompt involve cybersecurity, automation, credentials, scraping, malware, exploit research, personal data, legal, medical, or financial matters?
- Does it require authorization?
- Could it enable harm if misused?
- Are refusal and redirection rules clear?
- Are privacy requirements clear?

## Output

| Risk | Present? | Required Boundary | Prompt Fix |
|---|---:|---|---|
