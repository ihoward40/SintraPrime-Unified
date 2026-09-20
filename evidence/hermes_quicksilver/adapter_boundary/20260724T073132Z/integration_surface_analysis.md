# Hermes Integration Surface Analysis

## Candidate Surfaces

### 1. Filesystem read-only adapter
Read `~/.hermes/profiles/<name>/profile.yaml` and `config.yaml` directly.

| Criterion | Assessment |
| --------- | ---------- |
| Stability | High; file layout is contract in `hermes_cli/profiles.py` |
| Authentication | N/A (local filesystem) |
| Supported version | 0.18.2 source tree layout |
| Failure behavior | File missing → profile not listed |
| Timeout | N/A |
| Read-only | Yes |
| Profile-list operation | Enumerate directories under `~/.hermes/profiles/` |
| Profile-description operation | Parse `profile.yaml` description/description_auto |
| Side effects | None |
| Testability | High; use temporary directory |
| Windows compatibility | Yes |
| Secret exposure risk | `config.yaml` may contain secrets; must not be read wholesale |

### 2. CLI subprocess invocation
Run `hermes profile list --json` / `hermes profile describe <name> --json`.

| Criterion | Assessment |
| --------- | ---------- |
| Stability | Medium; CLI output shape can change |
| Authentication | N/A |
| Supported version | Installed CLI is v0.15.2, 1893 commits behind source |
| Failure behavior | CLI exit code non-zero, stderr |
| Timeout | Requires subprocess timeout |
| Read-only | Yes, if only list/describe commands used |
| Profile-list operation | `hermes profile list --json` |
| Profile-description operation | `hermes profile describe <name> --json` |
| Side effects | Potential profile YAML write on first use; verify |
| Testability | Medium; requires Hermes CLI in PATH |
| Windows compatibility | Yes |
| Secret exposure risk | CLI may emit secrets in describe output; redact |

### 3. Python import of `hermes_cli.profiles`
Import functions from `C:\Users\admin\AppData\Local\hermes\hermes-agent\hermes_cli\profiles.py`.

| Criterion | Assessment |
| --------- | ---------- |
| Stability | Low; internal API, no semver guarantee |
| Authentication | N/A |
| Supported version | 0.18.2 source only |
| Failure behavior | ImportError, internal exceptions |
| Timeout | N/A |
| Read-only | Possible, but module contains write operations |
| Profile-list operation | Use `_get_profile_dirs()` or equivalent |
| Profile-description operation | Parse returned structures |
| Side effects | Easy to accidentally trigger writes |
| Testability | Medium |
| Windows compatibility | Yes |
| Secret exposure risk | High if config loaded |

### 4. Gateway API query
Query the running gateway for profile routes.

| Criterion | Assessment |
| --------- | ---------- |
| Stability | Low; gateway is inbound message router, not a management API for external callers |
| Authentication | Gateway platform tokens required |
| Supported version | Unknown |
| Failure behavior | Network/auth failure |
| Timeout | Required |
| Read-only | No; gateway performs side effects on messages |
| Profile-list operation | Not directly supported |
| Side effects | Risk of message dispatch |
| Testability | Low |
| Secret exposure risk | High (tokens, platform credentials) |

## Recommended Surface

**Filesystem read-only adapter** with optional CLI fallback for profile enumeration.

Rationale: it is the narrowest, most stable, read-only, testable surface and avoids importing Hermes internals or invoking the CLI with its version skew.

## Fallback Surface

**CLI subprocess** only when the profile directory is inaccessible or the CLI version is known to match the source version.
