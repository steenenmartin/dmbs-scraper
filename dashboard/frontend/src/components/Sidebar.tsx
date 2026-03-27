import { NavLink } from "react-router-dom";
import { InstituteStatusPanel } from "./InstituteStatusPanel";
import { useInstituteStatus } from "../hooks/useInstituteStatus";

const navItems = [
  { path: "/", label: "Home", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
  { path: "/prices", label: "Fixed Loan Prices", iconSrc: "/icons/padlock.png", invertIcon: true },
  { path: "/rates", label: "Flex Loan Rates", iconSrc: "/icons/interest_rate.png", invertIcon: true },
  { path: "/ohlc", label: "OHLC Prices", icon: "M3 3v18h18M7 16V9m5 11V6m5 14v-8" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { status, loading } = useInstituteStatus();

  return (
    <>
      {!collapsed && (
        <button
          aria-label="Close sidebar backdrop"
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden"
          onClick={onToggle}
        />
      )}

      <aside
        className={`fixed bottom-0 left-0 top-0 z-40 flex w-64 flex-col border-r border-slate-700/40 bg-gray-800 text-white shadow-2xl transition-transform duration-300 ${collapsed ? "-translate-x-full" : "translate-x-0"}`}
      >
        <div className="flex items-center gap-3 px-6 py-6">
          <img src="/favicon.ico" alt="Bondstats logo" className="h-9 w-9 rounded-md invert" />
          <h1 className="text-lg font-semibold tracking-wide text-gray-100">Bondstats</h1>
        </div>

        <nav className="mt-2 space-y-1 px-3">
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
              onClick={() => {
                if (window.innerWidth < 1024) onToggle();
              }}
            >
              {item.iconSrc ? (
                <img
                  src={item.iconSrc}
                  alt=""
                  aria-hidden="true"
                  className={`h-5 w-5 shrink-0 object-contain ${item.invertIcon ? "invert" : ""}`}
                />
              ) : (
                <svg
                  className="h-5 w-5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                </svg>
              )}
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto px-3 pb-4">
          <InstituteStatusPanel status={status} loading={loading} inSidebar />
        </div>
      </aside>

      <button
        onClick={onToggle}
        className={`fixed bottom-4 z-50 flex h-10 w-10 items-center justify-center rounded-full bg-gray-800 text-white shadow-lg transition-all duration-300 hover:bg-gray-700 ${collapsed ? "left-4" : "left-[15rem]"}`}
      >
        <svg
          className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    </>
  );
}
