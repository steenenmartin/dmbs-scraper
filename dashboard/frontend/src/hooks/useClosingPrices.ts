import { useState, useCallback } from "react";
import type { SpotPrice } from "../types";

let cache: SpotPrice[] | null = null;

export function useClosingPrices() {
  const [closingPrices, setClosingPrices] = useState<SpotPrice[] | null>(cache);
  const [loading, setLoading] = useState(false);

  const fetchClosingPrices = useCallback(async () => {
    if (cache !== null) {
      setClosingPrices(cache);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/closing-prices");
      const data: SpotPrice[] = await res.json();
      cache = data;
      setClosingPrices(data);
    } catch (err) {
      console.error("Failed to fetch closing prices:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { closingPrices, loading, fetchClosingPrices };
}
