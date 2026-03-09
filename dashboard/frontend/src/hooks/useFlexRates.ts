import { useEffect, useState } from "react";
import type { FlexRate } from "../types";

export function useFlexRates() {
  const [rates, setRates] = useState<FlexRate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/rates")
      .then((res) => res.json())
      .then((data) => setRates(data))
      .catch((err) => console.error("Failed to fetch rates:", err))
      .finally(() => setLoading(false));
  }, []);

  return { rates, loading };
}
