# Federal Overlays Foundation

Phase 2C-1 establishes a governed federal authority package at `data/federal/`.

## Scope

The package covers issue-spotting records for:

- FDCPA debt validation and collection communications
- FCRA disputes and reinvestigation
- TILA and FCBA disclosures and billing errors
- EFTA unauthorized transfers and error resolution
- ECOA credit discrimination and adverse action
- bankruptcy estate, automatic stay, and transfer issues
- Social Security and support-enforcement benefit overlays
- federal tax liens and levies
- SCRA interest protection
- arbitration and electronically stored information preservation
- federal intersections with state UCC, bankruptcy, and tax priority

Each rule links to one or more `LegalAuthority` records. Federal statutes use `FEDERAL_STATUTE`; federal rules and regulations retain their distinct authority types. eCFR records are marked `PRIMARY_SOURCE_LOCATED` and `LOCATOR_ONLY` because the eCFR is an authoritative but unofficial electronic version.

## Guardrails

All Phase 2C-1 rules require human review and remain `NOT_SUBMITTED`. No federal rule is production eligible. Bankruptcy records are labeled `BANKRUPTCY_ONLY_RULE`; tax conclusions remain CPA or tax-attorney review gated. The UCC intersection record does not assert a federal UCC: Article 9 enactment and filing questions remain state-law questions with federal bankruptcy and tax overlays.

This increment does not implement persistent matters, evidence attachments, deadline calculations, review endpoints, or frontend case workspaces. Those are later Phase 2C increments.

## Primary source families

- [United States Code](https://uscode.house.gov/)
- [Federal Rules of Civil Procedure](https://www.uscourts.gov/rules-policies/current-rules-practice-procedure/federal-rules-civil-procedure)
- [Electronic Code of Federal Regulations](https://www.ecfr.gov/)

Source verification is not professional legal approval. Output is educational and issue-spotting only.