# Phase Two — Constraint Audit

**Audit ID:** CA-2026-07-27-01
**Generated:** 2026-07-27T05:24:36.162475+00:00
**Scope:** Live runtime schema after P2.2 migration
**Status:** PASS

---

## Primary Keys

| Table | Column |
|---|---|
| agents | id |
| execution_history | id |
| knowledge_entries | id |
| messages | id |
| sessions | id |
| skills | id |
| swarms | id |
| users | id |

## Foreign Keys

| Table | Column | References | Added/Retained |
|---|---|---|---|
| execution_history | agent_id | agents(id) | Retained |
| execution_history | swarm_id | swarms(id) | Retained |
| sessions | user_id | users(id) | Retained |

## Unique Constraints

| Table | Column(s) |
|---|---|
| knowledge_entries | key |
| sessions | token |
| skills | name |
| users | email |
| users | username |

## CHECK Constraints Added in P2.2

| Table | Constraint | Allowed Values |
|---|---|---|
| agents | ck_agents_status | idle, active, paused, stopped, failed |
| execution_history | ck_execution_history_status | pending, running, completed, failed, cancelled |
| swarms | ck_swarms_status | initializing, active, paused, dissolved, failed |
| messages | ck_messages_priority | LOW, NORMAL, HIGH, URGENT |
| knowledge_entries | ck_knowledge_entries_confidence | 0.0 <= confidence <= 1.0 |

## NOT NULL Columns After P2.2

| Table | NOT NULL Columns |
|---|---|
| agents | id, name, type, status, config, created_at, updated_at |
| execution_history | id, command, status, started_at |
| knowledge_entries | id, key, value, confidence, created_at, updated_at |
| messages | id, type, priority, content, processed, created_at |
| sessions | id, token, expires_at, created_at |
| skills | id, name, parameters, version, enabled, created_at |
| swarms | id, name, type, status, config, agent_ids, created_at, updated_at |
| users | id, username, email, hashed_password, is_active, created_at |

## Indexes Added in P2.2

| Index | Table/Columns |
|---|---|
| idx_messages_sender_id | messages(sender_id) |
| idx_messages_recipient_id | messages(recipient_id) |
| idx_execution_history_agent_id | execution_history(agent_id) |
| idx_execution_history_swarm_id | execution_history(swarm_id) |
| idx_sessions_user_id | sessions(user_id) |
| idx_users_is_active | users(is_active) |
| idx_knowledge_entries_source | knowledge_entries(source) |

## Justification Summary

| Change | Justification |
|---|---|
| CHECK constraints on status/priority/confidence | Application invariants; prevents invalid state values |
| NOT NULL on columns with defaults | Enforces default values explicitly; prevents accidental NULL overrides |
| FK indexes | Improves join/lookup performance and constraint enforcement |
| idx_users_is_active | Common filter for active user lookups |
| idx_knowledge_entries_source | Common source-based filtering |

## Status

All changes are additive and do not break existing data. The single existing user row satisfies all new constraints.
