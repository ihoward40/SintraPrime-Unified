"""
Tests for CitationNetwork
"""

import pytest
from unittest.mock import MagicMock, patch
from ..citation_network import CitationNetwork, CitationEdge, CaseNode, CitationReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def network():
    """Create a fresh CitationNetwork."""
    return CitationNetwork()


@pytest.fixture
def populated_network():
    """Create a CitationNetwork with sample data."""
    net = CitationNetwork()
    # Add foundational case
    net.add_case(case_id=1, case_name="Marbury v. Madison", court="scotus", year=1803, citation="5 U.S. 137")
    # Add second case citing first
    net.add_case(case_id=2, case_name="McCulloch v. Maryland", court="scotus", year=1819, citation="17 U.S. 316")
    net.add_citation(citing_id=2, cited_id=1)
    # Add third case citing both
    net.add_case(case_id=3, case_name="Youngstown Sheet", court="scotus", year=1952, citation="343 U.S. 579")
    net.add_citation(citing_id=3, cited_id=1)
    net.add_citation(citing_id=3, cited_id=2)
    # Add fourth case citing third
    net.add_case(case_id=4, case_name="New Case v. Law", court="ca9", year=2022, citation="100 F.3d 200")
    net.add_citation(citing_id=4, cited_id=3)
    return net


# ---------------------------------------------------------------------------
# CaseNode tests
# ---------------------------------------------------------------------------


class TestCaseNode:
    def test_create_case_node(self):
        node = CaseNode(
            case_id=1,
            case_name="Test v. Case",
            court="scotus",
            year=2020,
            citation="100 U.S. 200",
        )
        assert node.case_id == 1
        assert node.case_name == "Test v. Case"
        assert node.year == 2020

    def test_case_node_defaults(self):
        node = CaseNode(case_id=99, case_name="Unknown", court="ca1", year=2000, citation="")
        assert node.authority_score == 0.0
        assert node.is_overruled is False
        assert node.practice_areas == []


# ---------------------------------------------------------------------------
# CitationEdge tests
# ---------------------------------------------------------------------------


class TestCitationEdge:
    def test_create_edge(self):
        edge = CitationEdge(citing_id=2, cited_id=1)
        assert edge.citing_id == 2
        assert edge.cited_id == 1

    def test_edge_with_treatment(self):
        edge = CitationEdge(citing_id=2, cited_id=1, treatment="distinguishes", weight=0.5)
        assert edge.treatment == "distinguishes"
        assert edge.weight == 0.5


# ---------------------------------------------------------------------------
# CitationNetwork tests
# ---------------------------------------------------------------------------


class TestCitationNetwork:
    def test_add_case(self, network):
        """Test adding a case to the network."""
        node = network.add_case(case_id=1, case_name="Test v. Case", court="scotus", year=2020, citation="1 U.S. 1")
        assert node.case_id == 1
        assert 1 in network._cases

    def test_add_duplicate_case(self, network):
        """Test adding a duplicate case returns existing node."""
        n1 = network.add_case(1, "A v. B", "scotus", 2020, "1 U.S. 1")
        n2 = network.add_case(1, "A v. B (duplicate)", "scotus", 2020, "1 U.S. 1")
        assert n1 is n2

    def test_add_citation(self, network):
        """Test adding a citation edge."""
        network.add_case(1, "A v. B", "scotus", 2000, "1 U.S. 1")
        network.add_case(2, "C v. D", "ca9", 2010, "2 F.3d 3")
        edge = network.add_citation(citing_id=2, cited_id=1)
        assert edge is not None
        assert edge.citing_id == 2
        assert edge.cited_id == 1

    def test_add_citation_missing_case(self, network):
        """Test that adding citation with missing case raises ValueError."""
        with pytest.raises((ValueError, KeyError)):
            network.add_citation(citing_id=999, cited_id=1000)

    def test_get_cases_citing(self, populated_network):
        """Test getting all cases that cite a given case."""
        citing = populated_network.get_cases_citing(1)
        citing_ids = [c.case_id for c in citing]
        assert 2 in citing_ids
        assert 3 in citing_ids

    def test_get_cases_cited_by(self, populated_network):
        """Test getting all cases cited by a given case."""
        cited = populated_network.get_cases_cited_by(3)
        cited_ids = [c.case_id for c in cited]
        assert 1 in cited_ids
        assert 2 in cited_ids

    def test_citation_count(self, populated_network):
        """Test citation count for foundational case."""
        count = populated_network.get_citation_count(1)
        assert count >= 2  # At least cases 2 and 3 cite case 1

    def test_authority_score_scotus_higher(self, populated_network):
        """Test that SCOTUS cases have higher authority scores."""
        populated_network.compute_authority_scores()
        scotus_case = populated_network._cases[1]  # Marbury - most cited SCOTUS case
        ca9_case = populated_network._cases[4]     # New CA9 case - never cited
        assert scotus_case.authority_score >= ca9_case.authority_score

    def test_compute_authority_scores(self, populated_network):
        """Test that authority scores are computed for all cases."""
        populated_network.compute_authority_scores()
        for case_id, node in populated_network._cases.items():
            assert node.authority_score >= 0.0

    def test_find_citation_chain(self, populated_network):
        """Test finding the citation chain between two cases."""
        chain = populated_network.find_citation_chain(source_id=4, target_id=1)
        assert chain is not None
        assert 4 in chain
        assert 1 in chain

    def test_find_citation_chain_no_path(self, populated_network):
        """Test that no chain returns None/empty when no path exists."""
        # Case 1 does not cite case 4, so no path in reverse direction
        chain = populated_network.find_citation_chain(source_id=1, target_id=4)
        assert not chain  # None or empty list

    def test_get_landmark_cases(self, populated_network):
        """Test identifying landmark cases by citation count."""
        populated_network.compute_authority_scores()
        landmarks = populated_network.get_landmark_cases(top_n=2)
        assert len(landmarks) <= 2
        # Marbury (case 1) should be near top
        landmark_ids = [n.case_id for n in landmarks]
        assert 1 in landmark_ids

    def test_mark_overruled(self, populated_network):
        """Test marking a case as overruled."""
        populated_network.mark_overruled(case_id=2, overruled_by_id=3)
        assert populated_network._cases[2].is_overruled is True
        assert populated_network._cases[2].overruled_by == 3

    def test_is_overruled_detection(self, populated_network):
        """Test detecting if a case is overruled."""
        assert not populated_network.is_overruled(1)
        populated_network.mark_overruled(1, 4)
        assert populated_network.is_overruled(1)

    def test_get_depth_of_citations(self, populated_network):
        """Test getting citation depth from a starting case."""
        depth = populated_network.get_citation_depth(starting_id=4, max_depth=3)
        # Should reach cases 3, 1, 2 from case 4
        assert len(depth) >= 1

    def test_export_json_graph(self, populated_network):
        """Test exporting network as JSON for d3.js."""
        import json
        graph_json = populated_network.export_json_graph()
        graph = json.loads(graph_json)
        assert "nodes" in graph
        assert "links" in graph
        assert len(graph["nodes"]) == 4
        assert len(graph["links"]) >= 3

    def test_generate_citation_report(self, populated_network):
        """Test generating a citation report for a case."""
        populated_network.compute_authority_scores()
        report = populated_network.generate_citation_report(case_id=1)
        assert isinstance(report, CitationReport)
        assert report.case_id == 1
        assert report.total_citing_cases >= 2
        assert report.authority_score >= 0.0

    def test_empty_network_citation_count(self, network):
        """Test citation count on empty network."""
        network.add_case(1, "Alone v. No One", "ca1", 2020, "1 F.3d 1")
        assert network.get_citation_count(1) == 0

    def test_network_size(self, populated_network):
        """Test network has correct node and edge counts."""
        stats = populated_network.get_stats()
        assert stats["total_cases"] == 4
        assert stats["total_citations"] >= 3

    def test_add_citation_with_treatment(self, populated_network):
        """Test adding citation with treatment type."""
        edge = populated_network.add_citation(
            citing_id=4, cited_id=2, treatment="distinguishes"
        )
        assert edge.treatment == "distinguishes"

    def test_get_most_cited_in_court(self, populated_network):
        """Test getting most cited cases within a specific court."""
        populated_network.compute_authority_scores()
        scotus_cases = populated_network.get_most_cited_in_court("scotus", top_n=3)
        assert all(c.court == "scotus" for c in scotus_cases)
