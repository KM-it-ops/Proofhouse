# Security Policy

PromptRig is a prompt-operations framework. It should not contain secrets, API keys, account tokens, private data, or provider credentials.

## Supported Scope

Security, automation, scraping, credentials, exploit research, malware analysis, and sensitive-data workflows must stay defensive, authorized, educational, privacy-preserving, and compliance-oriented.

## Reporting

If you find a security issue in the prompt assets, eval data, CLI behavior, or documentation, open a private report through the repository owner's preferred channel. Do not include live secrets or sensitive third-party data in public issues.

## Maintainer Checklist

- Keep `.env`, keys, tokens, and local auth files out of Git.
- Prefer synthetic eval data.
- Redact sensitive examples before adding them to `evals/datasets/`.
- Keep provider integrations optional until their credential handling is explicitly designed.
