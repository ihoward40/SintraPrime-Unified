# Chain of Custody Model

**Status:** DESIGN SPECIFICATION  
**Created:** 2026-06-14  
**Based on:** Verified Nova execution_ledger.py hash-chained audit trail

---

## Purpose

The Chain of Custody model provides a tamper-evident audit trail for all evidence-related actions in the Evidence Command Center. Every action (upload, review, tag, link, export) is timestamped, hashed, and chained to the previous action, making it impossible to alter history without detection.

---

## Design Principles

1. **Immutability:** Once recorded, entries cannot be modified or deleted
2. **Hash-Chained:** Each entry contains the hash of the previous entry (like blockchain)
3. **Tamper-Evident:** Any modification breaks the hash chain and is detectable
4. **Court-Defensible:** Provides cryptographic proof of evidence handling
5. **Chronological:** Maintains strict time-ordering of all actions

---

## Data Model

### Chain Entry Structure

```json
{
  "timestamp": "2026-06-14T12:00:00.000Z",
  "actor": "user-uuid-or-agent-name",
  "actor_role": "attorney|paralegal|client|ai_agent",
  "action": "upload|review|tag|link|export|approve|reject",
  "details": {
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "location": "Evidence Command Center",
    "notes": "Reviewed for FDCPA violations"
  },
  "prev_hash": "a1b2c3d4e5f6...",
  "entry_hash": "b2c3d4e5f6g7..."
}
```

### Hash Computation

```
entry_hash = SHA-256(
  action +
  actor +
  timestamp +
  details (stringified JSON) +
  prev_hash
)
```

**First entry:** `prev_hash = ""` (empty string for genesis entry)

**Subsequent entries:** `prev_hash = previous_entry.entry_hash`

---

## Action Types

| Action | Description | Actor | Details Required |
|--------|-------------|-------|------------------|
| `upload` | Evidence item uploaded to system | User/Client | source, filename, size, hash |
| `review` | Evidence reviewed by human or AI | User/Agent | review_notes, confidence_score |
| `tag` | Evidence tagged with category/metadata | User/Agent | tags_added, tags_removed |
| `link` | Evidence linked to violation | User/Agent | violation_id, confidence |
| `approve` | Evidence approved for use in case | Attorney | approval_notes |
| `reject` | Evidence rejected or excluded | Attorney | rejection_reason |
| `export` | Evidence exported/downloaded | User | export_format, packet_id |
| `modify_metadata` | Metadata updated (not file content) | User | fields_changed, old_values, new_values |
| `legal_hold` | Evidence placed under legal hold | Attorney | hold_reason, expiration |
| `release_hold` | Legal hold released | Attorney | release_reason |

---

## Chain Verification

### Verification Algorithm

```python
def verify_chain_of_custody(chain: List[ChainEntry]) -> (bool, Optional[int], Optional[str]):
    """
    Verify integrity of chain of custody.
    
    Returns:
        (valid, broken_at_index, error_message)
    """
    prev_hash = ""
    
    for index, entry in enumerate(chain):
        # Verify previous hash matches
        if entry.prev_hash != prev_hash:
            return (False, index, f"Chain broken at entry {index}: prev_hash mismatch")
        
        # Recompute hash
        computed_hash = sha256(
            entry.action +
            entry.actor +
            entry.timestamp +
            json.dumps(entry.details, sort_keys=True) +
            prev_hash
        ).hexdigest()
        
        # Verify hash matches
        if entry.entry_hash != computed_hash:
            return (False, index, f"Entry {index} has been tampered: hash mismatch")
        
        prev_hash = entry.entry_hash
    
    return (True, None, "Chain of custody intact")
```

### Verification Frequency

- **On demand:** When generating court packets or affidavits
- **Scheduled:** Daily verification of all evidence chains
- **On export:** Before including evidence in legal filings
- **On audit:** External compliance reviews

---

## Integration with Existing Audit Trail

### Relationship to portal.audit_logs

The Chain of Custody model **complements** (not replaces) the existing `portal.audit_logs` table:

| System | Purpose | Scope |
|--------|---------|-------|
| **portal.audit_logs** | System-wide audit trail | All actions (login, document view, settings changes, etc.) |
| **Chain of Custody** | Evidence-specific audit trail | Evidence-related actions only (upload, review, link, export) |

**Design Decision:** Chain of Custody entries **reference** audit log entries but maintain separate hash chain for evidence-specific verification.

**Linkage:**
```json
{
  "chain_entry_id": "chain-uuid",
  "audit_log_id": "audit-uuid",  // References portal.audit_logs.id
  "entry_hash": "...",
  "prev_hash": "..."
}
```

This allows:
- ✅ Unified audit trail (portal.audit_logs has all actions)
- ✅ Evidence-specific verification (chain of custody independently verifiable)
- ✅ Cross-reference capability (link chain entries to system audit log)

---

## Storage Considerations

### Option A: Embedded in Evidence Registry (JSONB column)

**Structure:**
```sql
-- In evidence_registry table
chain_of_custody JSONB DEFAULT '[]'
```

**Pros:**
- ✅ Simple (chain stored with evidence)
- ✅ No joins (all data in one row)
- ✅ Easy to retrieve full chain

**Cons:**
- ⚠️ Row size grows with chain length
- ⚠️ Harder to query across all evidence

---

### Option B: Separate Chain Table

**Structure:**
```sql
-- Separate table
evidence_chain_of_custody (
  entry_id UUID PRIMARY KEY,
  evidence_id UUID NOT NULL,
  sequence_number INT NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  actor UUID NOT NULL,
  action VARCHAR(50) NOT NULL,
  details JSONB,
  prev_hash VARCHAR(64),
  entry_hash VARCHAR(64) NOT NULL,
  UNIQUE(evidence_id, sequence_number)
)
```

**Pros:**
- ✅ Normalized data
- ✅ Easy to query (find all reviews, exports, etc.)
- ✅ Scalable (no row size limits)

**Cons:**
- ⚠️ Requires JOIN to get full chain
- ⚠️ More complex schema

---

### Recommended Approach (Hybrid)

**Use Option A (JSONB) with retention policy:**
- Store full chain in `evidence_registry.chain_of_custody` JSONB column
- When chain exceeds threshold (e.g., 100 entries), archive old entries to separate table
- Keep last 100 entries in JSONB for fast access
- Maintain full chain in archive for verification

---

## Example Chain

```json
[
  {
    "timestamp": "2026-06-14T10:00:00.000Z",
    "actor": "client-uuid-001",
    "actor_role": "client",
    "action": "upload",
    "details": {
      "filename": "credit_report_experian_2024.pdf",
      "size_bytes": 524288,
      "sha256": "a1b2c3d4...",
      "source": "client_portal_upload"
    },
    "prev_hash": "",
    "entry_hash": "e5f6g7h8i9j0..."
  },
  {
    "timestamp": "2026-06-14T10:05:00.000Z",
    "actor": "hermes",
    "actor_role": "ai_agent",
    "action": "review",
    "details": {
      "review_type": "violation_analysis",
      "violations_found": 3,
      "confidence_score": 0.89,
      "analysis_duration_ms": 1250
    },
    "prev_hash": "e5f6g7h8i9j0...",
    "entry_hash": "f6g7h8i9j0k1..."
  },
  {
    "timestamp": "2026-06-14T10:10:00.000Z",
    "actor": "attorney-uuid-002",
    "actor_role": "attorney",
    "action": "approve",
    "details": {
      "approval_notes": "Credit report shows clear FCRA violations",
      "approved_for_use": true
    },
    "prev_hash": "f6g7h8i9j0k1...",
    "entry_hash": "g7h8i9j0k1l2..."
  },
  {
    "timestamp": "2026-06-14T11:00:00.000Z",
    "actor": "attorney-uuid-002",
    "actor_role": "attorney",
    "action": "export",
    "details": {
      "export_type": "court_packet",
      "packet_id": "packet-uuid-003",
      "format": "pdf",
      "recipient": "U.S. District Court"
    },
    "prev_hash": "g7h8i9j0k1l2...",
    "entry_hash": "h8i9j0k1l2m3..."
  }
]
```

**Verification:**
- ✅ Each entry's `prev_hash` matches previous entry's `entry_hash`
- ✅ Recomputing each `entry_hash` produces identical result
- ✅ Chain is chronologically ordered (timestamps increasing)
- ✅ Tampering with any entry breaks the chain

---

## Court Presentation

### Affidavit Language Template

```
I, [Attorney Name], do hereby certify that the attached evidence has been 
maintained under a cryptographically-secured chain of custody from the time 
of acquisition through present filing.

The chain of custody consists of [N] recorded actions, each cryptographically 
hashed and linked to the previous action using SHA-256 hashing, making any 
alteration or tampering immediately detectable.

Chain of Custody Summary:
- Evidence Item: [Evidence ID]
- File: [Filename]
- SHA-256 Hash: [Hash]
- Date Acquired: [Date]
- Acquired By: [Person]
- Total Chain Entries: [N]
- Chain Integrity: VERIFIED ✓

The complete chain of custody is attached as Exhibit [X] and may be 
independently verified using the provided hashes.
```

### Exhibit Format

```
CHAIN OF CUSTODY VERIFICATION
Evidence ID: EV-0001-2024
File: credit_report_experian_2024.pdf
SHA-256: a1b2c3d4e5f6g7h8...

Entry 1 of 4
Timestamp: 2026-06-14 10:00:00 UTC
Action: UPLOAD
Actor: John Doe (Client)
Hash: e5f6g7h8i9j0k1l2...
Previous Hash: (genesis)

Entry 2 of 4
Timestamp: 2026-06-14 10:05:00 UTC
Action: REVIEW
Actor: Hermes AI Agent
Details: 3 violations found, 89% confidence
Hash: f6g7h8i9j0k1l2m3...
Previous Hash: e5f6g7h8i9j0k1l2...

[...]

VERIFICATION STATUS: ✓ CHAIN INTACT
All hashes verified. No tampering detected.
```

---

## API Requirements (Future Implementation)

### Append to Chain
```http
POST /api/evidence/{evidence_id}/chain
Content-Type: application/json

{
  "action": "review",
  "details": {
    "review_notes": "...",
    "confidence_score": 0.89
  }
}

Response:
{
  "entry_id": "chain-entry-uuid",
  "entry_hash": "f6g7h8i9j0k1l2m3...",
  "prev_hash": "e5f6g7h8i9j0k1l2...",
  "sequence_number": 2
}
```

### Verify Chain
```http
GET /api/evidence/{evidence_id}/chain/verify

Response:
{
  "valid": true,
  "total_entries": 4,
  "first_entry_timestamp": "2026-06-14T10:00:00Z",
  "last_entry_timestamp": "2026-06-14T11:00:00Z",
  "verification_timestamp": "2026-06-14T16:00:00Z"
}
```

### Export Chain
```http
GET /api/evidence/{evidence_id}/chain/export?format=pdf

Returns: PDF document with full chain of custody for court filing
```

---

## Compliance & Legal Standards

### Standards Met

- ✅ **Federal Rules of Evidence 901(b)(4):** Distinctive characteristics and the like (hash provides unique fingerprint)
- ✅ **Federal Rules of Evidence 902(14):** Certified data copied from electronic device (SHA-256 hash certification)
- ✅ **E-Discovery Best Practices:** Tamper-evident audit trail
- ✅ **SOC 2 Type II:** Audit trail for access control and data integrity
- ✅ **GDPR Article 32:** Technical measures to ensure security of processing

### Admissibility Considerations

**Foundation for Admissibility:**
1. **Authentication:** SHA-256 hash proves file identity
2. **Chain of Custody:** Unbroken record from acquisition to filing
3. **Integrity:** Hash verification proves no alteration
4. **Reliability:** Industry-standard cryptographic methods

**Potential Challenges:**
- ⚠️ "How can we trust the system itself wasn't compromised?"
- **Response:** Independent verification possible (provide chain + hashes to third party)

- ⚠️ "What prevents you from creating a false chain?"
- **Response:** Genesis entry references external source (client portal upload log, email timestamp, etc.) that can be independently verified

---

## Future Enhancements

1. **Blockchain Integration:** Anchor chain hashes to public blockchain for additional verification
2. **Third-Party Timestamping:** Use RFC 3161 timestamping authority for cryptographic proof of time
3. **Multi-Signature Actions:** Require multiple parties to approve critical actions
4. **Encrypted Chain:** Encrypt chain entries for privacy (while maintaining hash verification)
5. **Chain Comparison:** Compare chains across multiple evidence items to detect patterns

---

**END CHAIN OF CUSTODY MODEL SPECIFICATION**
