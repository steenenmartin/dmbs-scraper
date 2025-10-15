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
        API  = "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"
        ORIGIN = "https://www.jyskebank.dk/"
        PAGE   = "https://www.jyskebank.dk/bolig/realkreditkurser"
        with sync_playwright() as p:
            browser = p.firefox.launch(
                executable_path=os.getenv("FIREFOX_EXECUTABLE_PATH"),
                headless=True,
                args=["-headless"],   # safe in containers
            )
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
    
            ctx = browser.new_context(locale="da-DK", user_agent=ua)
    
            # Light stealth: remove webdriver flag etc.
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                try { window.chrome = window.chrome || { runtime: {} }; } catch (e) {}
                Object.defineProperty(navigator, 'languages', { get: () => ['da-DK','da','en-US','en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            """)
    
            page = ctx.new_page()
            page.goto(PAGE, wait_until="domcontentloaded")
    
            page.wait_for_load_state("networkidle")
            time.sleep(1.0)
    
            fetch_script = """
                async ({ url, ref }) => {
                    const doFetch = async () => {
                        const r = await fetch(url, {
                            headers: { "accept": "application/json" },
                            credentials: "include",
                            referrer: ref,
                            referrerPolicy: "strict-origin"
                        });
                        if (!r.ok) return { ok:false, status:r.status, text: await r.text() };
                        return { ok:true, json: await r.json() };
                    };
                    let lastErr = null;
                    for (let i = 0; i < 3; i++) {
                        try { return await doFetch(); }
                        catch (e) { lastErr = String(e); await new Promise(r => setTimeout(r, 800)); }
                    }
                    return { ok:false, error:lastErr || "unknown error" };
                }
            """
            res = page.evaluate(fetch_script, {"url": API, "ref": ORIGIN})
            browser.close()
                
        return res["json"]
