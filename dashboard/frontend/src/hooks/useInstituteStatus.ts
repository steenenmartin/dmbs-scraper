import { useState, useEffect } from "react";
import type { StatusSnapshot } from "../types";

const REFRESH_INTERVAL = 60_000;

export function useInstituteStatus() {
  const [snapshot, setSnapshot] = useState<StatusSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let stopped = false;
    let controller: AbortController | null = null;
    let timer: ReturnType<typeof setTimeout>;

    async function refresh() {
      if (stopped || controller) return;
      const request = new AbortController();
      controller = request;
      const started = Date.now();
      const timeout = setTimeout(() => request.abort(), 10_000);
      try {
        const response = await fetch("/api/status", { signal: request.signal, cache: "no-store" });
        if (!response.ok) throw new Error(`Status unavailable (${response.status}).`);
        const data: StatusSnapshot = await response.json();
        const lifetime = Date.parse(data.refresh_at) - Date.parse(data.checked_at);
        if (!Number.isFinite(lifetime) || lifetime <= 0 || !Array.isArray(data.institutes)) {
          throw new Error("Invalid status response.");
        }
        if (stopped || request.signal.aborted) return;
        const remaining = Math.min(REFRESH_INTERVAL, lifetime) - (Date.now() - started);
        if (remaining <= 0) throw new Error("Status response expired.");
        setSnapshot(data);
        setError("");
        clearTimeout(timer);
        timer = setTimeout(() => {
          setError("Status unavailable. Refreshing…");
          void refresh();
        }, remaining);
      } catch (err) {
        if (stopped) return;
        setError(request.signal.aborted ? "Status request timed out." : (err as Error).message);
        clearTimeout(timer);
        timer = setTimeout(() => void refresh(), Math.max(0, REFRESH_INTERVAL - (Date.now() - started)));
      } finally {
        clearTimeout(timeout);
        controller = null;
        if (!stopped) setLoading(false);
      }
    }

    const onFocus = () => { void refresh(); };
    const onVisibility = () => { if (document.visibilityState === "visible") void refresh(); };
    void refresh();
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller?.abort();
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return { snapshot, loading, error };
}
