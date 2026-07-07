"""
Tests for BRA Standard Disclaimer Library — BKR-14 and BKR-15.
"""
import pytest
from blackstone.bra.disclaimers import (
    get_disclaimer,
    get_disclaimer_record,
    select_disclaimers,
    list_all,
    ALL_DISCLAIMERS,
)


class TestRegistry:
    def test_all_eight_disclaimers_registered(self):
        assert len(ALL_DISCLAIMERS) == 8

    def test_nla_disclaimers_present(self):
        for i in range(1, 5):
            assert f"DIS-NLA-0{i}" in ALL_DISCLAIMERS

    def test_unc_disclaimers_present(self):
        for i in range(1, 5):
            assert f"DIS-UNC-0{i}" in ALL_DISCLAIMERS


class TestGetDisclaimer:
    def test_returns_text_string(self):
        text = get_disclaimer("DIS-NLA-01")
        assert isinstance(text, str)
        assert len(text) > 50

    def test_nla_01_content(self):
        text = get_disclaimer("DIS-NLA-01")
        assert "not constitute legal advice" in text

    def test_nla_04_content(self):
        text = get_disclaimer("DIS-NLA-04")
        assert "IRS" in text or "tax" in text.lower()

    def test_unknown_id_raises(self):
        with pytest.raises(KeyError, match="not found"):
            get_disclaimer("DIS-FAKE-99")


class TestSelectDisclaimers:
    def test_educational_gets_nla01(self):
        ids = select_disclaimers(claim_status_code="EDU")
        assert "DIS-NLA-01" in ids

    def test_preliminary_gets_unc01(self):
        ids = select_disclaimers(confidence_code="CONF-P")
        assert "DIS-UNC-01" in ids

    def test_disputed_gets_unc02(self):
        ids = select_disclaimers(claim_status_code="DISP")
        assert "DIS-UNC-02" in ids

    def test_multi_jurisdiction_gets_unc03(self):
        ids = select_disclaimers(jurisdiction_code="MULTI:{NJ,NY}")
        assert "DIS-UNC-03" in ids

    def test_not_temporal_current_gets_unc04(self):
        ids = select_disclaimers(temporal_current=False)
        assert "DIS-UNC-04" in ids

    def test_tax_gets_nla04(self):
        ids = select_disclaimers(is_tax_matter=True)
        assert "DIS-NLA-04" in ids

    def test_consumer_rights_gets_nla02(self):
        ids = select_disclaimers(is_consumer_rights=True)
        assert "DIS-NLA-02" in ids

    def test_inline_gets_nla03(self):
        ids = select_disclaimers(inline_only=True)
        assert "DIS-NLA-03" in ids


class TestListAll:
    def test_returns_list_of_8(self):
        all_d = list_all()
        assert len(all_d) == 8
        for d in all_d:
            assert "id" in d
            assert "text" in d
            assert "name" in d
