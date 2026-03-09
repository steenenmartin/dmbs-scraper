import express from "express";
import cors from "cors";
import path from "node:path";
import spotPricesRouter from "./routes/spotPrices.js";

const app = express();
const PORT = Number(process.env.PORT ?? 3001);
const frontendDistPath = path.resolve(process.cwd(), "dashboard/frontend/dist");

app.use(cors());
app.use(express.json());
app.use("/api", spotPricesRouter);
app.use(express.static(frontendDistPath));

app.get("*", (_req, res) => {
  res.sendFile(path.join(frontendDistPath, "index.html"));
});

app.listen(PORT, () => {
  console.log(`Dashboard server running on port ${PORT}`);
});
