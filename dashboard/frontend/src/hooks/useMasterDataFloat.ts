import { fetchJson } from "../utils/api";
import { useEffect, useState } from "react";
import type { MasterDataFloat } from "../types";

export function useMasterDataFloat() {
  const [masterDataFloat, setMasterDataFloat] = useState<MasterDataFloat[]>([]);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    fetchJson<any>("/api/master-data-float")
      .then((data) => setMasterDataFloat(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { masterDataFloat, loading, error };
}
