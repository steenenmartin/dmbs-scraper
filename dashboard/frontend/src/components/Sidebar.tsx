import { NavLink } from "react-router-dom";

const navItems = [
  { path: "/", label: "Home", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { path: "/prices", label: "Fixed Loan Prices", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" },
  { path: "/rates", label: "Flex Loan Rates", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { path: "/ohlc", label: "OHLC Prices", icon: "M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <>
      <aside
        className={`fixed top-0 left-0 bottom-0 z-40 flex flex-col bg-gray-800 text-white transition-all duration-300 ${collapsed ? "-translate-x-full" : "translate-x-0"}`}
        style={{ width: "16rem" }}
      >
        <div className="px-6 py-6">
          <h1 className="text-lg font-semibold tracking-wide text-gray-100">
            DMBS Dashboard
          </h1>
          <p className="mt-1 text-xs text-gray-400">
            Danish Mortgage Bond Prices
          </p>
        </div>

        <nav className="mt-2 flex-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-gray-700 text-white"
                    : "text-gray-300 hover:bg-gray-700/50 hover:text-white"
                }`
              }
            >
              <svg
                className="h-5 w-5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d={item.icon}
                />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <button
        onClick={onToggle}
        className={`fixed bottom-4 z-50 flex h-8 w-8 items-center justify-center rounded-full bg-gray-800 text-white shadow-lg transition-all duration-300 hover:bg-gray-700 ${collapsed ? "left-4" : "left-[15rem]"}`}
      >
        <svg
          className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>
    </>
  );
}
