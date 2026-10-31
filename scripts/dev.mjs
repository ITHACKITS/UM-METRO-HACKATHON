// Runs the API and the web dev server together; Ctrl+C stops both.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";

const python = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

if (!existsSync(python)) {
  console.error("Python environment missing. Run `npm run setup` from the repository root first.");
  process.exit(1);
}

const procs = [
  spawn(`../${python}`, ["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], { cwd: "backend", stdio: "inherit" }),
  spawn("npm", ["--prefix", "frontend", "run", "dev"], { stdio: "inherit" }),
];
const stop = () => procs.forEach((p) => p.kill());
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
procs.forEach((p) => p.on("exit", stop));
