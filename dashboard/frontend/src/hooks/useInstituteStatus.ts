import { useState, useEffect, useCallback } from "react";
import type { InstituteStatus } from "../types";

const REFRESH_INTERVAL = 60_000;

export function useInstituteStatus() {
  const [status, setStatus] = useState<InstituteStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch status:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { status, loading };
}
