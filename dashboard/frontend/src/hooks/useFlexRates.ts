import { fetchJson } from "../utils/api";
import { useEffect, useState } from "react";
import type { FlexRate } from "../types";


function getSinceParam(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 2);
  return d.toISOString().split("T")[0];
}

export function useFlexRates() {
  const [rates, setRates] = useState<FlexRate[]>([]);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    fetchJson<any>(`/api/rates?since=${getSinceParam()}`)
      .then((data: FlexRate[]) => { setRates(data); })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { rates, loading, error };
}
