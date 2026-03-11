import { useEffect, useState } from "react";
import type { OHLCPrice } from "../types";

let cache: OHLCPrice[] | null = null;

function getSinceParam(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().split("T")[0];
}

export function useOHLCPrices() {
  const [ohlcPrices, setOhlcPrices] = useState<OHLCPrice[]>(cache ?? []);
  const [loading, setLoading] = useState(cache === null);

  useEffect(() => {
    if (cache !== null) return;
    fetch(`/api/ohlc-prices?since=${getSinceParam()}`)
      .then((res) => res.json())
      .then((data: OHLCPrice[]) => { cache = data; setOhlcPrices(data); })
      .catch((err) => console.error("Failed to fetch OHLC prices:", err))
      .finally(() => setLoading(false));
  }, []);

  return { ohlcPrices, loading };
}
