# Hermes Specialist-to-Profile Contract

## Scope

This contract defines the read-only mapping between a SintraPrime **specialist** and a Hermes **profile**. It is a SintraPrime-owned construct; Hermes has no concept of a specialist.

## Required fields

| Field | Type | Required | Source / justification |
| ----- | ---- | :------: | ---------------------- |
| `specialist_id` | `str` | yes | SintraPrime canonical identifier; no Hermes equivalent |
| `hermes_profile_id` | `str` | yes | Must match Hermes profile ID regex `^[a-z0-9][a-z0-9_-]{0,63}$` from `hermes_cli/profiles.py` |
| `display_name` | `str` | yes | Human-readable label for UI and audit |
| `capabilities` | `list[str]` | yes | Subset of Hermes profile skills / described capability; used for routing sanity checks |
| `allowed_tool_classes` | `list[str]` | yes | Tool categories this specialist may request (e.g., `read`, `search`, `compute`) |
| `prohibited_tool_classes` | `list[str]` | yes | Tool categories explicitly forbidden; hard-deny precedence |
| `risk_ceiling` | `enum` | yes | One of `LOW`, `MEDIUM`, `HIGH`; drives approval tier and cost guard behavior |
| `tenant_scope` | `list[str]` | yes | UUID tenant IDs permitted to use this mapping; empty list means no tenant |
| `enabled` | `bool` | yes | Default `False` for new mappings; feature flag and mapping flag both required |
| `minimum_hermes_version` | `str` | yes | Inclusive minimum Hermes version; checked against `pyproject.toml` version |
| `maximum_hermes_version` | `str \| None` | yes | Inclusive maximum, or `None` for unbounded |
| `metadata_version` | `str` | yes | Schema version of this contract; starts at `1.0.0` |

## Constraints

- `specialist_id` must be unique within the SintraPrime tenant/registry.
- `hermes_profile_id` must refer to an existing Hermes profile directory or CLI-listed profile.
- `allowed_tool_classes` and `prohibited_tool_classes` must not overlap. If they do, the mapping is invalid.
- `tenant_scope` must contain at least one tenant UUID. A mapping with empty tenant scope is invalid.
- `minimum_hermes_version` must be parseable as a PEP 440 version.
- `enabled` defaults to `False`. A disabled mapping causes immediate denial regardless of feature flag.

## Failure behavior (fail-closed)

| Condition | Result |
| --------- | ------ |
| Unknown `specialist_id` | Deny |
| Unknown `hermes_profile_id` | Deny |
| Disabled mapping (`enabled=False`) | Deny |
| Duplicate `specialist_id` registration | Reject registration / deny delegation |
| Tenant not in `tenant_scope` | Deny and audit |
| Hermes version below `minimum_hermes_version` | Deny or safe diagnostic only |
| Hermes version above `maximum_hermes_version` | Deny or safe diagnostic only |
| Overlapping allow/prohibit tool classes | Deny (mapping invalid) |
| Hermes runtime unavailable | Deny |
| Feature flag disabled | Deny without Hermes invocation |

## Determinism

- The registry must be deterministic: same `specialist_id` + `tenant_id` always resolves to the same `hermes_profile_id`.
- Stale registry entries (profile deleted after mapping created) fail closed at resolution time.

## Redaction

- The contract itself contains no secrets.
- Hermes profile directory must not be read for `.env` or `config.yaml` wholesale; only `profile.yaml` description fields and directory existence are inspected.
