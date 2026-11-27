"""SP-PROCEDURAL-TRAPS-001 — deadline, burden, waiver, and proof scanner.

This scanner surfaces underused procedural leverage only when facts make it
potentially relevant.  It does not declare a violation or create deadlines by
itself; every candidate carries a trigger, proof requirement, and jurisdiction
check.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProceduralTrap:
    trap_id: str
    name: str
    authority: tuple[str, ...]
    trigger: str
    action: str
    deadline_or_consequence: str
    proof_needed: tuple[str, ...]
    caveat: str
    priority: int = 50

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProceduralTrapScanner:
    """Scan a matter for quiet procedural leverage and burden-shifting devices."""

    MODULE_ID = "SP-PROCEDURAL-TRAPS-001"

    def scan(self, matter: dict[str, Any]) -> list[ProceduralTrap]:
        tx = self._text(matter.get("transaction_type")).lower()
        status = self._text(matter.get("matter_status")).lower()
        jurisdiction = {self._text(x).lower() for x in (matter.get("jurisdiction") or [])}
        facts = {self._text(x).lower() for x in (matter.get("facts") or [])}
        evidence = {self._text(x).lower() for x in (matter.get("evidence") or [])}
        capacities = {
            self._text(p.get("capacity")).lower()
            for p in (matter.get("parties") or [])
            if isinstance(p, dict)
        }

        litigation = status in {"litigation", "filed", "discovery", "court"} or "pending_action" in facts
        federal = "federal" in jurisdiction or "federal_court" in facts
        secured = "secured" in tx or "security_agreement" in evidence or "debtor" in capacities
        disposition = bool({"disposition_occurred", "collateral_sold", "repossession_sale"} & (facts | evidence))
        assigned = bool({"assignment", "assignee", "assigned_contract", "servicer_transfer"} & (facts | evidence))
        credit_reporting = bool({"credit_reporting", "consumer_report", "furnished_credit_data"} & (facts | evidence))
        esi_risk = bool({"emails", "texts", "system_logs", "call_recordings", "metadata", "esi"} & (facts | evidence))

        traps: list[ProceduralTrap] = []

        if secured:
            traps.append(ProceduralTrap(
                trap_id="PTR-UCC-9-210",
                name="Authenticated accounting deadline",
                authority=("UCC § 9-210", "N.J.S.A. 12A:9-210 when New Jersey law governs"),
                trigger="A debtor needs a secured-party accounting, collateral list, or approval/correction of a stated balance.",
                action="Serve an authenticated request that reasonably identifies the transaction and precisely states the accounting or statement requested.",
                deadline_or_consequence="Uniform text generally requires response within 14 days; failure can feed section-specific Article 9 remedies.",
                proof_needed=("debtor status", "secured transaction", "authenticated request", "proof of receipt"),
                caveat="Do not label a generic validation letter a § 9-210 request unless it satisfies the statute.",
                priority=100,
            ))

        if disposition:
            traps.append(ProceduralTrap(
                trap_id="PTR-UCC-9-611-614",
                name="Disposition-notice compliance trap",
                authority=("UCC §§ 9-611 through 9-614",),
                trigger="Collateral has been or will be disposed of after default.",
                action="Audit recipients, timing, content, address used, method of dispatch, and consumer-goods safe-harbor content before accepting a deficiency calculation.",
                deadline_or_consequence="Defective notice can materially affect deficiency rights and remedies, but consequences vary by transaction and state law.",
                proof_needed=("notice", "dispatch evidence", "address chronology", "default/disposition dates", "consumer-goods status"),
                caveat="Nonreceipt alone does not necessarily prove noncompliance; distinguish sending requirements from actual receipt requirements.",
                priority=98,
            ))
            traps.append(ProceduralTrap(
                trap_id="PTR-UCC-9-616",
                name="Post-disposition deficiency explanation deadline",
                authority=("UCC § 9-616", "N.J.S.A. 12A:9-616 when New Jersey law governs"),
                trigger="Consumer-goods collateral was disposed of and a deficiency is asserted.",
                action="Serve a qualifying authenticated request for the statutory surplus/deficiency explanation and calendar receipt plus 14 days.",
                deadline_or_consequence="A qualifying request generally triggers a 14-day response obligation; the exact statutory consequence must be mapped before use.",
                proof_needed=("consumer-goods transaction", "disposition", "authenticated request", "proof of receipt"),
                caveat="This is not a substitute for proving commercial unreasonableness or an incorrect balance.",
                priority=100,
            ))

        if assigned:
            traps.append(ProceduralTrap(
                trap_id="PTR-UCC-9-404",
                name="Assignee-defense / recoupment preservation",
                authority=("UCC § 9-404", "N.J.S.A. 12A:9-404 when New Jersey law governs"),
                trigger="A contract or account has been assigned and the obligor has claims or defenses arising from the underlying transaction.",
                action="Identify which defenses or recoupment claims arose from the same transaction, when other claims accrued, and when authenticated assignment notice was received.",
                deadline_or_consequence="Qualifying defenses/recoupment can follow the obligation to the assignee, often at least to reduce what is owed; consumer law may provide a different rule.",
                proof_needed=("underlying contract", "assignment notice", "claim accrual dates", "seller/assignor misconduct evidence"),
                caveat="Do not assume every affirmative claim can be recovered from an assignee; § 9-404 contains limits and other consumer law may control.",
                priority=94,
            ))

        if litigation and federal:
            traps.extend([
                ProceduralTrap(
                    trap_id="PTR-FRCP-36",
                    name="Requests for Admission deadline trap",
                    authority=("Fed. R. Civ. P. 36",),
                    trigger="A federal civil action is pending and discrete facts, application-of-law-to-fact, or document genuineness can be narrowed.",
                    action="Serve separately stated RFAs and calendar the response deadline; use admissions to eliminate proof disputes, not to manufacture impossible legal conclusions.",
                    deadline_or_consequence="A matter is admitted if not timely answered or objected to, generally within 30 days unless the court or parties set another time.",
                    proof_needed=("pending federal action", "proper service", "served requests", "deadline calculation"),
                    caveat="This consequence for silence is litigation-specific; it does not validate pre-suit tacit-agreement theories.",
                    priority=100,
                ),
                ProceduralTrap(
                    trap_id="PTR-FRCP-13A",
                    name="Compulsory-counterclaim waiver screen",
                    authority=("Fed. R. Civ. P. 13(a)",),
                    trigger="A responsive pleading is due in federal court and the party has a claim arising out of the same transaction or occurrence.",
                    action="Run a transaction-or-occurrence comparison before answering so potentially compulsory counterclaims are identified and preserved.",
                    deadline_or_consequence="Failure to plead a compulsory counterclaim can create later preclusion risk, subject to the rule and applicable doctrine.",
                    proof_needed=("operative complaint", "candidate counterclaim facts", "transaction nexus", "pleading deadline"),
                    caveat="State compulsory-counterclaim rules differ; verify forum-specific law before treating a claim as compulsory.",
                    priority=96,
                ),
                ProceduralTrap(
                    trap_id="PTR-FRCP-30B6",
                    name="Institutional-knowledge deposition trap",
                    authority=("Fed. R. Civ. P. 30(b)(6)",),
                    trigger="A corporation claims knowledge is fragmented across departments, servicers, databases, or vendors.",
                    action="Serve reasonably particular deposition topics targeting policies, system-of-record fields, transfer history, calculations, notices, and preservation.",
                    deadline_or_consequence="The organization must designate and prepare witness(es) to testify about information known or reasonably available to it.",
                    proof_needed=("pending federal action", "particularized topics", "proper notice/subpoena"),
                    caveat="Overbroad or disproportional topics can be limited by the court.",
                    priority=92,
                ),
            ])

        if litigation and esi_risk:
            traps.append(ProceduralTrap(
                trap_id="PTR-FRCP-37E",
                name="ESI preservation and spoliation sequence",
                authority=("Fed. R. Civ. P. 37(e) in federal court",),
                trigger="Relevant ESI may be subject to deletion, overwrite, retention limits, or loss after litigation became reasonably foreseeable.",
                action="Map preservation trigger, custodians, systems, retention periods, notices, reasonable preservation steps, losses, replaceability, prejudice, and evidence of intent if severe sanctions are sought.",
                deadline_or_consequence="Potential curative or sanction consequences depend on the rule's full sequence; preservation should begin before routine deletion destroys evidence.",
                proof_needed=("foreseeability", "specific ESI", "retention system", "loss", "failed reasonable steps", "nonreplaceability"),
                caveat="A preservation letter does not itself establish spoliation or intent.",
                priority=95,
            ))

        if litigation:
            traps.append(ProceduralTrap(
                trap_id="PTR-FRE-FOUNDATION",
                name="Business-record / authentication foundation attack",
                authority=("Fed. R. Evid. 803(6)", "Fed. R. Evid. 901", "Fed. R. Evid. 902(11)", "Fed. R. Evid. 1006"),
                trigger="A party relies on inherited account records, computer-generated histories, declarations, or summaries rather than a witness with firsthand knowledge.",
                action="Separate authenticity, hearsay exception, integrated-record reliability, certification notice, underlying-data availability, and summary-chart foundation into distinct objections/discovery targets.",
                deadline_or_consequence="Weak foundation can limit or exclude records or summaries; certification and pretrial disclosure deadlines can create additional leverage.",
                proof_needed=("proffered records", "custodian declaration", "system provenance", "underlying data", "summary methodology"),
                caveat="A witness need not have personally created every record; focus on the actual evidentiary elements and reliability of adopted/integrated records.",
                priority=93,
            ))

        if credit_reporting:
            traps.append(ProceduralTrap(
                trap_id="PTR-FCRA-DISPUTE-SEQUENCE",
                name="CRA/furnisher dispute-sequence preservation",
                authority=("FCRA", "12 C.F.R. § 1022.43 where applicable"),
                trigger="An inaccurate or incomplete consumer-report field is being furnished.",
                action="Preserve before/after reports, dispute channel, exact field, substantiation, receipt, investigation result, and any reinsertion or repeated furnishing.",
                deadline_or_consequence="Statutory duties and litigation theories can depend on who received the dispute, what was disputed, and what happened afterward.",
                proof_needed=("consumer reports", "dispute", "proof of receipt", "results", "furnishing history"),
                caveat="Do not collapse direct-furnisher and CRA-routed dispute duties into one rule; private remedies differ by provision.",
                priority=90,
            ))

        return sorted(traps, key=lambda item: (-item.priority, item.trap_id))

    @staticmethod
    def _text(value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""
