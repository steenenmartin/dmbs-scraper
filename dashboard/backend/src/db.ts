import pg from "pg";

function resolveDatabaseUrl(): string {
  const databaseUrl =
    process.env.DATABASE_URL ??
    process.env.HEROKU_POSTGRESQL_BRONZE_URL ??
    process.env.HEROKU_POSTGRESQL_COBALT_URL ??
    process.env.HEROKU_POSTGRESQL_CRIMSON_URL;

  if (!databaseUrl) {
    throw new Error(
      "Missing database connection string. Set DATABASE_URL (preferred) or HEROKU_POSTGRESQL_* env var."
    );
  }

  return databaseUrl;
}

const pool = new pg.Pool({
  connectionString: resolveDatabaseUrl(),
  ssl: { rejectUnauthorized: false },
});

export async function query<T extends pg.QueryResultRow = any>(
  sql: string,
  params?: any[]
): Promise<T[]> {
  const result = await pool.query<T>(sql, params);
  return result.rows;
}

export default pool;
