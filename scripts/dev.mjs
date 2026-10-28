// Runs the API and the web dev server together; Ctrl+C stops both.
import { spawn } from "node:child_process";

const procs = [
  spawn("python", ["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], { cwd: "backend", stdio: "inherit", shell: true }),
  spawn("npm", ["--prefix", "frontend", "run", "dev"], { stdio: "inherit", shell: true }),
];
const stop = () => procs.forEach((p) => p.kill());
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
procs.forEach((p) => p.on("exit", stop));
