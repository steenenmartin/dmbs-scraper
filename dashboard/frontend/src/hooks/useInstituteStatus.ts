import { fetchJson } from "../utils/api";
import { useState, useEffect, useCallback } from "react";
import type { InstituteStatus } from "../types";

const REFRESH_INTERVAL = 60_000;

export function useInstituteStatus() {
  const [status, setStatus] = useState<InstituteStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const fetchStatus = useCallback(async () => {
    try {
      const data = await fetchJson<any>("/api/status");
      setError("");
      setStatus(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { error, status, loading };
}
