import { useState, useEffect } from "react";
import type { MasterData } from "../types";

export function useMasterData() {
  const [masterData, setMasterData] = useState<MasterData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/master-data")
      .then((res) => res.json())
      .then((data) => setMasterData(data))
      .catch((err) => console.error("Failed to fetch master data:", err))
      .finally(() => setLoading(false));
  }, []);

  return { masterData, loading };
}
