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
        with sync_playwright() as p:
            executable_path = os.getenv("CHROMIUM_EXECUTABLE_PATH", None)
    
            launch_kwargs = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                ],
            }
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
    
            browser = p.chromium.launch(**launch_kwargs)
            ctx = browser.new_context(
                locale="da-DK",
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) " "AppleWebKit/537.36 (KHTML, like Gecko) " "Chrome/120.0.0.0 Safari/537.36"),
            )
            page = ctx.new_page()
    
            page.goto(HOME, wait_until="networkidle")
            time.sleep(1.0)
    
            data = page.evaluate(
                """async (url) => {
                    const r = await fetch(url, {
                        headers: { "accept": "application/json" },
                        credentials: "include"
                    });
                    if (!r.ok) {
                        return { ok: false, status: r.status, text: await r.text() };
                    }
                    return { ok: true, json: await r.json() };
                }""",
                API
            )
            browser.close()
        return data["json"]
