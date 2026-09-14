import pg from "pg";
import { databaseUrl, readCredentials } from "./config.js";

export const databaseKind = "postgres";
// Preserve timestamp precision; scraper timestamps without a zone are UTC.
pg.types.setTypeParser(1114, value => value.replace(" ", "T") + "Z");
pg.types.setTypeParser(1184, value => value.replace(" ", "T"));
pg.types.setTypeParser(1082, value => value);
pg.types.setTypeParser(1700, Number);
let pool: pg.Pool | undefined;
function getPool() {
  if (pool) return pool;
  const credentials = databaseUrl ? undefined : readCredentials();
  if (!databaseUrl && !credentials) throw new Error("Configure DATABASE_URL or credentials.json.");
  const sslMode = process.env.DATABASE_SSL || credentials?.ssl || (process.env.DYNO ? "require" : undefined);
  const { ssl: _ssl, ...connection } = credentials ?? {};
  pool = new pg.Pool({
    ...(databaseUrl ? { connectionString: databaseUrl } : connection),
    ...(sslMode === "disable" ? { ssl: false } : sslMode === "require" ? { ssl: { rejectUnauthorized: false } } : {}),
    connectionTimeoutMillis: 5000,
    statement_timeout: 15000,
    options: "-c timezone=UTC",
  });
  pool.on("error", () => console.error("Database connection lost"));
  return pool;
}
export type Query = <T extends pg.QueryResultRow = any>(sql: string, params?: any[]) => Promise<T[]>;
export const query: Query = async (sql, params = []) => (await getPool().query(sql, params)).rows;
export async function closeDatabase() { await pool?.end(); pool = undefined; }
