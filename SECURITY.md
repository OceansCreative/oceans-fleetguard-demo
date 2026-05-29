# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in FleetGuard, please report it
responsibly:

- **Do not** open a public issue for security-sensitive reports.
- Use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
  on this repository, or contact a maintainer privately.

Please include steps to reproduce, affected versions, and any relevant logs
(with secrets redacted).

## Handling secrets

FleetGuard never stores credentials in the repository. All secrets are provided
at runtime via environment variables (`.env`, git-ignored) or GitHub Secrets.
If you believe a secret was committed by mistake, report it immediately so it
can be rotated and purged from history.

## Supported versions

This project is in early development; only the latest `main` is supported.
