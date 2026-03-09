import { Router } from "express";
import { query } from "../db.js";
import { getActiveTimeRange } from "../utils/dateHelper.js";

const router = Router();

router.get("/spot-prices", async (_req, res) => {
  try {
    const [startUtc, endUtc] = getActiveTimeRange(undefined, true);

    const prices = await query(
      "SELECT * FROM spot_prices WHERE timestamp BETWEEN $1 AND $2",
      [startUtc.toISOString(), endUtc.toISOString()]
    );

    res.json({
      prices,
      dateRange: [startUtc.toISOString(), endUtc.toISOString()],
    });
  } catch (err) {
    console.error("Error fetching spot prices:", err);
    res.status(500).json({ error: "Failed to fetch spot prices" });
  }
});

router.get("/master-data", async (_req, res) => {
  try {
    const data = await query("SELECT * FROM master_data");
    res.json(data);
  } catch (err) {
    console.error("Error fetching master data:", err);
    res.status(500).json({ error: "Failed to fetch master data" });
  }
});

router.get("/closing-prices", async (_req, res) => {
  try {
    const data = await query("SELECT * FROM closing_prices");
    res.json(data);
  } catch (err) {
    console.error("Error fetching closing prices:", err);
    res.status(500).json({ error: "Failed to fetch closing prices" });
  }
});

export default router;
