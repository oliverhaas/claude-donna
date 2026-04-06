---
name: general-security
description: Essential security practices for all code.
user-invocable: false
---

# Security Essentials

## Secrets

- Never hardcode secrets, API keys, tokens, or passwords in code.
- Never log secrets or include them in error messages or commits.
- Use environment variables or a secrets manager for all credentials.

## Sensitive Files: Do Not Access

- `.env`, `.env.*` (environment secrets)
- `*.pem`, `*.key`, `*.p12` (private keys and certificates)
- `credentials.json`, `serviceAccount.json` (credential files)
- `.ssh/` (SSH keys and config)

## Code Safety

- No `eval()` or `exec()` on untrusted input.
- Be aware of the OWASP Top 10 vulnerabilities.
- Prevent SQL injection: use parameterized queries, never string concatenation.
- Prevent XSS: escape all user-provided content rendered in HTML.
- Prevent command injection: never pass unsanitized input to shell commands.
- Guard against CSRF in forms and state-changing endpoints.

## Data Protection

- Do not process PII/PHI without explicit approval.
- Access only the minimum data necessary for the task.

---
