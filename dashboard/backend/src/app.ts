import express from "express";
import path from "node:path";
import { existsSync } from "node:fs";
import spotPricesRouter from "./routes/spotPrices.js";
import { query, databaseKind } from "./db.js";
import { repoRoot } from "./config.js";

export const app = express();
const frontendDistPath = path.join(repoRoot, "dashboard/frontend/dist");
app.get("/api/health", async (_req, res) => {
  try {
    await query("SELECT 1 AS ok");
    res.json({ connected: true, database: databaseKind });
  } catch {
    res.status(503).json({ connected: false, database: databaseKind, error: "Database unavailable. Configure .env.dashboard.local and check database access." });
  }
});
app.use("/api", spotPricesRouter);
app.use("/api", (_req, res) => { res.status(404).json({ error: "Unknown API endpoint" }); });
app.use(express.static(frontendDistPath));
app.get("*", (_req, res) => {
  const index = path.join(frontendDistPath, "index.html");
  if (existsSync(index)) res.sendFile(index);
  else res.status(503).type("text").send("Frontend is not built. Use http://127.0.0.1:5173 during npm run dev, or run npm run build.");
});
app.use((err: { status?: number }, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  res.status(err.status === 400 ? 400 : 500).json({ error: err.status === 400 ? "Invalid JSON request" : "Request failed" });
});
