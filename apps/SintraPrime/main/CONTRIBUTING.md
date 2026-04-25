# Contributing to SintraPrime

Thank you for your interest in contributing to SintraPrime, the institution-grade governance OS for AI agents. Whether you are fixing a bug, improving documentation, or proposing a new feature, your contributions are valued and appreciated.

This guide outlines the process for contributing to the project and the standards we expect all contributions to meet. Following these guidelines helps maintain the quality and integrity of the codebase and ensures a smooth experience for everyone involved.

## Table of Contents

- [AI-Assisted Pull Requests (Strict Review)](#ai-assisted-pull-requests-strict-review)
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Branch Naming Conventions](#branch-naming-conventions)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Code Style & Standards](#code-style--standards)
- [Governance Compliance](#governance-compliance)
- [License](#license)

## AI-Assisted Pull Requests (Strict Review)

This repository uses a strict review workflow. Automation, including AI agents, may assist with pull requests, but humans are responsible for final approval and merges.

### Branch Protection Expectations

Contributors should expect the following branch protection rules when proposing changes to `master`:

- pull requests are required for merges to `master`
- required CI checks must pass before merge
- at least one human approval is required, per branch protection settings
- changes under `.github/workflows/` require CODEOWNERS review

### What AI agents may do

AI agents and automation may:
- open or update pull requests, including dependency updates
- generate Review Packs, including change summaries, risk notes, and suggested tests
- monitor CI results and summarize failures

### What AI agents may not do

AI agents and automation must not:
- self-approve pull requests
- merge pull requests without human oversight
- bypass required checks or branch protection rules

### Merge requirements

A pull request may be merged only when:
- required CI checks are passing
- required conversations are resolved when applicable
- at least the required number of human approvals is present, per branch protection settings

### Notes on Review Packs

The Review Pack is intended to reduce review overhead and highlight risk areas. It is advisory and does not replace human review.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. We are committed to providing a welcoming and inclusive experience for everyone. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** >= 20.x
- **npm** >= 10.x
- **Git**
- **Docker & Docker Compose** (for full-stack testing)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub by clicking the "Fork" button at the top of the [SintraPrime repository](https://github.com/ihoward40/SintraPrime).

2. **Clone your fork** to your local machine:

   ```bash
   git clone https://github.com/<your-username>/SintraPrime.git
   cd SintraPrime
   ```

3. **Add the upstream remote** to keep your fork in sync:

   ```bash
   git remote add upstream https://github.com/ihoward40/SintraPrime.git
   ```

4. **Install dependencies:**

   ```bash
   npm install
   ```

5. **Copy the environment file and configure it:**

   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

6. **Verify your setup** by running the build and tests:

   ```bash
   npm run build
   npm test
   ```

## How to Contribute

We welcome contributions in the following areas:

- **Bug Reports:** Open an issue with a clear description, steps to reproduce, and expected vs. actual behavior.
- **Feature Requests:** Open an issue describing the feature, its use case, and how it aligns with SintraPrime's governance-first architecture.
- **Code Contributions:** Submit a pull request for bug fixes, new features, or improvements.
- **Documentation:** Improve existing documentation or add new guides, tutorials, and examples.
- **Testing:** Add or improve unit tests, integration tests, and smoke tests.

If you are unsure where to start, look for issues labeled `good first issue` or `help wanted`.

## Branch Naming Conventions

All branches must follow a consistent naming convention. This ensures clarity and makes it easy to understand the purpose of each branch at a glance.

| Prefix | Purpose | Example |
| :--- | :--- | :--- |
| `feat/` | New features or capabilities | `feat/add-slack-adapter` |
| `fix/` | Bug fixes | `fix/receipt-signature-validation` |
| `docs/` | Documentation changes | `docs/update-api-reference` |
| `chore/` | Maintenance, refactoring, CI/CD | `chore/upgrade-typescript-5.8` |
| `test/` | Adding or improving tests | `test/add-workflow-runner-tests` |
| `security/` | Security patches and hardening | `security/patch-minimatch-redos` |

Always branch from the latest `master` branch:

```bash
git checkout master
git pull upstream master
git checkout -b feat/your-feature-name
```

## Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. This enables automated changelog generation and makes the commit history easy to read.

**Format:**

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**

| Type | Description |
| :--- | :--- |
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `chore` | Changes to the build process or auxiliary tools |
| `test` | Adding missing tests or correcting existing tests |
| `refactor` | A code change that neither fixes a bug nor adds a feature |
| `security` | A security-related change |
| `ci` | Changes to CI configuration files and scripts |

**Examples:**

```
feat(browser): add governed browser operator with Ajv2020 compile gate
fix(receipts): enforce receipt_id filenames for ledger consistency
docs(governance): update mode governance release notes to v1.1
chore(deps): bump express from 4.21.2 to 5.2.1
```

## Pull Request Process

1. **Ensure your branch is up to date** with the latest `master`:

   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Run all checks locally** before submitting:

   ```bash
   npm run typecheck
   npm run build
   npm test
   ```

3. **Open a Pull Request** against the `master` branch of the upstream repository.

4. **Fill out the PR template** completely, including:
   - A clear description of the changes
   - The issue number(s) being addressed (e.g., `Closes #42`)
   - A summary of testing performed
   - Any breaking changes

5. **Respond to review feedback** promptly and constructively.

6. **CI checks must pass.** All automated checks (TypeScript type checking, build verification, schema validation, and security audits) must pass before a PR can be merged.

7. **Approval required.** At least one maintainer must approve the PR before it can be merged.

8. **Branch cleanup.** After your PR is merged, delete the feature branch both locally and on your fork to keep the repository clean.

## Code Style & Standards

SintraPrime is a TypeScript-first project. All new code must be written in TypeScript.

- **Language:** TypeScript (strict mode). No new JavaScript files.
- **Formatting:** Use Prettier with the project's default configuration.
- **Linting:** All code must pass ESLint checks.
- **Type Safety:** Use explicit types. Avoid `any` unless absolutely necessary and documented.
- **File Organization:** Follow the existing directory structure. Place adapters in `agents/`, governance logic in `governance/`, and scripts in `scripts/`.
- **Testing:** All new features and bug fixes should include corresponding tests. Use the existing test infrastructure in `tests/`.

## Governance Compliance

SintraPrime is a governance-first platform. All contributions must respect the project's governance model:

- **Receipt Generation:** Any new adapter or tool integration must generate signed receipts for all actions.
- **Policy Gates:** New features that involve external API calls or resource consumption must integrate with the existing policy gate system.
- **Mode Governance:** Respect the `READ_ONLY`, `SINGLE_RUN_APPROVED`, and `FROZEN` mode constraints.
- **AGENTS.md Constitution:** All agent behavior must comply with the fail-closed constitution defined in `AGENTS.md`.

If you are unsure whether your contribution meets these requirements, please open an issue or ask in the community Discord before submitting a PR.

## License

SintraPrime is licensed under the [Apache License 2.0](LICENSE). By contributing to this project, you agree that your contributions will be licensed under the same license.

---

Thank you for helping make SintraPrime better. We look forward to your contributions.
