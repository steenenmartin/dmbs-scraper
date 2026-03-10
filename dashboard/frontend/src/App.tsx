import { useEffect, useState } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { SpotPricesPage } from "./components/SpotPricesPage";
import { FlexRatesPage } from "./components/FlexRatesPage";
import { OhlcPage } from "./components/OhlcPage";

const PAGE_TITLES: Record<string, string> = {
  "/": "Home",
  "/prices": "Prices",
  "/daily": "Prices",
  "/rates": "Rates",
  "/ohlc": "OHLC",
};

function HomePage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">Welcome to Bondstats</h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-600 sm:text-base">
          Bondstats features intra-day live updated fixed-rate Danish Mortgage Backed Securities
          (DMBS) spot prices.
        </p>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 sm:text-base">
          Prices are collected during exchange opening hours (09:00–17:00 Copenhagen time) from
          Nordea Kredit, Jyske Realkredit, Realkredit Danmark, and Totalkredit.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link to="/prices" className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100">
            Spot Prices
          </Link>
          <Link to="/rates" className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100">
            Flex Loan Rates
          </Link>
          <Link to="/ohlc" className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100">
            OHLC Prices
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">General information</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Featured prices are identical to the spot prices ("Aktuel kurs") shown by each credit
            institute for bonds currently open for loan payment.
          </p>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li><a className="underline" href="https://www.jyskebank.dk/bolig/boliglaan/kurser">Jyske Realkredit</a></li>
            <li><a className="underline" href="https://www.nordea.dk/privat/produkter/boliglaan/Kurser-realkreditlaan-kredit.html">Nordea Kredit</a></li>
            <li><a className="underline" href="https://rd.dk/kurser-og-renter">Realkredit Danmark</a></li>
            <li><a className="underline" href="https://www.totalkredit.dk/boliglan/kurser-og-priser/">Totalkredit</a></li>
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">User guide</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-600">
            <li>Use the sidebar to open Spot Prices, Flex Loan Rates, and OHLC Prices.</li>
            <li>Filter selections are stored in the URL so you can bookmark your preferred view.</li>
            <li>In OHLC view, first narrow down filters, then select one or more ISINs to plot.</li>
            <li>Historic mode is available on Spot Prices for longer-term context.</li>
          </ul>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">Disclaimer</h3>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          Bondstats reserves the right for errors and omissions in the information shown. Data is
          gathered directly from credit institutes, and decisions should be verified with official
          sources.
        </p>
      </section>
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia("(min-width: 1024px)").matches : true
  );
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() =>
    typeof window !== "undefined" ? !window.matchMedia("(min-width: 1024px)").matches : false
  );

  useEffect(() => {
    const pageName = PAGE_TITLES[location.pathname] ?? "Bondstats";
    document.title = pageName === "Bondstats" ? "Bondstats" : `${pageName} | Bondstats`;

    if (typeof window !== "undefined" && typeof window.gtag === "function") {
      window.gtag("config", "G-V3RXS9EHBM", {
        page_path: `${location.pathname}${location.search}`,
        page_title: document.title,
      });
    }
  }, [location.pathname, location.search]);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const onChange = (event: MediaQueryListEvent) => {
      setIsDesktop(event.matches);
      setSidebarCollapsed(!event.matches);
    };

    setIsDesktop(media.matches);
    setSidebarCollapsed(!media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !isDesktop) return;

    const triggerResize = () => window.dispatchEvent(new Event("resize"));
    const timeout = window.setTimeout(triggerResize, 320);
    triggerResize();

    return () => window.clearTimeout(timeout);
  }, [isDesktop, sidebarCollapsed]);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
      />

      <main
        className="flex-1 overflow-auto p-3 transition-all duration-300 sm:p-4 lg:p-6"
        style={{ marginLeft: isDesktop && !sidebarCollapsed ? "16rem" : 0 }}
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/prices" element={<SpotPricesPage />} />
          <Route path="/daily" element={<SpotPricesPage />} />
          <Route path="/rates" element={<FlexRatesPage />} />
          <Route path="/ohlc" element={<OhlcPage />} />
        </Routes>
      </main>
    </div>
  );
}
