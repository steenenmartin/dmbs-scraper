import { useState, useCallback } from "react";
import type { SpotPrice } from "../types";

export function useClosingPrices() {
  const [closingPrices, setClosingPrices] = useState<SpotPrice[] | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchClosingPrices = useCallback(async () => {
    if (closingPrices !== null) return;
    setLoading(true);
    try {
      const res = await fetch("/api/closing-prices");
      const data = await res.json();
      setClosingPrices(data);
    } catch (err) {
      console.error("Failed to fetch closing prices:", err);
    } finally {
      setLoading(false);
    }
  }, [closingPrices]);

  return { closingPrices, loading, fetchClosingPrices };
}
