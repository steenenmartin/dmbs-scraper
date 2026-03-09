import { useEffect, useState } from "react";
import type { MasterDataFloat } from "../types";

export function useMasterDataFloat() {
  const [masterDataFloat, setMasterDataFloat] = useState<MasterDataFloat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/master-data-float")
      .then((res) => res.json())
      .then((data) => setMasterDataFloat(data))
      .catch((err) => console.error("Failed to fetch floating master data:", err))
      .finally(() => setLoading(false));
  }, []);

  return { masterDataFloat, loading };
}
