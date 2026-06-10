# API Boundaries — Live Connections Map

## Purpose

Document every external system that SintraPrime-Unified connects to, what it's used for, and the capability boundaries for each connection.

**Key principle:** Prompts are not permission layers. Real control comes from what the agent can physically access.

---

## Connection Status Legend

| Icon | Status | Meaning |
|---|---|---|
| 🟢 | Active | Connected and operational |
| 🟡 | Planned | Configured but not yet wired |
| 🔵 | Exploring | Under evaluation |
| ⚪ | Not started | Identified but no work done |

---

## Connections

### 🟢 Gmail
| Field | Value |
|---|---|
| **Purpose** | Receive client intake emails, send dispute letters and case updates |
| **Read scope** | Inbox (intake folder), sent mail (receipts) |
| **Write scope** | Draft only — no auto-send |
| **Boundaries** | External send requires T3 approval. Drafts only without explicit confirmation. |
| **Approval tier** | T2 (read), T3 (send) |

### 🟢 Google Drive
| Field | Value |
|---|---|
| **Purpose** | Store case documents, evidence files, and client records |
| **Read scope** | Designated case folders |
| **Write scope** | Upload to approved folders only |
| **Boundaries** | No delete. No modify existing files without T2 approval. |
| **Approval tier** | T1 (read), T2 (write) |

### 🟢 GitHub
| Field | Value |
|---|---|
| **Purpose** | Repository management, CI/CD, code review |
| **Read scope** | All public repos, SintraPrime-Unified |
| **Write scope** | Branch creation, commits, PRs |
| **Boundaries** | No direct push to main. No merge without passing CI. No deployment without T2. |
| **Approval tier** | T1 (read/inspect), T2 (commit/push/PR), T3 (merge to main) |

### 🟢 Calendar
| Field | Value |
|---|---|
| **Purpose** | Schedule deadlines, court dates, content calendar, and recurring reviews |
| **Read scope** | Primary calendar |
| **Write scope** | Create events only |
| **Boundaries** | No delete or modify existing events. No scheduling without T2. |
| **Approval tier** | T1 (read), T2 (create) |

### 🟢 Slack
| Field | Value |
|---|---|
| **Purpose** | Command center, notifications, status reports |
| **Read scope** | #ike-command-center, DMs |
| **Write scope** | Send messages to authorized channels |
| **Boundaries** | No DMs to third parties. No posting in external channels. |
| **Approval tier** | T1 (read/report), T2 (message) |

### 🟢 Stripe
| Field | Value |
|---|---|
| **Purpose** | Payment processing, billing, invoice tracking |
| **Read scope** | Transaction history, invoice list, customer data |
| **Write scope** | Draft invoices only |
| **Boundaries** | No refunds, no charge processing, no payout changes without T3. |
| **Approval tier** | T1 (read), T3 (write/process) |

### 🟡 Notion
| Field | Value |
|---|---|
| **Purpose** | Knowledge base, project tracking, content planning |
| **Read scope** | Designated workspaces |
| **Write scope** | Add pages to designated databases |
| **Boundaries** | No delete. No restructure without T2. |
| **Approval tier** | T2 |

### 🟡 Website
| Field | Value |
|---|---|
| **Purpose** | Business presence, client intake, service listings |
| **Read scope** | Public pages |
| **Write scope** | Draft content only |
| **Boundaries** | No publish without T3. No DNS, hosting, or infrastructure changes. |
| **Approval tier** | T2 (draft), T3 (publish) |

### 🔵 TikTok
| Field | Value |
|---|---|
| **Purpose** | Content publishing, analytics tracking |
| **Status** | Exploring — API access and auth not yet configured |
| **Boundaries** | Draft content only. No auto-publish. |

### 🔵 YouTube
| Field | Value |
|---|---|
| **Purpose** | Music distribution, content library, analytics |
| **Status** | Exploring — API access and auth not yet configured |
| **Boundaries** | No upload without T3. Metadata drafts only. |

### 🔵 Spotify
| Field | Value |
|---|---|
| **Purpose** | Music distribution tracking, playlist monitoring |
| **Status** | Exploring — API access and auth not yet configured |
| **Boundaries** | Read-only analytics. No playlist modification. |

### ⚪ Credit Monitoring Exports
| Field | Value |
|---|---|
| **Purpose** | Import credit report data for analysis |
| **Status** | Not started — waiting on export format specification |
| **Boundaries** | Read-only import. No dispute filing without T3. |

### ⚪ Court / Public Records
| Field | Value |
|---|---|
| **Purpose** | Docket monitoring, record retrieval, filing deadlines |
| **Status** | Not started — waiting on court system access |
| **Boundaries** | Read-only record retrieval. No e-filing without T3. |

---

## Summary Matrix

| Connection | Status | Read | Write | Draft | Delete | Send |
|---|---|---|---|---|---|---|
| Gmail | 🟢 | ✅ T1 | ✅ T2 | ✅ T1 | ❌ | T3 only |
| Google Drive | 🟢 | ✅ T1 | ✅ T2 | ✅ T1 | ❌ | N/A |
| GitHub | 🟢 | ✅ T1 | ✅ T2 | ✅ T1 | ❌ | N/A |
| Calendar | 🟢 | ✅ T1 | ✅ T2 | ✅ T1 | ❌ | N/A |
| Slack | 🟢 | ✅ T1 | ✅ T2 | ✅ T1 | ❌ | T2 |
| Stripe | 🟢 | ✅ T1 | ❌ | ✅ T2 | ❌ | T3 |
| Notion | 🟡 | ✅ T2 | ✅ T2 | ✅ T2 | ❌ | N/A |
| Website | 🟡 | ✅ T2 | ❌ | ✅ T2 | ❌ | T3 |
| TikTok | 🔵 | Exploring | — | — | — | — |
| YouTube | 🔵 | Exploring | — | — | — | — |
| Spotify | 🔵 | Exploring | — | — | — | — |
| Credit Exports | ⚪ | Not started | — | — | — | — |
| Court Records | ⚪ | Not started | — | — | — | — |

---

## Safety Rules

1. **No connection may auto-send** without T3 approval
2. **No connection may auto-delete** any data
3. **Every write action** must generate a receipt
4. **Every external action** must pass the risk classifier first
5. **Credentials are never stored** in code, docs, or config files
6. **Connection status** is reviewed monthly as part of the trust/admin records audit