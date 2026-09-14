import { fetchJson } from "../utils/api";
import { useEffect, useState } from "react";
import type { OHLCPrice } from "../types";


function getSinceParam(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().split("T")[0];
}

export function useOHLCPrices() {
  const [ohlcPrices, setOhlcPrices] = useState<OHLCPrice[]>([]);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    fetchJson<any>(`/api/ohlc-prices?since=${getSinceParam()}`)
      .then((data: OHLCPrice[]) => { setOhlcPrices(data); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { ohlcPrices, loading, error };
}
