# CF-1 Capability Matrix

| Capability | CF-1 Status | Notes |
|---|---|---|
| CollaborationChannel | ✅ implemented | 9 channel types, 4 visibilities |
| ChannelMembership | ✅ implemented | HUMAN/AGENT/SERVICE; 6 roles |
| AgentChannelBinding | ✅ implemented | 6 response modes; default MENTION_ONLY |
| Canonical event types | ✅ implemented | 17 events incl. handoff events |
| Event envelope validation | ✅ implemented | structured, classification |
| Event policy engine | ✅ implemented | fail-closed, 10 gates |
| Anti-loop protection | ✅ implemented | causal chains, max_agent_hops=4 |
| Event deduplication | ✅ implemented | consumption keys, re-entry guard |
| Actor allowlist | ✅ implemented | 6 trigger policies |
| Concurrency control | ✅ implemented | max_parallelism, queueing |
| Rate limiting | ✅ implemented | sliding window per agent |
| Budget governor | 🟡 interface | binding budget dict; hard enforcement in Phase 5A runtime |
| Kill switch (tenant) | ✅ implemented | blocks agent activation, humans unaffected |
| Stop control (STOP_AGENT) | ✅ implemented | binding-level stop, persisted |
| Behavior contracts | ✅ implemented | hashed, versioned, authority_class |
| Stable agent identity | ✅ implemented | identity ≠ host |
| Execution host registry | 🟡 interface | model present; scheduler CF-2 |
| Remote execution | 🟡 mocked | in-process; host-independence proven |
| Agent presence | ✅ implemented | 8 operational states, no CoT |
| Activity stream | ✅ implemented | operational status only |
| ChannelBrief | ✅ implemented | mission/rules/do-not-do, versioned |
| Shared artifacts | 🟡 interface | artifact IDs in handoffs/receipts; dir CF-2 |
| AgentHandoff | ✅ implemented | structured, receipts, chain proven |
| Coordinator pattern | ✅ implemented | constrained, no permission grants |
| Execution receipts | ✅ implemented | hash-chained activation receipts |
| Event receipts | ✅ implemented | matched/activated/skipped + reasons |
| Handoff receipts | ✅ implemented | hash-chained |
| Response schemas | 🟡 interface | structured envelope in activation output |
| Threads | 🟡 interface | reply_to/thread_id on ChannelMessage |
| Reactions | 🟡 interface | REACTION_ADDED event; no auto-approval |
| Memory modes | 🟡 interface | NONE/SESSION active; CHANNEL/OMNIBRAIN CF-2 |
| OmniBrain integration | 🟡 interface | candidate path defined, not wired |
| Backend APIs | ✅ implemented | channel/membership/binding/activity/stop |
| Frontend | ❌ deferred | CF-2 (directive §XLIV) |
| PostgreSQL models | ❌ deferred | JSON persistence in CF-1 |
| GOD-1 Council UI | ❌ deferred | future |
