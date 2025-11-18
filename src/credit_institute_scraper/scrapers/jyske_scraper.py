import logging

from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class JyskeScraper(Scraper):
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

    _data_cache: dict | None = None

    def get_data(self):
        # 1) Reuse cached payload for both parse_* calls
        if self._data_cache is not None:
            return self._data_cache

        import os, time
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
            browser = p.firefox.launch(
                executable_path=exe or None,
                headless=True,
                args=["-headless"],
            )
            ctx = None
            page = None
            try:
                # 2) Create context
                ctx = browser.new_context(locale="da-DK", user_agent=UA)

                # Light stealth
                ctx.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'languages', { get: () => ['da-DK','da','en-US','en'] });
                    Object.defineProperty(navigator, 'platform',  { get: () => 'Win32' });
                """)

                # 3) Block heavy/3rd-party requests up front
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

                # ---- Strategy 1: hook the page's own XHR ----
                captured: dict[str, dict | None] = {"data": None}

                def on_resp(r):
                    if r.url == API and r.status == 200:
                        try:
                            captured["data"] = r.json()
                        except Exception as e:
                            logging.warning("Jyske: failed to parse JSON from XHR: %s", e)

                ctx.on("response", on_resp)

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

                # Wait up to 60s for XHR to show up
                end = time.time() + 60
                while captured["data"] is None and time.time() < end:
                    page.wait_for_timeout(250)

                if captured["data"] is not None:
                    logging.info("Jyske: got data from page XHR")
                    self._data_cache = captured["data"]
                    return self._data_cache

                logging.warning("Jyske: XHR did not appear within 60s, using direct API fallback")

                # ---- Strategy 2: context.request.get (shares cookies with ctx) ----
                resp = ctx.request.get(
                    API,
                    headers={"accept": "application/json"},
                    max_redirects=3,
                    timeout=45000,
                )
                if resp.ok:
                    logging.info("Jyske: got data via APIRequestContext (%s)", resp.status)
                    self._data_cache = resp.json()
                    return self._data_cache

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
                try:
                    if page:
                        page.close()
                finally:
                    try:
                        if ctx:
                            ctx.close()
                    finally:
                        browser.close()
