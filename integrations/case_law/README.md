# SintraPrime Case Law & Legal Intelligence Integration

Real-time case law and legal data integration for SintraPrime-Unified. Connects to CourtListener, PACER, Congress.gov, Federal Register, and 50-state court systems.

---

## Architecture Overview

```
integrations/case_law/
├── __init__.py                  # Package exports and version
├── courtlistener_client.py      # CourtListener REST API (free, no key required)
├── pacer_navigator.py           # PACER docket search + case tracking
├── congress_api.py              # Congress.gov legislation tracker
├── state_courts.py              # 50-state court navigator
├── citation_network.py          # Citation graph (PageRank-style authority scoring)
├── precedent_finder.py          # Controlling precedent for any fact pattern
├── case_alert_system.py         # Watch for new matching cases
├── legal_news_aggregator.py     # Multi-source legal news
├── statute_tracker.py           # Statute change + legislative history
├── regulatory_monitor.py        # CFR / Federal Register monitoring
├── case_law_search_engine.py    # Unified federated search
├── opinion_analyzer.py          # Holdings, dicta, reasoning extractor
├── jurisdiction_mapper.py       # Federal/state jurisdiction analysis
└── tests/                       # pytest suite (mock HTTP, no real calls)
```

---

## Quick Start

### Installation

```bash
pip install aiohttp aiohttp-retry beautifulsoup4 networkx lxml
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CONGRESS_API_KEY` | Optional | Congress.gov API key (free from api.congress.gov) |
| `COURTLISTENER_TOKEN` | Optional | CourtListener API token (higher rate limits) |
| `SINTRA_REDIS_URL` | Optional | Redis URL for response caching |
| `SINTRA_LOG_LEVEL` | Optional | Logging level (default: INFO) |

### Basic Usage

```python
import asyncio
from integrations.case_law import (
    CourtListenerClient,
    CaseLawSearchEngine,
    PrecedentFinder,
    CitationNetwork,
    OpinionAnalyzer,
    JurisdictionMapper,
)

async def main():
    # ── Unified Search ──────────────────────────────────────────
    async with CourtListenerClient() as cl:
        engine = CaseLawSearchEngine(courtlistener=cl)
        results = await engine.search(
            "Fourth Amendment cell phone warrant",
            court="scotus",
            date_min="2010-01-01",
        )
        print(f"Found {results.total_results} results in {results.search_time_ms}ms")
        for r in results.results[:3]:
            print(f"  [{r.source}] {r.title} ({r.date})")

    # ── Find Controlling Precedent ───────────────────────────────
    async with CourtListenerClient() as cl:
        net = CitationNetwork()
        finder = PrecedentFinder(courtlistener=cl, citation_network=net)
        precedents = await finder.find_precedent(
            fact_pattern="Police searched suspect's phone without warrant at traffic stop",
            forum_court="ca9",
            exclude_overruled=True,
        )
        brief = finder.generate_precedent_brief(
            fact_pattern="...",
            results=precedents,
            forum_court="ca9",
        )
        print(brief.summary)

    # ── Analyze an Opinion ───────────────────────────────────────
    analyzer = OpinionAnalyzer()
    analysis = analyzer.analyze(
        opinion_id=12345,
        text=opinion_full_text,
        case_name="Riley v. California",
        court="scotus",
        date_filed="2014-06-25",
        citation="573 U.S. 373",
    )
    print(analysis.plain_english_summary)
    print(f"Practice areas: {analysis.practice_areas}")
    print(f"Holdings found: {len(analysis.holdings)}")

    # ── Jurisdiction Analysis ────────────────────────────────────
    mapper = JurisdictionMapper()
    jx = mapper.analyze(
        description="Employee fired for requesting religious accommodation, filed in Texas",
        states=["TX"],
        plaintiff_state="TX",
        defendant_state="DE",
        amount_in_controversy=150_000,
    )
    print(f"Primary jurisdiction: {jx.primary_jurisdiction}")
    print(f"Federal basis: {jx.federal_basis}")
    print(f"Venue courts: {jx.venue_courts}")
    print(f"Binding authorities: {jx.binding_authorities}")

asyncio.run(main())
```

---

## Module Reference

### CourtListenerClient

Free REST API client for [CourtListener](https://www.courtlistener.com/api/rest/v4/).

**Rate limits:** 5,000 requests/day (anonymous), higher with token.

```python
async with CourtListenerClient(api_token="optional") as cl:
    # Full-text search
    results = await cl.search_opinions("warrant cell phone", court="scotus")
    
    # Fetch specific opinion + text
    opinion = await cl.get_opinion(12345)
    text = await cl.get_opinion_text(12345)
    
    # Citation network
    citations = await cl.get_opinion_citations(12345)
    # → {"cites": [1, 2, 3], "cited_by": [10, 11]}
    
    # Case cluster (all opinions for a case)
    cluster = await cl.get_cluster(999)
    
    # Docket search
    dockets = await cl.search_dockets("Apple Inc")
    
    # Paginated iteration
    async for opinion in cl.search_opinions_paginated("patent", max_results=100):
        process(opinion)
    
    # Judge lookup
    judges = await cl.search_people("Kagan")
    
    # Courts metadata
    courts = await cl.list_courts(jurisdiction="F")  # F=Federal
```

### PACERNavigator

Searches public PACER data for federal court filings.

```python
from integrations.case_law import PACERNavigator

async with PACERNavigator() as pacer:
    # Search by party name
    cases = await pacer.search_by_party("Tesla Inc", court="cacd")
    
    # Search by case number
    case = await pacer.search_by_case_number("3:23-cv-01234", court="cacd")
    
    # Get docket entries
    entries = await pacer.get_docket_entries(case_id="3:23-cv-01234", court="cacd")
    
    # Track a case for new filings
    tracker = pacer.track_case("3:23-cv-01234", "cacd")
    new_entries = await tracker.check_for_updates()
```

### CongressAPI

Tracks legislation through Congress.gov.

```python
from integrations.case_law import CongressAPI
import os

async with CongressAPI(api_key=os.getenv("CONGRESS_API_KEY")) as congress:
    # Search bills
    bills = await congress.search_bills("digital privacy data protection")
    
    # Get bill status
    bill = await congress.get_bill(congress=118, bill_type="hr", bill_number=1234)
    
    # Track bill through committee
    history = await congress.get_bill_history(118, "hr", 1234)
    
    # Member voting record
    votes = await congress.get_member_votes(bioguide_id="K000367")
    
    # Committee hearings
    hearings = await congress.get_committee_hearings("hsju")  # House Judiciary
```

### CitationNetwork

Directed graph of case citations with PageRank-style authority scoring.

```python
from integrations.case_law import CitationNetwork

net = CitationNetwork()

# Build from CourtListener data
async with CourtListenerClient() as cl:
    await net.build_from_courtlistener(cl, seed_case_ids=[12345, 67890], depth=2)

# Compute authority scores (PageRank)
net.compute_authority_scores()

# Find who cites a case
citing = net.get_cases_citing(12345)

# Find citation chain between two cases
chain = net.find_citation_chain(source_id=99, target_id=12345)

# Identify landmark cases in an area
landmarks = net.get_landmark_cases(top_n=10)

# Check if overruled
if net.is_overruled(12345):
    print("Warning: this case has been overruled")

# Export for d3.js visualization
json_graph = net.export_json_graph()

# Generate citation report
report = net.generate_citation_report(12345)
print(f"Cited by {report.total_citing_cases} cases, authority score: {report.authority_score:.3f}")
```

### PrecedentFinder

Semantic search for controlling precedent given a fact pattern.

```python
from integrations.case_law import PrecedentFinder, CitationNetwork

net = CitationNetwork()
async with CourtListenerClient() as cl:
    finder = PrecedentFinder(courtlistener=cl, citation_network=net)
    
    # Find precedent for a fact pattern
    precedents = await finder.find_precedent(
        fact_pattern="Police used drug-sniffing dog at front door without warrant",
        forum_court="ca5",
        exclude_overruled=True,
        include_persuasive=True,
    )
    
    # Separate binding vs. persuasive
    binding = [p for p in precedents if p.binding_status.value == "binding"]
    persuasive = [p for p in precedents if p.binding_status.value == "persuasive"]
    
    # Filter by client position
    favorable = finder.filter_favorable(precedents, "defendant challenging search")
    
    # Generate brief
    brief = finder.generate_precedent_brief(
        fact_pattern="...",
        results=precedents,
        forum_court="ca5",
    )
    print(brief.summary)
    print(brief.recommended_citations)
```

### CaseAlertSystem

Background monitoring for new cases matching search criteria.

```python
from integrations.case_law import CaseAlertSystem

async with CourtListenerClient() as cl:
    alerts = CaseAlertSystem(courtlistener=cl)
    
    # Create an alert
    alert_id = await alerts.create_alert(
        name="Fourth Amendment Digital Privacy",
        query="Fourth Amendment cell phone digital warrant",
        courts=["scotus", "ca9", "ca2"],
        webhook_url="https://hooks.example.com/legal",
    )
    
    # Check for new cases (run daily via scheduler)
    new_cases = await alerts.check_alert(alert_id)
    
    # Get daily digest
    digest = await alerts.get_daily_digest()
    
    # List active alerts
    for alert in alerts.list_alerts():
        print(f"Alert '{alert.name}': {alert.hit_count} hits")
```

### OpinionAnalyzer

Extract structured legal data from court opinion text.

```python
from integrations.case_law import OpinionAnalyzer

analyzer = OpinionAnalyzer()
analysis = analyzer.analyze(
    opinion_id=12345,
    text=full_opinion_text,
    case_name="Riley v. California",
    court="scotus",
    date_filed="2014-06-25",
    citation="573 U.S. 373",
)

# Holdings
for holding in analysis.holdings:
    print(f"Holding: {holding.text[:200]}")
    print(f"  Confidence: {holding.confidence:.0%}")

# Statute citations
for stat in analysis.statute_citations:
    print(f"Statute: {stat.citation} ({stat.citation_type})")

# Case treatments
for treatment in analysis.treatments:
    print(f"  {treatment.treatment}: {treatment.cited_case}")

# Scores
print(f"Complexity: {analysis.complexity_score:.2f}/1.0")
print(f"Importance: {analysis.importance_score:.2f}/1.0")
print(f"Practice areas: {', '.join(analysis.practice_areas)}")
print(f"Flags: {', '.join(analysis.flags)}")
print()
print(analysis.plain_english_summary)
```

### JurisdictionMapper

Determine applicable courts and binding authority for any legal matter.

```python
from integrations.case_law import JurisdictionMapper

mapper = JurisdictionMapper()

# Full jurisdiction analysis
jx = mapper.analyze(
    description="Title VII employment discrimination claim",
    states=["NY"],
    plaintiff_state="NY",
    defendant_state="DE",
    amount_in_controversy=200_000,
)
print(f"Jurisdiction: {jx.primary_jurisdiction}")  # "federal"
print(f"Basis: {jx.federal_basis}")                # "federal question"
print(f"Venue: {jx.venue_courts}")                  # ["nysd", "nyed", ...]
print(f"Binding: {jx.binding_authorities}")         # ["scotus", "ca2"]

# Convenience methods
circuit = mapper.get_circuit_for_state("TX")        # "ca5"
districts = mapper.get_district_courts_for_state("CA")  # ["cacd", "cand", ...]
is_binding = mapper.is_binding_on("scotus", "cacd")     # True
```

### UnifiedSearchEngine

Federated search across all configured sources.

```python
from integrations.case_law import CaseLawSearchEngine

engine = CaseLawSearchEngine(
    courtlistener=cl,
    congress=congress,
    regulatory=reg_monitor,
)

# Natural language search
results = await engine.search(
    "corporate officer fiduciary duty shareholder suit",
    sources=["opinions", "bills"],
    date_min="2015-01-01",
    order_by="authority",
    page=1,
    page_size=25,
)

# Facets
for source, count in results.facets["source"].items():
    print(f"  {source}: {count} results")

# Export
json_export = engine.export_json(results)
csv_export = engine.export_csv(results)

# Save search for later
search_id = engine.save_search("Fiduciary Duty Watch", results.query)
later_results = await engine.run_saved_search(search_id)
```

---

## Testing

```bash
# Run all tests
pytest integrations/case_law/tests/ -v

# Run specific test file
pytest integrations/case_law/tests/test_courtlistener.py -v

# Run with coverage
pytest integrations/case_law/tests/ --cov=integrations.case_law --cov-report=html

# Run async tests
pytest integrations/case_law/tests/ -v --asyncio-mode=auto
```

All tests use mocked HTTP responses — no real API calls are made.

---

## Data Sources

| Source | URL | Key Required | Rate Limit |
|--------|-----|-------------|------------|
| CourtListener | https://www.courtlistener.com/api/rest/v4/ | No (optional) | 5,000/day anon |
| PACER Public Search | https://pcl.uscourts.gov/ | No | ~60/min |
| Congress.gov | https://api.congress.gov/v3/ | Yes (free) | 5,000/hour |
| Federal Register | https://www.federalregister.gov/api/v1/ | No | ~1,000/day |
| eCFR | https://www.ecfr.gov/api/ | No | Generous |

---

## Error Handling

All modules use custom exceptions in a hierarchy:

```
LegalDataError (base)
├── RateLimitError       # 429 Too Many Requests → retry with backoff
├── NotFoundError        # 404 resource not found
├── AuthenticationError  # 401/403 invalid or missing credentials
├── ParseError           # Failed to parse response
└── APIError             # Generic API error
```

All async methods implement exponential backoff on transient errors (429, 503).

---

## Caching

By default, responses are cached in-memory with a 5-minute TTL. To use Redis:

```python
import redis.asyncio as redis

cache_client = redis.from_url(os.getenv("SINTRA_REDIS_URL"))
cl = CourtListenerClient(cache=cache_client, cache_ttl=300)
```

---

## Contributing

1. Add new source clients in `integrations/case_law/<source>_client.py`
2. Register the source in `CaseLawSearchEngine._search_<source>()` 
3. Add tests in `tests/test_<source>.py` with mocked HTTP responses
4. Export from `__init__.py`

---

## License

Part of SintraPrime-Unified. Internal use only.
