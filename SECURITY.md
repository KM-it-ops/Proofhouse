# Security Policy

Proofhouse is a local prompt-operations tool. It should not contain secrets, API keys, account tokens, private data, or provider credentials.

## Supported Scope

Security, automation, scraping, credentials, exploit research, malware analysis, and sensitive-data workflows must stay defensive, authorized, educational, privacy-preserving, and compliance-oriented.

Reports are welcome for the Python package and CLIs, the skill bundle and installer, the artifact (`apps/proofhouse.jsx`), eval data, and documentation. The experimental `hosted-*` slices have no tenant isolation by design and must not be exposed over a network; a report that they are not isolated is expected behavior, not a vulnerability.

## Reporting

Report privately, not in a public issue:

1. **GitHub private vulnerability reporting:** on the repository's **Security** tab, choose **Report a vulnerability**.
2. **If that button is not shown:** open a public issue titled `Security contact request` with **no details**, and the maintainer will arrange a private channel.

Do not include live secrets or sensitive third-party data in any report. Expect an acknowledgement within 7 days. This is a single-maintainer project; there is no bug bounty.

## Maintainer Checklist

- Keep `.env`, keys, tokens, and local auth files out of Git.
- Prefer synthetic eval data.
- Redact sensitive examples before adding them to `evals/datasets/`.
- Keep provider integrations optional until their credential handling is explicitly designed.
