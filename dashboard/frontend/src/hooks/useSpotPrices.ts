import { fetchJson } from "../utils/api";
import { useState, useEffect, useCallback } from "react";
import type { SpotPrice } from "../types";

const REFRESH_INTERVAL = 60_000;

export function useSpotPrices() {
  const [prices, setPrices] = useState<SpotPrice[]>([]);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const fetchPrices = useCallback(async () => {
    try {
      const data = await fetchJson<any>("/api/spot-prices");
      setError("");
      setPrices(data.prices);
      setDateRange(data.dateRange);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  return { error, prices, dateRange, loading, refetch: fetchPrices };
}
