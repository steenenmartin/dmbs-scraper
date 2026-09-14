import { fetchJson } from "../utils/api";
import { useState, useCallback } from "react";
import type { SpotPrice } from "../types";


export function useClosingPrices() {
  const [closingPrices, setClosingPrices] = useState<SpotPrice[] | null>(null);
  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const fetchClosingPrices = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJson<any>("/api/closing-prices");
      setError("");
      setClosingPrices(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { error, closingPrices, loading, fetchClosingPrices };
}
