import { fetchJson } from "../utils/api";
import { useState, useEffect } from "react";
import type { MasterData } from "../types";

export function useMasterData() {
  const [masterData, setMasterData] = useState<MasterData[]>([]);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    fetchJson<any>("/api/master-data")
      .then((data) => setMasterData(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { masterData, loading, error };
}
