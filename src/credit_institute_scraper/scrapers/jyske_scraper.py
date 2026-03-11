import logging
import json

from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class JyskeScraper(Scraper):
    @classmethod
    def clear_cache(cls):
        cls._class_data_cache = None

    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(product["loebetidAar"]),
                float(product["aktuelKurs"]),
                float(product["tilbudsKurs"]),
                float(product["maxAntalAfdragsfrieAar"]),
                float(product["kuponrenteProcent"]),
                product["isin"]
            ) for product in data["fastRenteProdukter"]
        ]

    @Scraper.scraper
    def parse_floating_rate_bonds(self, data) -> list[FloatingRateBondDataEntry]:
        return [
            FloatingRateBondDataEntry(
                self.institute.name,
                int(product["fastrenteperiode"]),
                0,
                float(product["vaegtetTilbudskursProcent"]),
            ) for product in data["variabelRenteProdukter"]
        ]

    @property
    def url(self) -> str:
        return "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.Jyske

    _class_data_cache: dict | None = None

    def get_data(self):
        # 1) Reuse cached payload across all JyskeScraper instances (fixed + floating)
        if JyskeScraper._class_data_cache is not None:
            return JyskeScraper._class_data_cache

        import os
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        
        API = "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"
        PAGE = "https://www.jyskebank.dk/bolig/realkreditkurser"
        ORIGIN = "https://www.jyskebank.dk/"
        UA = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) "
            "Gecko/20100101 Firefox/131.0"
        )
        exe = os.getenv("FIREFOX_EXECUTABLE_PATH")

        with sync_playwright() as p:
            try:
                # 2) Try lightweight API context first (no browser process)
                req_ctx = p.request.new_context(
                    user_agent=UA,
                    extra_http_headers={
                        "accept": "application/json, text/plain, */*",
                        "origin": ORIGIN.rstrip("/"),
                        "referer": PAGE,
                    },
                )
                try:
                    resp = req_ctx.get(API, max_redirects=3, timeout=30000)
                    if resp.ok:
                        logging.info("Jyske: got data via lightweight APIRequestContext (%s)", resp.status)
                        JyskeScraper._class_data_cache = resp.json()
                        return JyskeScraper._class_data_cache
                    logging.warning("Jyske: lightweight APIRequestContext returned HTTP %s", resp.status)
                finally:
                    req_ctx.dispose()

                # 3) Fallback: run real browser session and fetch from page context
                browser = p.firefox.launch(
                    executable_path=exe or None,
                    headless=True,
                    args=["-headless"],
                )
                ctx = None
                page = None

                # 4) Create context
                ctx = browser.new_context(locale="da-DK", user_agent=UA)

                # Light stealth
                ctx.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'languages', { get: () => ['da-DK','da','en-US','en'] });
                    Object.defineProperty(navigator, 'platform',  { get: () => 'Win32' });
                """)

                # 5) Block heavy/3rd-party requests up front
                BLOCK_TYPES = {"image", "media", "font", "stylesheet"}
                BLOCK_HOSTS = (
                    "doubleclick.net", "google-analytics.com", "googletagmanager.com",
                    "facebook.com", "facebook.net", "hotjar.com", "azure.com",
                    "optimizely.com", "cdn.segment.com",
                )

                def _route(route, req):
                    url = req.url
                    if req.resource_type in BLOCK_TYPES or any(h in url for h in BLOCK_HOSTS):
                        return route.abort()
                    return route.continue_()

                ctx.route("**/*", _route)

                page = ctx.new_page()

                logging.debug("Jyske: navigating to kursliste page")
                page.goto(PAGE, wait_until="domcontentloaded")

                # Accept cookies if present (best-effort)
                for sel in ("button:has-text('Acceptér alle')",
                            "button:has-text('Accepter')",
                            "[data-testid='uc-accept-all']"):
                    try:
                        page.locator(sel).first.click(timeout=350)
                        logging.debug("Jyske: clicked cookie button %s", sel)
                        break
                    except Exception:
                        pass

                # Let the page settle a bit
                try:
                    page.wait_for_load_state("networkidle", timeout=30000)
                except PWTimeout:
                    logging.debug("Jyske: networkidle timeout, continue anyway")

                # Small nudge
                try:
                    page.evaluate("window.scrollTo(0, 600)")
                    page.evaluate("window.scrollTo(0, 0)")
                except Exception:
                    pass

                # Fetch from page JS context (avoids Firefox response-body protocol errors)
                raw = page.evaluate(
                    """
                    async (apiUrl) => {
                        const resp = await fetch(apiUrl, {
                            method: 'GET',
                            credentials: 'include',
                            headers: { 'accept': 'application/json, text/plain, */*' }
                        });
                        const text = await resp.text();
                        return { ok: resp.ok, status: resp.status, text };
                    }
                    """,
                    API,
                )
                if raw.get("ok"):
                    JyskeScraper._class_data_cache = json.loads(raw["text"])
                    logging.info("Jyske: got data from in-page fetch")
                    return JyskeScraper._class_data_cache

                logging.warning("Jyske: in-page fetch returned HTTP %s, trying context.request fallback", raw.get("status"))

                # 6) Context-request fallback (shares browser context cookies)
                resp = ctx.request.get(
                    API,
                    headers={
                        "accept": "application/json, text/plain, */*",
                        "origin": ORIGIN.rstrip("/"),
                        "referer": PAGE,
                    },
                    max_redirects=3,
                    timeout=45000,
                )
                if resp.ok:
                    logging.info("Jyske: got data via APIRequestContext (%s)", resp.status)
                    JyskeScraper._class_data_cache = resp.json()
                    return JyskeScraper._class_data_cache

                # Non-2xx HTTP response
                text_snippet = resp.text()[:180]
                raise RuntimeError(
                    f"Jyske kursliste HTTP error: {resp.status} {text_snippet}"
                )

            except Exception as e:
                # This is what your decorator will log as "Scraping 'Jyske' failed ..."
                logging.exception("Jyske: unrecoverable error in get_data: %s", e)
                raise
            finally:
                if "page" in locals() and page:
                    page.close()
                if "ctx" in locals() and ctx:
                    ctx.close()
                if "browser" in locals() and browser:
                    browser.close()
