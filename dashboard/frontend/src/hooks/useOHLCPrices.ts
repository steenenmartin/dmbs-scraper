import { useEffect, useState } from "react";
import type { OHLCPrice } from "../types";

export function useOHLCPrices() {
  const [ohlcPrices, setOhlcPrices] = useState<OHLCPrice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ohlc-prices")
      .then((res) => res.json())
      .then((data) => setOhlcPrices(data))
      .catch((err) => console.error("Failed to fetch OHLC prices:", err))
      .finally(() => setLoading(false));
  }, []);

  return { ohlcPrices, loading };
}
