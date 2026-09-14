"""Certification tests for rare but defensible SP-LEGAL-LEVERAGE methods."""

from legal_intelligence.rare_legal_levers import RareLegalLeverageEngine


def _ids(ctx):
    return {lever.lever_id for lever in RareLegalLeverageEngine().suggest(ctx)}


def test_uacc_secured_auto_surfaces_accounting_deficiency_and_holder_rule():
    ctx = {
        "transaction_type": "secured_auto_finance",
        "jurisdiction": ["New Jersey"],
        "matter_status": "prelitigation",
        "parties": [
            {"name": "consumer", "capacity": "consumer_obligor"},
            {"name": "servicer", "capacity": "secured_party_claimant"},
        ],
        "evidence": [
            "security_agreement",
            "retail_installment_contract",
            "disposition_occurred",
            "credit_reporting",
            "consumer_report",
        ],
        "facts": ["vehicle", "repossession_sale", "seller_arranged_credit"],
    }
    ids = _ids(ctx)
    assert "LEV-UCC-9-210" in ids
    assert "LEV-UCC-9-616" in ids
    assert "LEV-UCC-9-602" in ids
    assert "LEV-NJ-DEFICIENCY-PRESUMPTION" in ids
    assert "LEV-FTC-HOLDER-RULE" in ids
    assert "LEV-REGV-1022-43" in ids


def test_related_party_sale_lever_is_post_disposition_candidate_not_merits_finding():
    ctx = {
        "transaction_type": "secured_auto_finance",
        "parties": [{"name": "consumer", "capacity": "debtor"}],
        "evidence": ["security_agreement", "disposition_occurred"],
        "facts": ["repossession_sale"],
    }
    levers = RareLegalLeverageEngine().suggest(ctx)
    lever = next(item for item in levers if item.lever_id == "LEV-UCC-9-615F")
    assert "relationship" in lever.evidence_needed
    assert "Low price alone" in lever.caveat


def test_rule_36_only_surfaces_when_litigation_is_pending():
    pre = {
        "transaction_type": "consumer_credit",
        "matter_status": "prelitigation",
        "parties": [{"name": "consumer", "capacity": "consumer_obligor"}],
    }
    filed = dict(pre, matter_status="litigation")
    assert "LEV-FRCP-36" not in _ids(pre)
    assert "LEV-FRCP-36" in _ids(filed)
    assert "LEV-FRCP-30B6" in _ids(filed)
    assert "LEV-FRCP-37E" in _ids(filed)


def test_credit_reporting_surfaces_direct_dispute_and_accuracy_integrity_audit():
    ctx = {
        "transaction_type": "consumer_credit",
        "parties": [{"name": "consumer", "capacity": "consumer_obligor"}],
        "facts": ["credit_reporting"],
        "evidence": ["consumer_report"],
    }
    ids = _ids(ctx)
    assert "LEV-REGV-1022-43" in ids
    assert "LEV-REGV-ACCURACY-INTEGRITY" in ids


def test_engine_does_not_surface_secured_transaction_tools_without_trigger():
    ctx = {
        "transaction_type": "employment_dispute",
        "matter_status": "prelitigation",
        "parties": [{"name": "worker", "capacity": "employee"}],
    }
    ids = _ids(ctx)
    assert "LEV-UCC-9-210" not in ids
    assert "LEV-UCC-9-616" not in ids
    assert "LEV-NJ-DEFICIENCY-PRESUMPTION" not in ids
