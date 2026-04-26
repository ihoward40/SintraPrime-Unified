"""
Financial Data Connectors for SintraPrime-Unified (Legal Context).

Supports:
  - Plaid (extended with asset reports)
  - Yodlee API
  - Finicity API
  - EDGAR (SEC financial filings) — full connector
  - Bloomberg Law financial data
  - Bankruptcy filing search (PACER bankruptcy)

All credentials from environment variables.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


def _build_session(retries: int = 3) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Account:
    """A financial account."""

    account_id: str
    name: str
    institution: Optional[str] = None
    account_type: Optional[str] = None
    balance_current: Optional[float] = None
    balance_available: Optional[float] = None
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetReport:
    """Asset report — snapshot of all accounts and assets."""

    report_id: str
    generated_at: Optional[datetime] = None
    accounts: List[Account] = field(default_factory=list)
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    net_worth: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SECFiling:
    """A filing retrieved from SEC EDGAR."""

    accession_number: str
    company_name: str
    cik: str
    form_type: str
    filed_date: Optional[str] = None
    period_of_report: Optional[str] = None
    filing_url: Optional[str] = None
    documents: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BankruptcyCase:
    """A bankruptcy case from PACER."""

    case_id: str
    debtor_name: str
    chapter: str  # "7", "11", "13"
    filed_date: Optional[str] = None
    court: Optional[str] = None
    status: Optional[str] = None
    trustee: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Plaid (extended with asset reports)
# ---------------------------------------------------------------------------


class PlaidConnector:
    """
    Plaid API connector extended with asset report capabilities.

    Env vars:
        PLAID_CLIENT_ID
        PLAID_SECRET
        PLAID_ENV  (sandbox / development / production — default sandbox)
    """

    _ENVIRONMENTS = {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }

    def __init__(self) -> None:
        self._client_id = os.environ["PLAID_CLIENT_ID"]
        self._secret = os.environ["PLAID_SECRET"]
        env = os.getenv("PLAID_ENV", "sandbox").lower()
        self._base_url = self._ENVIRONMENTS.get(env, self._ENVIRONMENTS["sandbox"])
        self._session = _build_session()

    def _headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "PLAID-CLIENT-ID": self._client_id, "PLAID-SECRET": self._secret}

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._session.post(
            f"{self._base_url}{path}", json=payload, headers=self._headers(), timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def get_accounts(self, access_token: str) -> List[Account]:
        """Return all accounts for an access token."""
        data = self._post("/accounts/get", {"access_token": access_token})
        accounts = []
        for a in data.get("accounts", []):
            bal = a.get("balances", {})
            accounts.append(
                Account(
                    account_id=a.get("account_id", ""),
                    name=a.get("name", ""),
                    institution=data.get("item", {}).get("institution_id"),
                    account_type=a.get("type"),
                    balance_current=bal.get("current"),
                    balance_available=bal.get("available"),
                    currency=bal.get("iso_currency_code", "USD"),
                    metadata=a,
                )
            )
        return accounts

    def create_asset_report(
        self, access_tokens: List[str], days_requested: int = 730
    ) -> str:
        """Create an asset report and return its token."""
        data = self._post(
            "/asset_report/create",
            {"access_tokens": access_tokens, "days_requested": days_requested, "options": {}},
        )
        return data.get("asset_report_token", "")

    def get_asset_report(self, asset_report_token: str) -> AssetReport:
        """Retrieve a completed asset report."""
        data = self._post("/asset_report/get", {"asset_report_token": asset_report_token})
        report_data = data.get("report", {})
        accounts: List[Account] = []
        total_assets = 0.0
        for item in report_data.get("items", []):
            for a in item.get("accounts", []):
                bal = a.get("balances", {})
                current = float(bal.get("current") or 0)
                acc = Account(
                    account_id=a.get("account_id", ""),
                    name=a.get("name", ""),
                    account_type=a.get("type"),
                    balance_current=current,
                    balance_available=bal.get("available"),
                    currency=bal.get("iso_currency_code", "USD"),
                    metadata=a,
                )
                accounts.append(acc)
                if a.get("type") in ("depository", "investment"):
                    total_assets += current
        return AssetReport(
            report_id=report_data.get("report_id", ""),
            generated_at=datetime.utcnow(),
            accounts=accounts,
            total_assets=total_assets,
            net_worth=total_assets,
            metadata=report_data,
        )

    def get_transactions(self, access_token: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Return transactions for the given date range."""
        data = self._post(
            "/transactions/get",
            {"access_token": access_token, "start_date": start_date, "end_date": end_date},
        )
        return data.get("transactions", [])


# ---------------------------------------------------------------------------
# Yodlee
# ---------------------------------------------------------------------------


class YodleeConnector:
    """
    Yodlee Envestnet API connector.

    Env vars:
        YODLEE_CLIENT_ID
        YODLEE_SECRET
        YODLEE_BASE_URL  (default https://production.api.yodlee.com/ysl)
    """

    def __init__(self) -> None:
        self._client_id = os.environ["YODLEE_CLIENT_ID"]
        self._secret = os.environ["YODLEE_SECRET"]
        self._base_url = os.getenv("YODLEE_BASE_URL", "https://production.api.yodlee.com/ysl")
        self._session = _build_session()
        self._access_token: Optional[str] = None

    def authenticate(self, login_name: str = "admin") -> None:
        resp = self._session.post(
            f"{self._base_url}/auth/token",
            headers={
                "Api-Version": "1.1",
                "loginName": login_name,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"clientId": self._client_id, "secret": self._secret},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._access_token = resp.json().get("token", {}).get("accessToken")
        self._session.headers.update({"Authorization": f"Bearer {self._access_token}", "Api-Version": "1.1"})
        logger.info("Yodlee: authenticated")

    def get_accounts(self, user_session: str) -> List[Account]:
        self._session.headers["userSession"] = user_session
        resp = self._session.get(f"{self._base_url}/accounts", timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        accounts = []
        for a in resp.json().get("account", []):
            accounts.append(
                Account(
                    account_id=str(a.get("id", "")),
                    name=a.get("accountName", ""),
                    institution=a.get("providerName"),
                    account_type=a.get("accountType"),
                    balance_current=a.get("balance", {}).get("amount"),
                    currency=a.get("balance", {}).get("currency", "USD"),
                    metadata=a,
                )
            )
        return accounts

    def get_transactions(self, user_session: str, account_id: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        self._session.headers["userSession"] = user_session
        params = {"accountId": account_id, "fromDate": from_date, "toDate": to_date}
        resp = self._session.get(f"{self._base_url}/transactions", params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("transaction", [])

    def get_holdings(self, user_session: str) -> List[Dict[str, Any]]:
        self._session.headers["userSession"] = user_session
        resp = self._session.get(f"{self._base_url}/holdings", timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("holding", [])


# ---------------------------------------------------------------------------
# Finicity
# ---------------------------------------------------------------------------


class FinicityConnector:
    """
    Finicity (Mastercard Open Banking) API connector.

    Env vars:
        FINICITY_PARTNER_ID
        FINICITY_PARTNER_SECRET
        FINICITY_APP_KEY
        FINICITY_BASE_URL  (default https://api.finicity.com)
    """

    def __init__(self) -> None:
        self._partner_id = os.environ["FINICITY_PARTNER_ID"]
        self._partner_secret = os.environ["FINICITY_PARTNER_SECRET"]
        self._app_key = os.environ["FINICITY_APP_KEY"]
        self._base_url = os.getenv("FINICITY_BASE_URL", "https://api.finicity.com")
        self._session = _build_session()
        self._access_token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            f"{self._base_url}/aggregation/v2/partners/authentication",
            json={"partnerId": self._partner_id, "partnerSecret": self._partner_secret},
            headers={"Finicity-App-Key": self._app_key, "Content-Type": "application/json", "Accept": "application/json"},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._access_token = resp.json().get("token")
        self._session.headers.update(
            {"Finicity-App-Key": self._app_key, "Finicity-App-Token": self._access_token, "Accept": "application/json"}
        )
        logger.info("Finicity: authenticated")

    def get_accounts(self, customer_id: str) -> List[Account]:
        resp = self._session.get(
            f"{self._base_url}/aggregation/v1/customers/{customer_id}/accounts", timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        accounts = []
        for a in resp.json().get("accounts", []):
            accounts.append(
                Account(
                    account_id=str(a.get("id", "")),
                    name=a.get("name", ""),
                    institution=a.get("institutionId"),
                    account_type=a.get("type"),
                    balance_current=a.get("balance"),
                    currency="USD",
                    metadata=a,
                )
            )
        return accounts

    def generate_asset_report(self, customer_id: str, days: int = 365) -> Dict[str, Any]:
        resp = self._session.post(
            f"{self._base_url}/decisioning/v2/customers/{customer_id}/assetSummary",
            json={"reportCustomFields": []},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def get_transactions(self, customer_id: str, from_date: int, to_date: int) -> List[Dict[str, Any]]:
        resp = self._session.get(
            f"{self._base_url}/aggregation/v3/customers/{customer_id}/transactions",
            params={"fromDate": from_date, "toDate": to_date},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("transactions", [])


# ---------------------------------------------------------------------------
# EDGAR (SEC)
# ---------------------------------------------------------------------------


class EDGARConnector:
    """
    SEC EDGAR full connector — company search, filings, financial data.

    No API key required (public API), but rate limited to 10 req/sec.
    Env var:
        EDGAR_USER_AGENT  (required by SEC — your name/email)
    """

    _BASE_URL = "https://data.sec.gov"
    _EFTS_URL = "https://efts.sec.gov"
    _SUBMISSIONS_URL = "https://data.sec.gov/submissions"
    _COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self) -> None:
        self._user_agent = os.environ.get("EDGAR_USER_AGENT", "SintraPrime Research research@sintra.prime")
        self._session = _build_session()
        self._session.headers.update({"User-Agent": self._user_agent, "Accept": "application/json"})

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def get_company_cik(self, company_name: str) -> Optional[str]:
        """Search for a company's CIK by name using EDGAR full-text search."""
        url = f"{self._EFTS_URL}/hits.json"
        resp = self._get(url, params={"q": f'"{company_name}"', "dateRange": "custom", "forms": "10-K"})
        hits = resp.json().get("hits", {}).get("hits", [])
        if hits:
            return hits[0].get("_source", {}).get("entity_id")
        return None

    def get_submissions(self, cik: str) -> Dict[str, Any]:
        """Get all submissions for a CIK."""
        padded_cik = cik.zfill(10)
        url = f"{self._SUBMISSIONS_URL}/CIK{padded_cik}.json"
        resp = self._get(url)
        return resp.json()

    def search_filings(
        self,
        company_name: Optional[str] = None,
        cik: Optional[str] = None,
        form_type: str = "10-K",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
    ) -> List[SECFiling]:
        """Search for SEC filings by company or form type."""
        if cik:
            submissions = self.get_submissions(cik)
            company = submissions.get("name", company_name or "")
        else:
            company = company_name or ""
            cik = self.get_company_cik(company) or ""
            if not cik:
                return []
            submissions = self.get_submissions(cik)

        filings = submissions.get("filings", {}).get("recent", {})
        form_types = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        results: List[SECFiling] = []

        for i, ft in enumerate(form_types):
            if form_type and ft != form_type:
                continue
            acc_num = accession_numbers[i] if i < len(accession_numbers) else ""
            fd = filing_dates[i] if i < len(filing_dates) else ""
            if start_date and fd < start_date:
                continue
            if end_date and fd > end_date:
                continue
            acc_path = acc_num.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_path}/{acc_num}-index.htm"
            )
            results.append(
                SECFiling(
                    accession_number=acc_num,
                    company_name=company,
                    cik=cik,
                    form_type=ft,
                    filed_date=fd,
                    filing_url=filing_url,
                )
            )
            if len(results) >= limit:
                break

        return results

    def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Get XBRL company facts (financial data)."""
        padded_cik = cik.zfill(10)
        url = f"{self._BASE_URL}/api/xbrl/companyfacts/CIK{padded_cik}.json"
        resp = self._get(url)
        return resp.json()

    def get_concept(self, cik: str, taxonomy: str, concept: str) -> Dict[str, Any]:
        """Get a specific financial concept for a company."""
        padded_cik = cik.zfill(10)
        url = f"{self._BASE_URL}/api/xbrl/companyconcept/CIK{padded_cik}/{taxonomy}/{concept}.json"
        resp = self._get(url)
        return resp.json()


# ---------------------------------------------------------------------------
# Bloomberg Law Financial Data
# ---------------------------------------------------------------------------


class BloombergLawConnector:
    """
    Bloomberg Law financial data connector.

    Env vars:
        BLOOMBERG_LAW_API_KEY
        BLOOMBERG_LAW_BASE_URL  (default https://api.bloomberglaw.com)
    """

    def __init__(self) -> None:
        self._api_key = os.environ["BLOOMBERG_LAW_API_KEY"]
        self._base_url = os.getenv("BLOOMBERG_LAW_BASE_URL", "https://api.bloomberglaw.com")
        self._session = _build_session()

    def authenticate(self) -> None:
        self._session.headers.update(
            {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        )
        logger.info("Bloomberg Law: API key configured")

    def _get(self, path: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(f"{self._base_url}{path}", timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def get_company_financials(self, ticker: str) -> Dict[str, Any]:
        """Get financial data for a public company."""
        resp = self._get(f"/v1/company/{ticker}/financials")
        return resp.json()

    def get_dockets(self, company: str) -> List[Dict[str, Any]]:
        """Get litigation dockets for a company."""
        resp = self._get(f"/v1/dockets", params={"company": company})
        return resp.json().get("dockets", [])

    def search_transactions(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search M&A and deal transactions."""
        resp = self._get("/v1/transactions/search", params={"q": query, "limit": limit})
        return resp.json().get("transactions", [])


# ---------------------------------------------------------------------------
# Bankruptcy Filing Search (PACER Bankruptcy)
# ---------------------------------------------------------------------------


class PACERBankruptcyConnector:
    """
    PACER bankruptcy search connector.

    Extends the base PACER auth to search and retrieve bankruptcy filings.

    Env vars:
        PACER_USERNAME
        PACER_PASSWORD
        PACER_BASE_URL  (default https://pcl.uscourts.gov)
    """

    _AUTH_URL = "https://pacer.login.uscourts.gov/services/cso-auth"

    def __init__(self) -> None:
        self._username = os.environ["PACER_USERNAME"]
        self._password = os.environ["PACER_PASSWORD"]
        self._base_url = os.getenv("PACER_BASE_URL", "https://pcl.uscourts.gov")
        self._session = _build_session()
        self._token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            self._AUTH_URL,
            json={"loginId": self._username, "password": self._password, "redactFlag": "1"},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json().get("nextGenCSO") or resp.headers.get("X-NEXT-GEN-CSO")
        self._session.headers.update({"X-NEXT-GEN-CSO": self._token, "Accept": "application/json"})
        logger.info("PACER Bankruptcy: authenticated")

    def _get(self, path: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(f"{self._base_url}{path}", timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def search_cases(
        self,
        debtor_name: Optional[str] = None,
        ssn_or_ein: Optional[str] = None,
        chapter: Optional[str] = None,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 25,
    ) -> List[BankruptcyCase]:
        """Search bankruptcy cases by debtor name or other criteria."""
        params: Dict[str, Any] = {"limit": limit}
        if debtor_name:
            params["debtor"] = debtor_name
        if ssn_or_ein:
            params["ssn"] = ssn_or_ein
        if chapter:
            params["chapter"] = chapter
        if court:
            params["court"] = court
        if date_from:
            params["dateFiledFrom"] = date_from
        if date_to:
            params["dateFiledTo"] = date_to
        resp = self._get("/pcl-public-api/rest/cases/find", params=params)
        cases = []
        for item in resp.json().get("content", []):
            cases.append(
                BankruptcyCase(
                    case_id=item.get("caseId", ""),
                    debtor_name=item.get("partyName", ""),
                    chapter=item.get("chapter", ""),
                    filed_date=item.get("dateFiled"),
                    court=item.get("courtId"),
                    status=item.get("disposition"),
                    trustee=item.get("trustee"),
                    metadata=item,
                )
            )
        return cases

    def get_case_detail(self, case_id: str) -> Dict[str, Any]:
        """Get full details for a bankruptcy case."""
        resp = self._get(f"/pcl-public-api/rest/cases/{case_id}")
        return resp.json()

    def get_case_docket(self, case_id: str) -> List[Dict[str, Any]]:
        """Get docket entries for a bankruptcy case."""
        resp = self._get(f"/pcl-public-api/rest/cases/{case_id}/docket")
        return resp.json().get("docketEntries", [])

    def search_assets(self, case_id: str) -> List[Dict[str, Any]]:
        """Search assets listed in a bankruptcy case."""
        resp = self._get(f"/pcl-public-api/rest/cases/{case_id}/assets")
        return resp.json().get("assets", [])
