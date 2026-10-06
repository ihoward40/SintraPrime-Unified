# Agent Control Surface — Relay Protocol

> **Status:** client + protocol specification only. No relay server implementation
> ships in this branch; the server is a small companion service to be built
> later against this spec.
>
> **Attribution:** the architecture pattern (a relay server running on the
> operator's machine + a mobile app acting as a remote control to start and
> monitor agent tasks) is inspired by
> [pingdotgg/t3code](https://github.com/pingdotgg/t3code), which is MIT
> licensed. This specification and the `mobile/src/control/` client are
> original implementations of that pattern for SintraPrime — no t3code code
> was copied. The MIT license notice is preserved in the header of every new
> source file under `mobile/src/control/` and `mobile/src/navigation/ControlStack.tsx`.

## 1. Architecture

```
┌──────────────┐      HTTPS/WSS       ┌──────────────┐      local IPC / PTY
│  Mobile app  │ ◄──────────────────► │ Relay server │ ◄──────────────────► │ Agents
│ (this client)│  REST + WebSocket    │ (operator's  │                      │ (shell /
└──────────────┘                      │  machine)    │                      │  workers)
                                      └──────────────┘
```

- The **relay server** runs on the operator's own machine (laptop, workstation,
  home server). It is the only component that can spawn or signal agent
  processes.
- The **mobile app** never talks to agents directly. It talks to the relay
  over REST (commands, queries) and WebSocket (live log/task/roster pushes).
- The relay host is **configuration, not code**: the app reads it from
  Settings (`mobile/src/control/RelaySettingsScreen.tsx`, persisted
  on-device via `relayConfig.ts`). No real host, token, or credential appears
  anywhere in the repository.

## 2. Transport

| Concern | Value |
|---|---|
| Base URL | `http(s)://<host>:<port>` (default port `8080`, configurable) |
| WebSocket URL | `ws(s)://<host>:<port>/ws` |
| Protocol version | `v1` — every REST path is prefixed `/v1` |
| REST auth | `Authorization: Bearer <token>` header |
| WebSocket auth | `?token=<url-encoded token>` query parameter |
| Token model | Pre-shared bearer token configured on the relay and pasted into the app's Relay Settings. Stored on-device only. |
| Unauthorized | `401` with `{ "message": "…" }` JSON body |

TLS is recommended whenever the relay is reachable beyond a trusted LAN
(`useTls` toggle in Relay Settings switches `http`→`https`, `ws`→`wss`).

## 3. REST endpoints

All responses are JSON. Error shape: `{ "message": string, "code"?: string }`.

### `GET /v1/health`
Lightweight reachability check. No auth required (safe to expose for the
app's "Test connection" button).

```json
{ "ok": true, "version": "1.0.0" }
```

### `GET /v1/agents`
List agents known to the relay.

```json
{
  "agents": [
    {
      "id": "agent-macbook",
      "name": "MacBook Pro",
      "host": "macbook-pro.local",
      "status": "online",
      "lastSeen": "2026-10-06T09:04:44.000Z",
      "currentTaskId": "task_01J...",
      "capabilities": ["shell", "code"]
    }
  ]
}
```

`status` is one of `online | busy | offline | unknown`.

### `POST /v1/tasks`
Start a task on an agent.

Request:
```json
{
  "agentId": "agent-macbook",
  "title": "Nightly evidence sync",
  "prompt": "Run the evidence sync and report failures",
  "command": "npm run sync:evidence"
}
```
`prompt` and `command` are alternatives — at least one is required.
`title` is required.

Response `201`:
```json
{ "task": { "id": "task_01J...", "agentId": "agent-macbook", "title": "…",
            "status": "queued", "createdAt": "…", "updatedAt": "…" } }
```

### `GET /v1/tasks/:taskId`
Fetch one task → `{ "task": { … } }`. `404` when unknown.

`status` is one of `queued | running | paused | completed | failed | stopped`.
Terminal states (`completed | failed | stopped`) may carry `exitCode` and a
human-readable `message`.

### `POST /v1/tasks/:taskId/stop`
Request a running/queued task to stop (graceful first, then SIGKILL after a
server-defined grace period). Response → `{ "task": { …updated… } }`.
`409` if the task is already terminal.

### `GET /v1/tasks/:taskId/logs?after=<seq>&limit=<n>`
Buffered log history for a task. `after` is an exclusive sequence number;
omit it for the oldest page. Default `limit` is server-defined (suggested 500,
max 2000).

```json
{
  "logs": [
    { "taskId": "task_01J...", "seq": 41, "ts": "2026-10-06T09:05:01.000Z",
      "level": "info", "stream": "stdout", "text": "sync complete: 12 files" }
  ],
  "nextSeq": 42
}
```
`level`: `debug | info | warn | error`. `stream`: `stdout | stderr | system`.

## 4. WebSocket messages

JSON frames, newline-free. The client sends a `ping` every 25 s; the server
replies `pong`. The client auto-reconnects with exponential backoff
(1 s → 30 s cap) and re-subscribes after reconnect.

### Client → server

| `type` | Shape | Purpose |
|---|---|---|
| `ping` | `{ "type": "ping", "ts": "<iso>" }` | heartbeat |
| `subscribe` | `{ "type": "subscribe", "channel": "task:<id>:logs" }` | live logs for a task |
| `unsubscribe` | `{ "type": "unsubscribe", "channel": "task:<id>:logs" }` | stop live logs |

### Server → client

| `type` | Shape | Purpose |
|---|---|---|
| `welcome` | `{ "type": "welcome", "protocol": "v1", "serverTime": "<iso>" }` | sent on connect |
| `pong` | `{ "type": "pong", "ts": "<iso>" }` | heartbeat reply |
| `log` | `{ "type": "log", "event": { …LogEvent… } }` | one log line, only to subscribers of that task's channel |
| `task` | `{ "type": "task", "task": { …AgentTask… } }` | task lifecycle transition, broadcast |
| `agents` | `{ "type": "agents", "agents": [ … ] }` | roster change, broadcast |
| `error` | `{ "type": "error", "message": "…", "code"?: "…" }` | e.g. bad subscribe, unknown channel |

The `LogEvent` and `AgentTask` shapes are identical to the REST versions —
see `mobile/src/control/types.ts`, the canonical TypeScript source of truth.

## 5. Client implementation (this branch)

`mobile/src/control/`:

| File | Role |
|---|---|
| `types.ts` | `Agent`, `AgentTask`, `LogEvent`, `RelayConfig`, `ControlStackParamList`, … |
| `relayConfig.ts` | Load/save relay settings (AsyncStorage when available, memory fallback). Never hardcodes a host. |
| `relayClient.ts` | `RelayClient` — typed REST methods (`listAgents`, `getTask`, `startTask`, `stopTask`, `getLogs`/`streamLogs` via `subscribeLogs`), WebSocket connect/disconnect with backoff, heartbeat, re-subscribe. `getRelayClient()` shared singleton; `resetRelayClient()` after settings change. |
| `AgentListScreen.tsx` | Agent roster with status, pull-to-refresh, per-agent *Start task* / *View current task*. |
| `TaskDetailScreen.tsx` | Task creation form (title + prompt/command), task detail with status pill, **Stop** for running tasks, and a live auto-scrolling log view (history via REST, then WebSocket stream, deduped by `seq`). |
| `RelaySettingsScreen.tsx` | Host / port / TLS / token editing with a *Test connection* button. |
| `index.ts` | Barrel exports. |

`mobile/src/navigation/ControlStack.tsx` registers the three screens in a
native stack following the existing `*Stack.tsx` convention. Wire it into
`RootNavigator.tsx` / `MainTabs.tsx` and (optionally) `navigation/types.ts`
when integrating.

## 6. Security notes

- The relay binds to the operator's machine; expose it beyond localhost only
  behind TLS and a strong pre-shared token.
- Tokens are entered in the app's Settings and stored on-device only. They
  must never be committed, logged, or embedded in build config.
- `startTask` executes arbitrary commands/prompts on the operator's machine —
  treat the relay token with the same care as SSH credentials. A future relay
  may add per-command allowlists; the protocol already carries `command`
  separately from `prompt` so the server can policy on it.
- Log streams may contain sensitive output; the app does not persist logs
  beyond the in-memory view.

## 7. Future work (out of scope for this branch)

- Reference relay server implementation (Node/Bun) against this spec.
- Push notifications for task completion/failure.
- Per-agent task history (`GET /v1/agents/:id/tasks`).
- Command allowlist / approval flow on the relay for `startTask`.
