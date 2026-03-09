import { useState, useEffect, useCallback } from "react";
import type { SpotPrice } from "../types";

const REFRESH_INTERVAL = 60_000;

export function useSpotPrices() {
  const [prices, setPrices] = useState<SpotPrice[]>([]);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPrices = useCallback(async () => {
    try {
      const res = await fetch("/api/spot-prices");
      const data = await res.json();
      setPrices(data.prices);
      setDateRange(data.dateRange);
    } catch (err) {
      console.error("Failed to fetch spot prices:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  return { prices, dateRange, loading, refetch: fetchPrices };
}
