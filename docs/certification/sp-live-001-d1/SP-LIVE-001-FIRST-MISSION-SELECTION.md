# SP-LIVE-001 first-mission selection

## Selection criteria

The first live mission must prove voice capture/output, current Principal identity, bounded mission creation, governed memory provenance, at least two isolated specialists, governed model routing, exact approval, one real side effect, independent verification, immutable evidence, and a spoken/written brief. It should minimize credential power, irreversibility, external data exposure, connector count, and cleanup burden.

## Candidates

| Candidate | Side effect | Connector need | Verification | Risk/complexity | Decision |
|---|---|---|---|---|---|
| A. Create a labeled test issue in the pinned public SintraPrime repository | One issue creation | Authenticated GitHub issue-create, tightly pinned repo/account | GET exact issue by returned ID via separate read capability | Moderate; reversible by later separately authorized close, but public write | **Preferred** |
| B. Create a synthetic calendar event in a dedicated test calendar | One event creation | Authenticated calendar create/read | Read event by provider ID | Moderate; account/OAuth and scheduling semantics | Alternate |
| C. Upload a synthetic text file to a dedicated Drive test folder | One file create | Drive file-create plus metadata/read | Metadata/hash retrieval | Higher; Drive write/content authority conflicts with dormant metadata-only design | Reject for first mission |
| D. Send a message/email to a test destination | One outbound communication | Messaging send/read/receipt | Delivery/receipt ambiguity | Higher consequence and privacy | Reject |
| E. Change an existing GitHub issue label | Mutation of existing object | Authenticated GitHub issue update/read | GET labels | Risk of acting on production state | Reject |

## Selected mission

**Candidate A: create exactly one unmistakably synthetic, labeled certification issue in `ihoward40/SintraPrime-Unified` after explicit approval.**

Illustrative title: `[SP-LIVE-001 CERTIFICATION FIXTURE] <mission short ID>`. Body contains no secrets or production action request, records mission/evidence references, and states that it is a certification fixture. Destination repository, owner, issue fields, and labels are fixed in the action envelope. The mission’s informational briefing uses existing certified/local status and governed memory; the side effect is issue creation only.

## Why it is minimum

- One provider and one object creation.
- Clear approval semantics and visible/retrievable postcondition.
- Provider-issued issue ID/URL supports independent verification.
- No file contents, account documents, email recipients, or production configuration.
- Existing Gate 4D-B public repository metadata proves only a conceptual network boundary; it does **not** authorize this write.

## Minimum connector required

A future separately governed connector similar to:

```text
provider.github-issue-create-v1
operation = issues.create
method = POST
repository = ihoward40/SintraPrime-Unified
object_count = 1
fixture_only = true
```

A separate exact-issue read verifier is also required; whether it can reuse a future authenticated read connector or needs its own certification is decided at M1.

## Authority status

```text
MISSION_SELECTED_FOR_DESIGN = TRUE
CONNECTOR_AUTHORIZED = FALSE
AUTHENTICATED_GITHUB_AUTHORIZED = FALSE
ISSUE_CREATION_AUTHORIZED = FALSE
LIVE_MISSION_AUTHORIZED = FALSE
```

Selection is not implementation or execution authority. If Principal review rejects public fixture creation, Candidate B is reconsidered under a new design decision; D1 must not silently substitute missions.
