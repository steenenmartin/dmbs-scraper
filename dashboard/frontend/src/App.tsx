import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { SpotPricesPage } from "./components/SpotPricesPage";

function HomePage() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-lg">
        <h1 className="text-3xl font-semibold text-gray-800 mb-4">
          DMBS Dashboard
        </h1>
        <p className="text-gray-500 text-lg leading-relaxed">
          Real-time Danish mortgage-backed securities pricing dashboard.
          Navigate to{" "}
          <a href="/prices" className="text-blue-500 hover:text-blue-600 underline">
            Fixed Loan Prices
          </a>{" "}
          to view live bond spot prices.
        </p>
      </div>
    </div>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">{title}</h2>
        <p className="text-gray-400">Coming soon</p>
      </div>
    </div>
  );
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <main
        className="flex-1 overflow-auto p-6 transition-all duration-300"
        style={{ marginLeft: sidebarCollapsed ? 0 : "16rem" }}
      >
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/prices" element={<SpotPricesPage />} />
          <Route path="/daily" element={<SpotPricesPage />} />
          <Route path="/rates" element={<PlaceholderPage title="Flex Loan Rates" />} />
          <Route path="/ohlc" element={<PlaceholderPage title="OHLC Prices" />} />
        </Routes>
      </main>
    </div>
  );
}
