"""
State Court Navigator
=====================
Navigate all 50 state court systems plus DC and territories.

Provides:
- State court hierarchy metadata
- CourtListener court IDs for each state court
- Links to official state court websites and portals
- State-specific search endpoints
- Jurisdiction mapping utilities
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StateCourt:
    """Represents a state court."""

    state: str
    state_abbr: str
    court_name: str
    court_level: str  # supreme, appellate, trial, specialty
    courtlistener_id: Optional[str]
    official_url: Optional[str]
    filing_url: Optional[str]
    case_search_url: Optional[str]
    opinions_online: bool = False
    notes: str = ""


@dataclass
class StateJurisdiction:
    """Complete court hierarchy for a state."""

    state: str
    state_abbr: str
    capital: str
    courts: List[StateCourt] = field(default_factory=list)

    def get_supreme_court(self) -> Optional[StateCourt]:
        for c in self.courts:
            if c.court_level == "supreme":
                return c
        return None

    def get_appellate_courts(self) -> List[StateCourt]:
        return [c for c in self.courts if c.court_level == "appellate"]

    def get_courtlistener_ids(self) -> List[str]:
        return [c.courtlistener_id for c in self.courts if c.courtlistener_id]


# ---------------------------------------------------------------------------
# Comprehensive state court database
# ---------------------------------------------------------------------------

# Each state entry: (state_abbr, capital, [(name, level, cl_id, url)])
_STATE_DATA: List[Tuple[str, str, str, List[Tuple[str, str, Optional[str], Optional[str]]]]] = [
    ("Alabama", "AL", "Montgomery", [
        ("Alabama Supreme Court", "supreme", "ala", "https://judicial.alabama.gov"),
        ("Alabama Court of Criminal Appeals", "appellate", "alacrimapp", "https://judicial.alabama.gov"),
        ("Alabama Court of Civil Appeals", "appellate", "alacivapp", "https://judicial.alabama.gov"),
    ]),
    ("Alaska", "AK", "Juneau", [
        ("Alaska Supreme Court", "supreme", "alaska", "https://courts.alaska.gov"),
        ("Alaska Court of Appeals", "appellate", "alaskactapp", "https://courts.alaska.gov"),
    ]),
    ("Arizona", "AZ", "Phoenix", [
        ("Arizona Supreme Court", "supreme", "ariz", "https://www.azcourts.gov"),
        ("Arizona Court of Appeals, Division One", "appellate", "arizctapp", "https://www.azcourts.gov"),
        ("Arizona Court of Appeals, Division Two", "appellate", "arizctappdiv2", "https://www.azcourts.gov"),
    ]),
    ("Arkansas", "AR", "Little Rock", [
        ("Arkansas Supreme Court", "supreme", "ark", "https://courts.arkansas.gov"),
        ("Arkansas Court of Appeals", "appellate", "arkctapp", "https://courts.arkansas.gov"),
    ]),
    ("California", "CA", "Sacramento", [
        ("California Supreme Court", "supreme", "cal", "https://www.courts.ca.gov"),
        ("California Court of Appeal, First Appellate District", "appellate", "calctapp", "https://www.courts.ca.gov"),
        ("California Court of Appeal, Second Appellate District", "appellate", "calctapp2", "https://www.courts.ca.gov"),
        ("California Court of Appeal, Third Appellate District", "appellate", "calctapp3", "https://www.courts.ca.gov"),
        ("California Court of Appeal, Fourth Appellate District", "appellate", "calctapp4", "https://www.courts.ca.gov"),
        ("California Court of Appeal, Fifth Appellate District", "appellate", "calctapp5", "https://www.courts.ca.gov"),
        ("California Court of Appeal, Sixth Appellate District", "appellate", "calctapp6", "https://www.courts.ca.gov"),
    ]),
    ("Colorado", "CO", "Denver", [
        ("Colorado Supreme Court", "supreme", "colo", "https://www.courts.state.co.us"),
        ("Colorado Court of Appeals", "appellate", "coloctapp", "https://www.courts.state.co.us"),
    ]),
    ("Connecticut", "CT", "Hartford", [
        ("Connecticut Supreme Court", "supreme", "conn", "https://www.jud.ct.gov"),
        ("Connecticut Appellate Court", "appellate", "connappct", "https://www.jud.ct.gov"),
    ]),
    ("Delaware", "DE", "Dover", [
        ("Delaware Supreme Court", "supreme", "del", "https://courts.delaware.gov"),
        ("Delaware Superior Court", "trial", "delsuperct", "https://courts.delaware.gov"),
        ("Delaware Court of Chancery", "specialty", "delch", "https://courts.delaware.gov"),
    ]),
    ("Florida", "FL", "Tallahassee", [
        ("Florida Supreme Court", "supreme", "fla", "https://www.floridasupremecourt.org"),
        ("Florida District Court of Appeal, First District", "appellate", "fladistctapp", "https://www.1dca.org"),
        ("Florida District Court of Appeal, Second District", "appellate", "fladistctapp2", "https://www.2dca.org"),
        ("Florida District Court of Appeal, Third District", "appellate", "fladistctapp3", "https://www.3dca.org"),
        ("Florida District Court of Appeal, Fourth District", "appellate", "fladistctapp4", "https://www.4dca.org"),
        ("Florida District Court of Appeal, Fifth District", "appellate", "fladistctapp5", "https://www.5dca.org"),
    ]),
    ("Georgia", "GA", "Atlanta", [
        ("Georgia Supreme Court", "supreme", "ga", "https://www.gasupreme.us"),
        ("Georgia Court of Appeals", "appellate", "gactapp", "https://www.gaappeals.us"),
    ]),
    ("Hawaii", "HI", "Honolulu", [
        ("Hawaii Supreme Court", "supreme", "haw", "https://www.courts.state.hi.us"),
        ("Hawaii Intermediate Court of Appeals", "appellate", "hawapp", "https://www.courts.state.hi.us"),
    ]),
    ("Idaho", "ID", "Boise", [
        ("Idaho Supreme Court", "supreme", "idaho", "https://isc.idaho.gov"),
        ("Idaho Court of Appeals", "appellate", "idahoctapp", "https://isc.idaho.gov"),
    ]),
    ("Illinois", "IL", "Springfield", [
        ("Illinois Supreme Court", "supreme", "ill", "https://www.illinoiscourts.gov"),
        ("Illinois Appellate Court, First District", "appellate", "illappct", "https://www.illinoiscourts.gov"),
    ]),
    ("Indiana", "IN", "Indianapolis", [
        ("Indiana Supreme Court", "supreme", "ind", "https://www.in.gov/courts"),
        ("Indiana Court of Appeals", "appellate", "indctapp", "https://www.in.gov/courts"),
        ("Indiana Tax Court", "specialty", "indtc", "https://www.in.gov/courts"),
    ]),
    ("Iowa", "IA", "Des Moines", [
        ("Iowa Supreme Court", "supreme", "iowa", "https://www.iowacourts.gov"),
        ("Iowa Court of Appeals", "appellate", "iowactapp", "https://www.iowacourts.gov"),
    ]),
    ("Kansas", "KS", "Topeka", [
        ("Kansas Supreme Court", "supreme", "kan", "https://www.kscourts.org"),
        ("Kansas Court of Appeals", "appellate", "kanctapp", "https://www.kscourts.org"),
    ]),
    ("Kentucky", "KY", "Frankfort", [
        ("Kentucky Supreme Court", "supreme", "ky", "https://courts.ky.gov"),
        ("Kentucky Court of Appeals", "appellate", "kyctapp", "https://courts.ky.gov"),
    ]),
    ("Louisiana", "LA", "Baton Rouge", [
        ("Louisiana Supreme Court", "supreme", "la", "https://www.lasc.org"),
        ("Louisiana Court of Appeal, First Circuit", "appellate", "lactapp", "https://www.la-fcca.org"),
    ]),
    ("Maine", "ME", "Augusta", [
        ("Maine Supreme Judicial Court", "supreme", "me", "https://www.courts.maine.gov"),
    ]),
    ("Maryland", "MD", "Annapolis", [
        ("Maryland Court of Appeals", "supreme", "md", "https://www.courts.state.md.us"),
        ("Maryland Appellate Court", "appellate", "mdctspecapp", "https://www.courts.state.md.us"),
    ]),
    ("Massachusetts", "MA", "Boston", [
        ("Massachusetts Supreme Judicial Court", "supreme", "mass", "https://www.mass.gov/courts"),
        ("Massachusetts Appeals Court", "appellate", "massappct", "https://www.mass.gov/courts"),
    ]),
    ("Michigan", "MI", "Lansing", [
        ("Michigan Supreme Court", "supreme", "mich", "https://www.courts.michigan.gov"),
        ("Michigan Court of Appeals", "appellate", "michctapp", "https://www.courts.michigan.gov"),
    ]),
    ("Minnesota", "MN", "Saint Paul", [
        ("Minnesota Supreme Court", "supreme", "minn", "https://www.mncourts.gov"),
        ("Minnesota Court of Appeals", "appellate", "minnctapp", "https://www.mncourts.gov"),
    ]),
    ("Mississippi", "MS", "Jackson", [
        ("Mississippi Supreme Court", "supreme", "miss", "https://www.courts.ms.gov"),
        ("Mississippi Court of Appeals", "appellate", "missctapp", "https://www.courts.ms.gov"),
    ]),
    ("Missouri", "MO", "Jefferson City", [
        ("Missouri Supreme Court", "supreme", "mo", "https://www.courts.mo.gov"),
        ("Missouri Court of Appeals, Eastern District", "appellate", "moctapp", "https://www.courts.mo.gov"),
    ]),
    ("Montana", "MT", "Helena", [
        ("Montana Supreme Court", "supreme", "mont", "https://courts.mt.gov"),
    ]),
    ("Nebraska", "NE", "Lincoln", [
        ("Nebraska Supreme Court", "supreme", "neb", "https://www.supremecourt.ne.gov"),
        ("Nebraska Court of Appeals", "appellate", "nebctapp", "https://www.supremecourt.ne.gov"),
    ]),
    ("Nevada", "NV", "Carson City", [
        ("Nevada Supreme Court", "supreme", "nev", "https://nvcourts.gov"),
        ("Nevada Court of Appeals", "appellate", "nevapp", "https://nvcourts.gov"),
    ]),
    ("New Hampshire", "NH", "Concord", [
        ("New Hampshire Supreme Court", "supreme", "nh", "https://www.courts.state.nh.us"),
    ]),
    ("New Jersey", "NJ", "Trenton", [
        ("New Jersey Supreme Court", "supreme", "nj", "https://www.njcourts.gov"),
        ("New Jersey Superior Court, Appellate Division", "appellate", "njsuperctappdiv", "https://www.njcourts.gov"),
    ]),
    ("New Mexico", "NM", "Santa Fe", [
        ("New Mexico Supreme Court", "supreme", "nm", "https://supremecourt.nmcourts.gov"),
        ("New Mexico Court of Appeals", "appellate", "nmctapp", "https://coa.nmcourts.gov"),
    ]),
    ("New York", "NY", "Albany", [
        ("New York Court of Appeals", "supreme", "ny", "https://www.nycourts.gov"),
        ("New York Supreme Court, Appellate Division, First Department", "appellate", "nyappdiv", "https://www.nycourts.gov"),
        ("New York Supreme Court, Appellate Division, Second Department", "appellate", "nyappdiv2", "https://www.nycourts.gov"),
        ("New York Supreme Court, Appellate Division, Third Department", "appellate", "nyappdiv3", "https://www.nycourts.gov"),
        ("New York Supreme Court, Appellate Division, Fourth Department", "appellate", "nyappdiv4", "https://www.nycourts.gov"),
    ]),
    ("North Carolina", "NC", "Raleigh", [
        ("North Carolina Supreme Court", "supreme", "nc", "https://www.nccourts.gov"),
        ("North Carolina Court of Appeals", "appellate", "ncctapp", "https://www.nccourts.gov"),
    ]),
    ("North Dakota", "ND", "Bismarck", [
        ("North Dakota Supreme Court", "supreme", "nd", "https://www.ndcourts.gov"),
    ]),
    ("Ohio", "OH", "Columbus", [
        ("Ohio Supreme Court", "supreme", "ohio", "https://www.supremecourt.ohio.gov"),
        ("Ohio Court of Appeals, First Appellate District", "appellate", "ohioctapp", "https://www.supremecourt.ohio.gov"),
    ]),
    ("Oklahoma", "OK", "Oklahoma City", [
        ("Oklahoma Supreme Court", "supreme", "okla", "https://www.oscn.net"),
        ("Oklahoma Court of Civil Appeals", "appellate", "oklacivapp", "https://www.oscn.net"),
        ("Oklahoma Court of Criminal Appeals", "appellate", "oklacrimapp", "https://www.oscn.net"),
    ]),
    ("Oregon", "OR", "Salem", [
        ("Oregon Supreme Court", "supreme", "or", "https://www.courts.oregon.gov"),
        ("Oregon Court of Appeals", "appellate", "orctapp", "https://www.courts.oregon.gov"),
    ]),
    ("Pennsylvania", "PA", "Harrisburg", [
        ("Pennsylvania Supreme Court", "supreme", "pa", "https://www.pacourts.us"),
        ("Pennsylvania Superior Court", "appellate", "pasuperct", "https://www.pacourts.us"),
        ("Pennsylvania Commonwealth Court", "appellate", "pacommwct", "https://www.pacourts.us"),
    ]),
    ("Rhode Island", "RI", "Providence", [
        ("Rhode Island Supreme Court", "supreme", "ri", "https://www.courts.ri.gov"),
    ]),
    ("South Carolina", "SC", "Columbia", [
        ("South Carolina Supreme Court", "supreme", "sc", "https://www.sccourts.org"),
        ("South Carolina Court of Appeals", "appellate", "scctapp", "https://www.sccourts.org"),
    ]),
    ("South Dakota", "SD", "Pierre", [
        ("South Dakota Supreme Court", "supreme", "sd", "https://ujs.sd.gov"),
    ]),
    ("Tennessee", "TN", "Nashville", [
        ("Tennessee Supreme Court", "supreme", "tenn", "https://www.tncourts.gov"),
        ("Tennessee Court of Appeals", "appellate", "tennctapp", "https://www.tncourts.gov"),
        ("Tennessee Court of Criminal Appeals", "appellate", "tenncrimapp", "https://www.tncourts.gov"),
    ]),
    ("Texas", "TX", "Austin", [
        ("Texas Supreme Court", "supreme", "tex", "https://www.txcourts.gov"),
        ("Texas Court of Criminal Appeals", "supreme", "texcrimapp", "https://www.txcourts.gov"),
        ("Texas Courts of Appeals, First District", "appellate", "texapp", "https://www.txcourts.gov"),
    ]),
    ("Utah", "UT", "Salt Lake City", [
        ("Utah Supreme Court", "supreme", "utah", "https://www.utcourts.gov"),
        ("Utah Court of Appeals", "appellate", "utahctapp", "https://www.utcourts.gov"),
    ]),
    ("Vermont", "VT", "Montpelier", [
        ("Vermont Supreme Court", "supreme", "vt", "https://www.vermontjudiciary.org"),
    ]),
    ("Virginia", "VA", "Richmond", [
        ("Virginia Supreme Court", "supreme", "va", "https://www.vacourts.gov"),
        ("Virginia Court of Appeals", "appellate", "vactapp", "https://www.vacourts.gov"),
    ]),
    ("Washington", "WA", "Olympia", [
        ("Washington Supreme Court", "supreme", "wash", "https://www.courts.wa.gov"),
        ("Washington Court of Appeals, Division One", "appellate", "washctapp", "https://www.courts.wa.gov"),
        ("Washington Court of Appeals, Division Two", "appellate", "washctapp2", "https://www.courts.wa.gov"),
        ("Washington Court of Appeals, Division Three", "appellate", "washctapp3", "https://www.courts.wa.gov"),
    ]),
    ("West Virginia", "WV", "Charleston", [
        ("West Virginia Supreme Court of Appeals", "supreme", "wva", "https://www.courtswv.gov"),
    ]),
    ("Wisconsin", "WI", "Madison", [
        ("Wisconsin Supreme Court", "supreme", "wis", "https://www.wicourts.gov"),
        ("Wisconsin Court of Appeals, District I", "appellate", "wisctapp", "https://www.wicourts.gov"),
    ]),
    ("Wyoming", "WY", "Cheyenne", [
        ("Wyoming Supreme Court", "supreme", "wyo", "https://www.courts.state.wy.us"),
    ]),
    # DC and territories
    ("District of Columbia", "DC", "Washington", [
        ("District of Columbia Court of Appeals", "supreme", "dc", "https://www.dccourts.gov"),
    ]),
    ("Puerto Rico", "PR", "San Juan", [
        ("Puerto Rico Supreme Court", "supreme", "pr", "https://www.ramajudicial.pr"),
    ]),
]


def _build_jurisdiction_registry() -> Dict[str, StateJurisdiction]:
    registry: Dict[str, StateJurisdiction] = {}
    for state_name, abbr, capital, courts_data in _STATE_DATA:
        courts = [
            StateCourt(
                state=state_name,
                state_abbr=abbr,
                court_name=name,
                court_level=level,
                courtlistener_id=cl_id,
                official_url=url,
                filing_url=None,
                case_search_url=None,
                opinions_online=cl_id is not None,
            )
            for name, level, cl_id, url in courts_data
        ]
        registry[abbr] = StateJurisdiction(
            state=state_name,
            state_abbr=abbr,
            capital=capital,
            courts=courts,
        )
    return registry


_JURISDICTION_REGISTRY: Dict[str, StateJurisdiction] = _build_jurisdiction_registry()


class StateCourtNavigator:
    """
    Navigate and query all 50-state court systems.

    Usage:
        nav = StateCourtNavigator()
        ca_courts = nav.get_state("CA")
        scotus_ids = nav.get_all_supreme_court_ids()
    """

    def get_state(self, state_abbr: str) -> Optional[StateJurisdiction]:
        """Get the court hierarchy for a state by abbreviation."""
        return _JURISDICTION_REGISTRY.get(state_abbr.upper())

    def get_all_states(self) -> List[StateJurisdiction]:
        """Get all state jurisdictions."""
        return list(_JURISDICTION_REGISTRY.values())

    def get_all_supreme_court_ids(self) -> List[str]:
        """Get CourtListener IDs for all state supreme courts."""
        ids = []
        for j in _JURISDICTION_REGISTRY.values():
            sc = j.get_supreme_court()
            if sc and sc.courtlistener_id:
                ids.append(sc.courtlistener_id)
        return ids

    def get_all_appellate_court_ids(self) -> List[str]:
        """Get CourtListener IDs for all state appellate courts."""
        ids = []
        for j in _JURISDICTION_REGISTRY.values():
            for court in j.get_appellate_courts():
                if court.courtlistener_id:
                    ids.append(court.courtlistener_id)
        return ids

    def find_court_by_id(self, courtlistener_id: str) -> Optional[StateCourt]:
        """Look up a court by its CourtListener ID."""
        for j in _JURISDICTION_REGISTRY.values():
            for court in j.courts:
                if court.courtlistener_id == courtlistener_id:
                    return court
        return None

    def get_courts_by_level(self, level: str) -> List[StateCourt]:
        """Get all courts of a given level (supreme, appellate, trial, specialty)."""
        results = []
        for j in _JURISDICTION_REGISTRY.values():
            for court in j.courts:
                if court.court_level == level:
                    results.append(court)
        return results

    def search_courts(self, query: str) -> List[StateCourt]:
        """Search for courts by name."""
        query_lower = query.lower()
        results = []
        for j in _JURISDICTION_REGISTRY.values():
            for court in j.courts:
                if query_lower in court.court_name.lower():
                    results.append(court)
        return results

    def get_state_from_court_id(self, courtlistener_id: str) -> Optional[str]:
        """Return state abbreviation for a given court ID."""
        court = self.find_court_by_id(courtlistener_id)
        return court.state_abbr if court else None

    def list_state_abbreviations(self) -> List[str]:
        """Get a sorted list of all state abbreviations."""
        return sorted(_JURISDICTION_REGISTRY.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Export the full registry as a dict."""
        return {
            abbr: {
                "state": j.state,
                "capital": j.capital,
                "courts": [
                    {
                        "name": c.court_name,
                        "level": c.court_level,
                        "courtlistener_id": c.courtlistener_id,
                        "url": c.official_url,
                    }
                    for c in j.courts
                ],
            }
            for abbr, j in _JURISDICTION_REGISTRY.items()
        }
