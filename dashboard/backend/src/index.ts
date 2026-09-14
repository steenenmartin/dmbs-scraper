import { app } from "./app.js";
import { host, port } from "./config.js";
import { closeDatabase } from "./db.js";

const server = app.listen(port, host, () => console.log(`Dashboard API: http://${host}:${port}`));
server.on("error", error => { console.error(error.message); process.exitCode = 1; });
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => server.close(() => { void closeDatabase().then(() => process.exit(0)); }));
}
