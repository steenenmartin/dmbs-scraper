import path from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { loadEnvFile } from "node:process";

export const repoRoot = path.resolve(__dirname, "../../..");
const envFile = path.join(repoRoot, ".env.dashboard.local");
if (existsSync(envFile)) loadEnvFile(envFile);

export const databaseUrl = process.env.DATABASE_URL ||
  process.env.HEROKU_POSTGRESQL_BRONZE_URL ||
  process.env.HEROKU_POSTGRESQL_COBALT_URL ||
  process.env.HEROKU_POSTGRESQL_CRIMSON_URL;
export function readCredentials(): { user: string; password: string; host: string; port: number; database: string; ssl?: string } | undefined {
  const credentialsPath = path.join(repoRoot, "src/credit_institute_scraper/database/credentials.json");
  if (!existsSync(credentialsPath)) return;
  const credentials = JSON.parse(readFileSync(credentialsPath, "utf8"));
  if (!["user", "password", "host", "database"].every(key => typeof credentials[key] === "string" && credentials[key].length > 0)) return;
  return { ...credentials, port: Number(credentials.port || 5432) };
}
export const port = Number(process.env.PORT || 3001);
export const host = process.env.HOST || (process.env.NODE_ENV === "production" || process.env.DYNO ? "0.0.0.0" : "127.0.0.1");
