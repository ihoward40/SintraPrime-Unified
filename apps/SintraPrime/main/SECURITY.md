# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x  | :white_check_mark: |
| 1.x.x  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in SintraPrime, please report it responsibly. **Do not open a public GitHub issue for security vulnerabilities.**

### How to Report

1. **Email:** Send a detailed report to the repository owner via GitHub's private vulnerability reporting feature, or contact the maintainer directly.
2. **Include:** A description of the vulnerability, steps to reproduce, potential impact, and any suggested fixes.
3. **Response Time:** We aim to acknowledge receipt within 48 hours and provide an initial assessment within 7 business days.

### What to Expect

- We will work with you to understand and validate the vulnerability.
- We will develop and test a fix in a private branch.
- We will release a patch and publicly disclose the vulnerability in a coordinated manner.
- Contributors who responsibly disclose vulnerabilities will be credited in the release notes (unless they prefer to remain anonymous).

## Security Best Practices for Contributors

When contributing to SintraPrime, please follow these security guidelines:

1. **Never commit secrets.** API keys, tokens, passwords, and private keys must never be committed to the repository. Use environment variables and the `.env.example` file as a template.
2. **Validate all inputs.** Any data received from external sources (webhooks, API calls, user input) must be validated and sanitized before processing.
3. **Use parameterized queries.** Never construct database queries using string concatenation.
4. **Follow the principle of least privilege.** Request only the minimum permissions necessary for any operation.
5. **Keep dependencies updated.** Regularly review and merge Dependabot pull requests.
6. **Use the governance layer.** All new adapters and tools must generate signed receipts and pass through PolicyGate checks before executing actions.

## Supply Chain Security

SintraPrime uses the following measures to protect its software supply chain:

- **Dependabot** is configured to automatically scan for and create PRs for vulnerable dependencies.
- **npm audit** is integrated into the CI pipeline and will fail builds with high-severity vulnerabilities.
- **Package lockfiles** (`package-lock.json`) are committed to ensure deterministic dependency installation.
- **Secret scanning** is enabled to prevent accidental credential exposure.
