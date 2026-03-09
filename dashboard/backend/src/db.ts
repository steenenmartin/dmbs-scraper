import pg from "pg";

const pool = new pg.Pool({
  host: "c35nvon35iqc30.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com",
  port: 5432,
  database: "d6v4equ3b5lrg3",
  user: "ufat6r7kf9ccoe",
  password:
    "pab015156b9089bb6d27b8bbc4b7ec7e693b14bac792335671b78029da29a2d32",
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
