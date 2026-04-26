"""
BrowserController – Web browser automation for SintraPrime Operator Mode.

Inspired by OpenAI Operator and Claude Computer Use.
Uses Playwright when available, falls back to requests + BeautifulSoup.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin, urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing Playwright; fall back gracefully
# ---------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT_AVAILABLE = False
    Page = Any  # type: ignore
    Browser = Any  # type: ignore

# ---------------------------------------------------------------------------
# Try importing requests + BeautifulSoup fallback
# ---------------------------------------------------------------------------
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False


POLITE_DELAY_SECONDS = 1.0  # minimum wait between requests
SCREENSHOT_DIR = "/tmp/sintra_screenshots"


@dataclass
class SearchResult:
    """A single search engine result."""
    title: str
    url: str
    snippet: str
    rank: int = 0


@dataclass
class ActionResult:
    """Unified result from any browser action."""
    success: bool
    data: Any = None
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    url: str = ""
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self):
        return self.success


class BrowserController:
    """
    High-level browser automation controller.

    Prefers Playwright for full JS rendering; falls back to requests+BS4
    for static pages. All actions return ActionResult for uniform handling.

    Example:
        bc = BrowserController(headless=True)
        result = bc.navigate("https://www.avvo.com")
        if result:
            text = bc.extract_text("h1")
            print(text.data)
        bc.close()
    """

    def __init__(
        self,
        headless: bool = True,
        screenshot_dir: str = SCREENSHOT_DIR,
        polite_delay: float = POLITE_DELAY_SECONDS,
        user_agent: str = (
            "Mozilla/5.0 (compatible; SintraPrimeBot/1.0; +https://sintraprime.com)"
        ),
    ):
        self.headless = headless
        self.screenshot_dir = screenshot_dir
        self.polite_delay = polite_delay
        self.user_agent = user_agent

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._last_request_time: float = 0.0
        self._session: Optional[requests.Session] = None

        os.makedirs(self.screenshot_dir, exist_ok=True)

        if PLAYWRIGHT_AVAILABLE:
            self._init_playwright()
        elif REQUESTS_AVAILABLE:
            self._init_requests()
        else:
            logger.warning(
                "Neither Playwright nor requests is available. "
                "Install one: pip install playwright requests beautifulsoup4"
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _init_playwright(self):
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            context = self._browser.new_context(user_agent=self.user_agent)
            self._page = context.new_page()
            logger.info("Playwright browser initialized.")
        except Exception as exc:
            logger.warning(f"Playwright init failed: {exc}. Falling back to requests.")
            self._playwright = None
            if REQUESTS_AVAILABLE:
                self._init_requests()

    def _init_requests(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})
        logger.info("Requests+BS4 fallback initialized.")

    def close(self):
        """Cleanly shut down browser resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            if self._session:
                self._session.close()
        except Exception as exc:
            logger.debug(f"Error during close: {exc}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _polite_wait(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.polite_delay:
            time.sleep(self.polite_delay - elapsed)
        self._last_request_time = time.time()

    # ------------------------------------------------------------------
    # Core actions
    # ------------------------------------------------------------------

    def navigate(self, url: str) -> ActionResult:
        """Navigate to a URL. Returns ActionResult with page title as data."""
        self._polite_wait()
        start = time.time()
        try:
            if self._page is not None:
                self._page.goto(url, wait_until="networkidle", timeout=30_000)
                title = self._page.title()
                return ActionResult(
                    success=True,
                    data={"title": title, "url": self._page.url},
                    url=self._page.url,
                    duration_seconds=time.time() - start,
                )
            elif self._session is not None:
                resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string if soup.title else ""
                return ActionResult(
                    success=True,
                    data={"title": title, "url": resp.url, "html": resp.text},
                    url=resp.url,
                    duration_seconds=time.time() - start,
                )
            else:
                return ActionResult(success=False, error="No browser backend available.", url=url)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), url=url,
                                duration_seconds=time.time() - start)

    def click(self, selector: str) -> ActionResult:
        """Click on a CSS selector or XPath element."""
        start = time.time()
        if self._page is None:
            return ActionResult(success=False, error="Playwright required for click()")
        try:
            self._page.click(selector, timeout=10_000)
            return ActionResult(
                success=True,
                data={"clicked": selector},
                url=self._page.url,
                duration_seconds=time.time() - start,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

    def type_text(self, selector: str, text: str, clear_first: bool = True) -> ActionResult:
        """Type text into a form field identified by selector."""
        start = time.time()
        if self._page is None:
            return ActionResult(success=False, error="Playwright required for type_text()")
        try:
            if clear_first:
                self._page.fill(selector, "")
            self._page.type(selector, text, delay=50)
            return ActionResult(
                success=True,
                data={"selector": selector, "text": text},
                url=self._page.url,
                duration_seconds=time.time() - start,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

    def extract_text(self, selector: str = "body") -> ActionResult:
        """Extract visible text from a CSS selector."""
        start = time.time()
        try:
            if self._page is not None:
                text = self._page.inner_text(selector)
                return ActionResult(
                    success=True, data=text, url=self._page.url,
                    duration_seconds=time.time() - start,
                )
            elif self._session is not None:
                # Assumes navigate() was called previously and HTML is in _last_html
                return ActionResult(success=False, error="No current page in requests mode.")
            else:
                return ActionResult(success=False, error="No browser backend available.")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

    def screenshot(self, full_page: bool = False) -> ActionResult:
        """Take a screenshot and save to disk. Returns the file path as data."""
        start = time.time()
        if self._page is None:
            return ActionResult(success=False, error="Playwright required for screenshot()")
        try:
            filename = f"{uuid.uuid4().hex}.png"
            path = os.path.join(self.screenshot_dir, filename)
            self._page.screenshot(path=path, full_page=full_page)
            return ActionResult(
                success=True, data=path, screenshot_path=path,
                url=self._page.url, duration_seconds=time.time() - start,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

    def scroll(self, direction: str = "down", pixels: int = 500) -> ActionResult:
        """Scroll the page. direction: 'up', 'down', 'top', 'bottom'."""
        start = time.time()
        if self._page is None:
            return ActionResult(success=False, error="Playwright required for scroll()")
        try:
            if direction == "down":
                self._page.evaluate(f"window.scrollBy(0, {pixels})")
            elif direction == "up":
                self._page.evaluate(f"window.scrollBy(0, -{pixels})")
            elif direction == "top":
                self._page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            return ActionResult(
                success=True, data={"direction": direction, "pixels": pixels},
                url=self._page.url, duration_seconds=time.time() - start,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

    def fill_form(self, fields: Dict[str, str]) -> ActionResult:
        """Fill multiple form fields. fields = {css_selector: value}."""
        results = {}
        all_ok = True
        for selector, value in fields.items():
            r = self.type_text(selector, value)
            results[selector] = r.success
            if not r.success:
                all_ok = False
        url = self._page.url if self._page else ""
        return ActionResult(
            success=all_ok,
            data=results,
            url=url,
            error=None if all_ok else "One or more fields failed.",
        )

    def submit_form(self, selector: str = '[type="submit"]') -> ActionResult:
        """Click the submit button and wait for navigation."""
        start = time.time()
        if self._page is None:
            return ActionResult(success=False, error="Playwright required for submit_form()")
        try:
            with self._page.expect_navigation(timeout=15_000):
                self._page.click(selector)
            return ActionResult(
                success=True, data={"url_after": self._page.url},
                url=self._page.url, duration_seconds=time.time() - start,
            )
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

    def fill_and_submit(self, url: str, form_data: Dict[str, str]) -> ActionResult:
        """Navigate to URL, fill form, and submit. Convenience wrapper."""
        nav = self.navigate(url)
        if not nav:
            return nav
        fill = self.fill_form(form_data)
        if not fill:
            return fill
        return self.submit_form()

    # ------------------------------------------------------------------
    # Web Search
    # ------------------------------------------------------------------

    def search_web(self, query: str, max_results: int = 10) -> ActionResult:
        """
        Perform a multi-engine web search.
        Returns ActionResult with data = List[SearchResult].
        Tries DuckDuckGo HTML, falls back to Google if needed.
        """
        results: List[SearchResult] = []

        # Try DuckDuckGo first
        ddg_results = self._search_duckduckgo(query, max_results)
        if ddg_results:
            results.extend(ddg_results)

        # Supplement with Bing if not enough results
        if len(results) < max_results // 2:
            bing_results = self._search_bing(query, max_results - len(results))
            results.extend(bing_results)

        # Deduplicate by URL
        seen_urls: set = set()
        unique: List[SearchResult] = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                r.rank = len(unique) + 1
                unique.append(r)

        return ActionResult(
            success=len(unique) > 0,
            data=unique,
            error=None if unique else "No search results found.",
        )

    def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        """Scrape DuckDuckGo HTML search results."""
        if not REQUESTS_AVAILABLE:
            return []
        self._polite_wait()
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            resp = (self._session or requests).get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select(".result__body")[:max_results]:
                title_tag = item.select_one(".result__title a")
                snippet_tag = item.select_one(".result__snippet")
                if title_tag:
                    results.append(SearchResult(
                        title=title_tag.get_text(strip=True),
                        url=title_tag.get("href", ""),
                        snippet=snippet_tag.get_text(strip=True) if snippet_tag else "",
                    ))
            return results
        except Exception as exc:
            logger.debug(f"DuckDuckGo search error: {exc}")
            return []

    def _search_bing(self, query: str, max_results: int) -> List[SearchResult]:
        """Scrape Bing search results."""
        if not REQUESTS_AVAILABLE:
            return []
        self._polite_wait()
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select(".b_algo")[:max_results]:
                title_tag = item.select_one("h2 a")
                snippet_tag = item.select_one(".b_caption p")
                if title_tag:
                    results.append(SearchResult(
                        title=title_tag.get_text(strip=True),
                        url=title_tag.get("href", ""),
                        snippet=snippet_tag.get_text(strip=True) if snippet_tag else "",
                    ))
            return results
        except Exception as exc:
            logger.debug(f"Bing search error: {exc}")
            return []

    # ------------------------------------------------------------------
    # Data Extraction
    # ------------------------------------------------------------------

    def extract_structured_data(self, url: str, schema: Dict[str, str]) -> ActionResult:
        """
        Scrape a URL and extract structured data according to a schema.

        schema format: {field_name: css_selector}
        Returns ActionResult with data = {field_name: extracted_value}
        """
        self._polite_wait()
        start = time.time()

        # Navigate to URL
        nav = self.navigate(url)
        if not nav:
            return nav

        extracted: Dict[str, Any] = {}
        try:
            if self._page is not None:
                for field_name, selector in schema.items():
                    try:
                        elements = self._page.query_selector_all(selector)
                        if len(elements) == 1:
                            extracted[field_name] = elements[0].inner_text()
                        elif len(elements) > 1:
                            extracted[field_name] = [e.inner_text() for e in elements]
                        else:
                            extracted[field_name] = None
                    except Exception:
                        extracted[field_name] = None
            elif self._session is not None and nav.data and "html" in nav.data:
                soup = BeautifulSoup(nav.data["html"], "html.parser")
                for field_name, selector in schema.items():
                    elements = soup.select(selector)
                    if len(elements) == 1:
                        extracted[field_name] = elements[0].get_text(strip=True)
                    elif len(elements) > 1:
                        extracted[field_name] = [e.get_text(strip=True) for e in elements]
                    else:
                        extracted[field_name] = None
        except Exception as exc:
            return ActionResult(success=False, error=str(exc), duration_seconds=time.time() - start)

        return ActionResult(
            success=True, data=extracted, url=url,
            duration_seconds=time.time() - start,
        )

    # ------------------------------------------------------------------
    # Page Monitoring
    # ------------------------------------------------------------------

    def monitor_page(
        self,
        url: str,
        condition: str,
        interval: int = 60,
        max_checks: int = 60,
        callback=None,
    ) -> ActionResult:
        """
        Watch a page for a condition (text substring) to appear.

        Args:
            url: Page to monitor.
            condition: String to look for in page text.
            interval: Seconds between checks.
            max_checks: Maximum number of checks before giving up.
            callback: Optional callable(url, text) invoked when condition met.

        Returns:
            ActionResult with data={'found': True/False, 'checks': int}
        """
        checks = 0
        while checks < max_checks:
            self._polite_wait()
            nav = self.navigate(url)
            if nav:
                if self._page is not None:
                    content = self._page.content()
                elif nav.data and "html" in nav.data:
                    content = nav.data["html"]
                else:
                    content = ""

                if condition.lower() in content.lower():
                    logger.info(f"Condition '{condition}' met on {url} after {checks+1} checks.")
                    if callback:
                        callback(url, content)
                    return ActionResult(
                        success=True,
                        data={"found": True, "checks": checks + 1},
                        url=url,
                    )

            checks += 1
            if checks < max_checks:
                logger.debug(f"Monitor check {checks}/{max_checks}: condition not met, waiting {interval}s.")
                time.sleep(interval)

        return ActionResult(
            success=False,
            data={"found": False, "checks": checks},
            url=url,
            error=f"Condition '{condition}' not met after {max_checks} checks.",
        )
