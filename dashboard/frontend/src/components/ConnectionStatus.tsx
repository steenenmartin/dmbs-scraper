import { useEffect, useState } from "react";
export function ConnectionStatus() {
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    async function check() {
      try {
        const response = await fetch("/api/health");
        const data = await response.json();
        if (!response.ok || !data.connected) throw new Error("Database unavailable");
        if (active) setError("");
      } catch {
        if (active) setError("Databasen er midlertidigt utilgængelig. Forbindelsen kontrolleres automatisk igen.");
      }
    }
    void check();
    const timer = window.setInterval(check, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return error ? <div role="alert" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{error}</div> : null;
}
