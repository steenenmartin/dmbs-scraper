import { useEffect, useState } from "react";
import type { FlexRate } from "../types";

let cache: FlexRate[] | null = null;

function getSinceParam(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 2);
  return d.toISOString().split("T")[0];
}

export function useFlexRates() {
  const [rates, setRates] = useState<FlexRate[]>(cache ?? []);
  const [loading, setLoading] = useState(cache === null);

  useEffect(() => {
    if (cache !== null) return;
    fetch(`/api/rates?since=${getSinceParam()}`)
      .then((res) => res.json())
      .then((data: FlexRate[]) => { cache = data; setRates(data); })
      .catch((err) => console.error("Failed to fetch rates:", err))
      .finally(() => setLoading(false));
  }, []);

  return { rates, loading };
}
