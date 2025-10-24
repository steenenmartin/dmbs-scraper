import os, time
from playwright.sync_api import sync_playwright

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

    _data_cache: dict | None = None  # add this

    def get_data(self):
        # 1) Reuse cached payload for both parse_* calls
        if self._data_cache is not None:
            return self._data_cache

        import os, time
        from playwright.sync_api import sync_playwright

        API = "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"
        PAGE = "https://www.jyskebank.dk/bolig/realkreditkurser"
        ORIGIN = "https://www.jyskebank.dk/"
        UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
        exe = os.getenv("FIREFOX_EXECUTABLE_PATH")  # set on Heroku

        with sync_playwright() as p:
            browser = p.firefox.launch(
                executable_path=exe if exe else None,
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
                    "optimizely.com", "cdn.segment.com"
                )

                def _route(route, req):
                    url = req.url
                    if req.resource_type in BLOCK_TYPES or any(h in url for h in BLOCK_HOSTS):
                        return route.abort()
                    return route.continue_()

                ctx.route("**/*", _route)

                page = ctx.new_page()

                # ---- Strategy 1: capture the page's own XHR (cheapest) ----
                captured = {"data": None}

                def on_resp(r):
                    if r.url == API and r.status == 200:
                        try:
                            captured["data"] = r.json()
                        except Exception:
                            pass

                ctx.on("response", on_resp)

                page.goto(PAGE, wait_until="domcontentloaded")

                # Accept cookies if present (best-effort)
                for sel in ("button:has-text('Acceptér alle')",
                            "button:has-text('Accepter')",
                            "[data-testid='uc-accept-all']"):
                    try:
                        page.locator(sel).first.click(timeout=350)
                        break
                    except Exception:
                        pass

                page.wait_for_load_state("networkidle")
                # Nudge some SPAs to refetch once
                try:
                    page.evaluate("window.scrollTo(0, 600)")
                    page.evaluate("window.scrollTo(0, 0)")
                except Exception:
                    pass

                # Wait up to ~60s (rare slow CF); check every 250ms
                end = time.time() + 60
                while captured["data"] is None and time.time() < end:
                    page.wait_for_timeout(250)

                if captured["data"] is not None:
                    self._data_cache = captured["data"]
                    return self._data_cache

                # ---- Strategy 2: fallback in-page fetch with proper referrer ----
                fetch_script = """
                    async ({ url, ref }) => {
                        const go = async () => {
                            const r = await fetch(url, {
                                headers: { "accept": "application/json" },
                                credentials: "include",
                                referrer: ref,
                                referrerPolicy: "strict-origin"
                            });
                            if (!r.ok) return { ok:false, status:r.status, text: await r.text() };
                            return { ok:true, json: await r.json() };
                        };
                        for (let i=0;i<2;i++){    // fewer retries; we already waited above
                            try { return await go(); }
                            catch { await new Promise(r=>setTimeout(r, 600)); }
                        }
                        return { ok:false, status:null, text:"fetch failed" };
                    }
                """
                res = page.evaluate(fetch_script, {"url": API, "ref": ORIGIN})
                if res.get("ok"):
                    self._data_cache = res["json"]
                    return self._data_cache

                raise RuntimeError(f"Jyske kursliste blocked: {res.get('status')} {str(res.get('text'))[:180]}")

            finally:
                # 4) Close aggressively to free RAM
                try:
                    if page: page.close()
                finally:
                    try:
                        if ctx: ctx.close()
                    finally:
                        browser.close()
