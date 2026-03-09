import express from "express";
import cors from "cors";
import spotPricesRouter from "./routes/spotPrices.js";

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());
app.use("/api", spotPricesRouter);

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});
