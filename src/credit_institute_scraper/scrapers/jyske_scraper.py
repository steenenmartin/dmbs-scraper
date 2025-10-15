import os, json, time
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

    def get_data(self):
    """
    Returns the kursliste JSON as a Python dict.
    Uses Firefox. On Heroku, set FIREFOX_EXECUTABLE_PATH (from the browsers buildpack).
    """    
    API  = "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"
    PAGE = "https://www.jyskebank.dk/bolig/realkreditkurser"
    ORIGIN = "https://www.jyskebank.dk/"
    UA   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"

    with sync_playwright() as p:
        browser = p.firefox.launch(
            executable_path=os.getenv("FIREFOX_EXECUTABLE_PATH"),
            headless=True,
            args=["-headless"],
        )
        try:
            ctx = browser.new_context(locale="da-DK", user_agent=UA)
            # light stealth
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['da-DK','da','en-US','en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            """)

            page = ctx.new_page()

            # ---- Strategy 1: capture the page's own XHR ----
            captured = {"data": None}
            def on_resp(r):
                if r.url == API and r.status == 200:
                    try:
                        captured["data"] = r.json()
                    except Exception:
                        pass
            ctx.on("response", on_resp)

            page.goto(PAGE, wait_until="domcontentloaded")

            # quick cookie-consent click if present (best-effort)
            for sel in ("button:has-text('Acceptér alle')",
                        "button:has-text('Accepter')",
                        "[data-testid='uc-accept-all']"):
                try:
                    page.locator(sel).first.click(timeout=400)
                    break
                except Exception:
                    pass

            page.wait_for_load_state("networkidle")
            # nudge some SPAs to refetch
            for _ in range(2):
                try:
                    page.evaluate("window.scrollTo(0, 800)")
                    page.evaluate("window.scrollTo(0, 0)")
                except Exception:
                    pass

            deadline = time.time() + (25000 / 1000.0)
            while captured["data"] is None and time.time() < deadline:
                page.wait_for_timeout(250)

            if captured["data"] is not None:
                return captured["data"]

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
                    for (let i=0;i<3;i++){
                        try { return await go(); }
                        catch { await new Promise(r=>setTimeout(r, 700)); }
                    }
                    return { ok:false, status:null, text:"fetch failed" };
                }
            """
            res = page.evaluate(fetch_script, {"url": API, "ref": "https://www.jyskebank.dk/"})
            if res.get("ok"):
                return res["json"]

            raise RuntimeError(f"Jyske kursliste fetch blocked: {res.get('status')} {str(res.get('text'))[:200]}")

        finally:
            browser.close()
