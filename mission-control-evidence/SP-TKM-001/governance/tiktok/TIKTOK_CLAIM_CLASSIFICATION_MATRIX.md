# TikTok Claim Classification Matrix

Mission: SP-TKM-001
Owner: Sentinel + Athena
Effective Date: 2026-07-27

## 1. Claim Verification Levels

| Level | Name | Meaning | Example |
|---|---|---|---|
| V1 | Verified primary authority | Direct statute, regulation, court opinion, agency publication, official TikTok policy, or original contract/account document. | FDCPA § 809 requires a debt collector to provide validation information within five days of initial communication. 15 U.S.C. § 1692g. |
| V2 | Supported secondary interpretation | Authoritative treatise, agency guidance, bar publication, or well-established legal analysis, with primary authority cited. | A UCC-1 financing statement perfects a security interest but does not create the underlying security interest. |
| V3 | Jurisdiction-dependent | Accurate in some jurisdictions but not all; requires local review. | Statute of limitations on debt collection varies by state and claim type. |
| V4 | Disputed or unresolved theory | Controversial, unsettled, or partially accepted interpretation; requires human review. | Some theories about "accepted for value" lack widespread legal acceptance. |
| V5 | Unsupported, misleading, or false | No credible authority or contrary to law; reject. | "A billing coupon is legal tender that cancels the debt." |

## 2. Risk Ratings

| Rating | Definition | Examples |
|---|---|---|
| LOW | General document organization; evidence preservation; reading account statements; public agency complaint procedures; plain-language definitions. | How to build a timeline; five documents to preserve; how to redact records. |
| MODERATE | Statute explanations; credit-report disputes; debt-validation procedures; contract analysis; UCC explanations. | What a UCC-1 does; debt validation vs. cancellation; credit-bureau dispute process. |
| HIGH | Litigation strategy; tax forms; UCC filings against named parties; affidavits accusing fraud; advice to stop making payments; claims involving negotiable instruments; trust asset protection; bankruptcy; court jurisdiction. | "How to file a UCC-1 against a specific lender"; "When to stop paying a debt"; bankruptcy options. |
| PROHIBITED | Instructions to submit false tax information; unauthorized liens; forged or altered instruments; deceptive payment instruments; claims that a billing statement is automatically legal tender; guaranteed secret-account access; impersonation; threats unsupported by law. | "Use this form to discharge debt without payment"; "File a lien to cancel your mortgage". |

## 3. Dispatch Marshal Decision Table

| Verification | LOW | MODERATE | HIGH | PROHIBITED |
|---|---|---|---|---|
| V1 | Publish | Publish with disclaimer | Human review required; publish only after human approval | Reject |
| V2 | Publish | Publish with disclaimer and source note | Human review required | Reject |
| V3 | Publish with jurisdiction note | Publish with jurisdiction note and disclaimer | Human review required; add jurisdiction warning | Reject |
| V4 | Human review | Human review | Reject unless downgraded | Reject |
| V5 | Reject | Reject | Reject | Reject |

## 4. Application Rules

- Every script must list the highest-risk claim and its classification.
- A script's overall risk rating is the highest rating of any claim it contains.
- MODERATE and HIGH scripts require a source packet.
- HIGH scripts require human review before production.
- PROHIBITED content is quarantined and reported to Hermes and Sentinel.
- V3 claims must name the jurisdictions in which they are accurate and include a warning for viewers elsewhere.

## 5. Content Pillar Risk Guidance

| Pillar | Typical Risk | Notes |
|---|---|---|
| Consumer-law fundamentals | LOW–MODERATE | Keep definitions general; cite sources. |
| Document literacy | LOW | Focus on reading and organizing documents. |
| Evidence building | LOW–MODERATE | Avoid telling viewers what conclusion to draw. |
| Myth correction | LOW–MODERATE | Frame as myth vs. verified principle; avoid amplifying the myth. |
| Enforcement pathways | MODERATE–HIGH | Agency complaint procedures are safer than litigation strategy. |
| SintraPrime demonstrations | LOW–MODERATE | Show the tool; do not diagnose individual cases. |

## 6. Escalation Path

1. Justice Scribe drafts script and assigns preliminary risk.
2. Athena verifies claims and assigns V1–V5.
3. Sentinel reconciles claim level and risk rating using this matrix.
4. If required, human reviewer approves or rejects.
5. Dispatch Marshal publishes only after matrix clearance.
