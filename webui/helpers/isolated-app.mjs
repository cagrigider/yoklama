/**
 * Isolated Yoklama runtime: copy the project to /tmp and run python3 app.py
 * from that copy. Never opens the operator data/attendance.db or copies
 * seed/people.json (Grup 8 PII).
 */
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(HERE, "../..");
export const RUNTIME_FILE = path.join(HERE, "../.isolated-runtime.json");

const SKIP_TOP = new Set([
  ".git",
  "node_modules",
  "test-results",
  "playwright-report",
  "blob-report",
  "__pycache__",
  ".factory-worktrees",
]);

export function pickListenPortSync(preferred = 8765) {
  const script = `
import socket
preferred = ${Number(preferred)}
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", preferred))
except OSError:
    s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
`;
  return Number(execFileSync("python3", ["-c", script], { encoding: "utf8" }).trim());
}

function shouldCopy(src) {
  const rel = path.relative(PROJECT_ROOT, src);
  if (!rel || rel === ".") return true;
  if (rel.startsWith("..")) return false;
  const parts = rel.split(path.sep);
  if (parts.some((p) => SKIP_TOP.has(p))) return false;
  if (parts[0] === "data" && parts[1] && /\.db(-journal)?$/.test(parts[1])) return false;
  if (rel === path.join("seed", "people.json") || rel === "seed/people.json") return false;
  return true;
}

function copyIsolatedTree(dest) {
  fs.cpSync(PROJECT_ROOT, dest, { recursive: true, filter: shouldCopy });
  fs.mkdirSync(path.join(dest, "data"), { recursive: true });
  fs.mkdirSync(path.join(dest, "seed"), { recursive: true });
  const leakedDb = path.join(dest, "data", "attendance.db");
  if (fs.existsSync(leakedDb)) {
    throw new Error("Refusing to start: copied tree contains data/attendance.db");
  }
  const leakedSeed = path.join(dest, "seed", "people.json");
  if (fs.existsSync(leakedSeed)) {
    throw new Error("Refusing to start: copied tree contains seed/people.json");
  }
}

function patchPort(dest, port) {
  const appPy = path.join(dest, "app.py");
  const text = fs.readFileSync(appPy, "utf8");
  const next = text.replace(/PORT = 8765/, `PORT = ${Number(port)}`);
  if (Number(port) !== 8765 && next === text) {
    throw new Error("Could not patch PORT in temp app.py");
  }
  if (next !== text) fs.writeFileSync(appPy, next);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForMeta(baseURL, timeoutMs = 20000) {
  const start = Date.now();
  let last = "";
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${baseURL}/api/meta`);
      if (res.ok) return;
      last = `HTTP ${res.status}`;
    } catch (err) {
      last = err instanceof Error ? err.message : String(err);
    }
    await sleep(100);
  }
  throw new Error(`Isolated Yoklama did not answer ${baseURL}/api/meta (${last})`);
}

/**
 * @param {{ port?: number, seedPeople?: object[], writeRuntime?: boolean }} [opts]
 */
export async function startIsolated(opts = {}) {
  const port = opts.port ?? pickListenPortSync(0);
  const dest = fs.mkdtempSync(path.join(os.tmpdir(), "yoklama-setup-"));
  copyIsolatedTree(dest);
  if (opts.seedPeople) {
    fs.writeFileSync(
      path.join(dest, "seed", "people.json"),
      JSON.stringify(opts.seedPeople, null, 2),
      "utf8",
    );
  }
  patchPort(dest, port);
  const baseURL = `http://127.0.0.1:${port}`;
  const child = spawn("python3", ["app.py"], {
    cwd: dest,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env },
  });
  let output = "";
  child.stdout.on("data", (buf) => {
    output += buf.toString();
  });
  child.stderr.on("data", (buf) => {
    output += buf.toString();
  });
  const runtime = { root: dest, port, baseURL, pid: child.pid };
  if (opts.writeRuntime) {
    fs.mkdirSync(path.dirname(RUNTIME_FILE), { recursive: true });
    fs.writeFileSync(RUNTIME_FILE, JSON.stringify(runtime, null, 2));
  }

  const stop = async () => {
    if (child.exitCode == null && child.signalCode == null) {
      child.kill("SIGINT");
      const deadline = Date.now() + 4000;
      while (child.exitCode == null && child.signalCode == null && Date.now() < deadline) {
        await sleep(50);
      }
      if (child.exitCode == null && child.signalCode == null) {
        child.kill("SIGKILL");
      }
    }
    fs.rmSync(dest, { recursive: true, force: true });
    if (opts.writeRuntime && fs.existsSync(RUNTIME_FILE)) {
      try {
        const current = JSON.parse(fs.readFileSync(RUNTIME_FILE, "utf8"));
        if (current.root === dest) fs.rmSync(RUNTIME_FILE, { force: true });
      } catch {
        fs.rmSync(RUNTIME_FILE, { force: true });
      }
    }
  };

  try {
    await waitForMeta(baseURL);
  } catch (err) {
    await stop();
    throw new Error(`${err.message}\n${output}`);
  }
  return { ...runtime, stop, child };
}

export function readRuntime() {
  if (!fs.existsSync(RUNTIME_FILE)) {
    throw new Error(`Missing ${RUNTIME_FILE} — webServer did not start isolated-app`);
  }
  return JSON.parse(fs.readFileSync(RUNTIME_FILE, "utf8"));
}

export function resetEmptyDb(root = readRuntime().root) {
  const dbPath = path.join(root, "data", "attendance.db");
  const operator = path.resolve(PROJECT_ROOT, "data", "attendance.db");
  if (path.resolve(dbPath) === operator) {
    throw new Error("Refusing to open operator data/attendance.db");
  }
  if (!fs.existsSync(dbPath)) return;
  const script = `
import sqlite3, sys
path = sys.argv[1]
conn = sqlite3.connect(path)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript("""
DELETE FROM attendance;
DELETE FROM people;
DELETE FROM meetings;
DELETE FROM group_profile;
""")
conn.commit()
conn.close()
`;
  execFileSync("python3", ["-c", script, dbPath], { encoding: "utf8" });
}

function parseArgs(argv) {
  const out = { port: undefined, writeRuntime: true };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--port") out.port = Number(argv[++i]);
  }
  return out;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = parseArgs(process.argv.slice(2));
  const handle = await startIsolated({ port: args.port, writeRuntime: true });
  const cleanup = async () => {
    await handle.stop();
    process.exit(0);
  };
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);
  handle.child.on("exit", async (code) => {
    await handle.stop();
    process.exit(code ?? 1);
  });
}
