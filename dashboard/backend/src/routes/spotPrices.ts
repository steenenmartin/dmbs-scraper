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

router.get("/status", async (_req, res) => {
  try {
    const data = await query("SELECT * FROM status ORDER BY institute");
    res.json(data);
  } catch (err) {
    console.error("Error fetching status:", err);
    res.status(500).json({ error: "Failed to fetch status" });
  }
});

router.get("/rates", async (req, res) => {
  try {
    const since = req.query.since as string | undefined;
    const data = since
      ? await query("SELECT * FROM rates WHERE timestamp >= $1 ORDER BY timestamp DESC", [since])
      : await query("SELECT * FROM rates ORDER BY timestamp DESC");
    res.json(data);
  } catch (err) {
    console.error("Error fetching rates:", err);
    res.status(500).json({ error: "Failed to fetch rates" });
  }
});

router.get("/master-data-float", async (_req, res) => {
  try {
    const data = await query("SELECT * FROM master_data_float");
    res.json(data);
  } catch (err) {
    console.error("Error fetching floating master data:", err);
    res.status(500).json({ error: "Failed to fetch floating master data" });
  }
});

router.get("/ohlc-prices", async (req, res) => {
  try {
    const since = req.query.since as string | undefined;
    const data = since
      ? await query("SELECT * FROM ohlc_prices WHERE timestamp >= $1 ORDER BY timestamp DESC", [since])
      : await query("SELECT * FROM ohlc_prices ORDER BY timestamp DESC");
    res.json(data);
  } catch (err) {
    console.error("Error fetching ohlc prices:", err);
    res.status(500).json({ error: "Failed to fetch ohlc prices" });
  }
});

export default router;
