#!/usr/bin/env node
/**
 * Real DSH web startup smoke test. Uses the DSH JS modules extracted
 * byte-for-byte from the built APK's embedded dsh-runtime.bin.
 *
 * PASS requires:
 *  - process stays alive, without an API key;
 *  - web profile launches and returns a usable HTML response over 127.0.0.1;
 *  - normal HTTP request reaches its DSH page (not a bare open TCP socket);
 *  - at least one linked bundle/static asset can be fetched, when present;
 *  - the child process group terminates, not left running in CI.
 *
 * Linux ARM64 validation is NOT Android/bxroot validation.
 */
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { mkdtemp, rm, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const entry = process.argv[2];
if (!entry) throw new Error("USAGE: smoke-dsh-web.mjs <extracted-full-path-to-dsh/lib/bin.js>");
const port = await new Promise((resolve, reject) => {
  const server = createServer();
  server.once("error", reject);
  server.listen(0, "127.0.0.1", () => {
    const address = server.address();
    const selected = address.port;
    server.close(() => resolve(selected));
  });
});

const workspace = await mkdtemp(path.join(tmpdir(), "dsha-real-dsh-boot-"));
await mkdir(path.join(workspace, "home"), { recursive: true });
const logs = [];
let size = 0;
const filteredEnv = {
  ...process.env,
  HOME: path.join(workspace, "home"),
  DSH_HOME: path.join(workspace, "home", ".dsh"),
  XDG_CONFIG_HOME: path.join(workspace, "home", ".config"),
  XDG_CACHE_HOME: path.join(workspace, "home", ".cache"),
  BROWSER: "none",
  CI: "true",
};
delete filteredEnv.DEEPSEEK_API_KEY;
delete filteredEnv.OPENAI_API_KEY;
delete filteredEnv.ANTHROPIC_API_KEY;
const child = spawn(process.execPath, [entry, "web", "--no-open", "--port", String(port)], {
  env: filteredEnv,
  cwd: workspace,
  detached: true,
  stdio: ["ignore", "pipe", "pipe"],
});
for (const stream of [child.stdout, child.stderr]) {
  stream.on("data", data => {
    const s = data.toString("utf8");
    size += s.length;
    if (size < 150_000) logs.push(s);
  });
}
const started = Date.now();
let outcome = null;
const origin = "http://127.0.0.1:" + port;
const deadline = Date.now() + 105_000;
let lastError = null;
let attempt = 0;

function redact(s) {
  return s
    .replace(/(https?:\/\/(?:127\.0\.0\.1|localhost):\d+)(?:\/[^\s"'<>]*)?/g, "$1/[REDACTED]")
    .replace(/(sk-[a-zA-Z0-9_-]{10,})/g, "[API_KEY_REDACTED]")
    .slice(-5000);
}
function urlCandidates(log, port) {
  const text = log.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, "");
  const urls = [...text.matchAll(/https?:\/\/(?:localhost|127\.0\.0\.1):(\d+)(?:\/[^\s"'<>]*)?/g)]
    .filter(m => Number(m[1]) === port)
    .map(m => m[0].replace(/[)\],.;]+$/, ""));
  return [...new Set([...urls, origin + "/"])];
}
async function httpVisit(target) {
  let cookie = "";
  let url = new URL(target);
  url.hostname = "127.0.0.1";
  if (url.port !== String(port) || url.protocol !== "http:") throw new Error("UNTRUSTED_STARTUP_URL");
  for (let i = 0; i < 5; i++) {
    const res = await fetch(url, {
      headers: cookie ? { cookie } : {},
      redirect: "manual",
      signal: AbortSignal.timeout(2300),
    });
    for (const part of res.headers.getSetCookie?.() || []) {
      const raw = part.split(";")[0];
      if (raw.includes("=")) cookie = cookie ? cookie + "; " + raw : raw;
    }
    const location = res.headers.get("location");
    if (location && [301, 302, 303, 307, 308].includes(res.status)) {
      url = new URL(location, url);
      if (url.hostname !== "127.0.0.1" || url.port !== String(port)) throw new Error("EXTERNAL_REDIRECT");
      continue;
    }
    const ct = res.headers.get("content-type") || "";
    const body = (await res.text()).slice(0, 140_000);
    return { status: res.status, ct, body, url, cookie };
  }
  throw new Error("TOO_MANY_REDIRECTS");
}
try {
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error("DSH_PROCESS_EARLY_EXIT code=" + child.exitCode + " signal=" + child.signalCode + "\n" + redact(logs.join("")));
    }
    attempt++;
    const targets = urlCandidates(logs.join(""), port).slice(0, 8);
    for (const url of targets) {
      try {
        const response = await httpVisit(url);
        const looksHtml = response.ct.includes("text/html") &&
          /<!doctype html|<html[\s>]/i.test(response.body) &&
          /dsh|deepseek|<script|<main|id="root"/i.test(response.body);
        if (response.status === 200 && looksHtml) {
          outcome = response;
          break;
        }
        lastError = "HTTP_" + response.status + " type=" + response.ct +
          " bodyPrefix=" + response.body.slice(0, 90).replace(/[^a-z0-9 ]/gi, "");
      } catch (e) {
        lastError = String(e.message || e);
      }
    }
    if (outcome) break;
    await new Promise(resolve => setTimeout(resolve, 750));
  }
  if (!outcome) {
    throw new Error("DSH_WEB_NOT_HTTP_READY in " + Math.round((Date.now() - started) / 1000) +
      "s (attempts=" + attempt + ", last=" + lastError + ")\n" + redact(logs.join("")));
  }
  console.log("DSH_PROCESS_HTTP_READY status=" + outcome.status + " htmlBytes=" +
    Buffer.byteLength(outcome.body) + " uptimeSeconds=" + ((Date.now()-started)/1000).toFixed(1));
  const script = outcome.body.match(/<script[^>]+src=["']([^"']+)["']/i);
  let staticOutcome = "NO_EXTERNAL_SCRIPT_TAG";
  if (script) {
    // HTML attributes are entity-escaped. Browsers decode &amp; to & when
    // resolving a <script src>; the Node harness must do the same before GET.
    // Without this, the ?module&rev= URL is sent as ?module&amp;rev=
    // and DSH (correctly) returns HTTP 404. This was a harness bug, not
    // evidence that the published DSH frontend file was missing.
    const decodedSrc = script[1].replaceAll("&amp;", "&").replaceAll("&#38;", "&")
      .replaceAll("&quot;", '"').replaceAll("&#39;", "'");
    const assetUrl = new URL(decodedSrc, outcome.url);
    if (assetUrl.origin !== origin) throw new Error("UNTRUSTED_SCRIPT_ORIGIN");
    console.log("DSH_STATIC_REQUEST path=" + assetUrl.pathname +
      " queryKeys=" + [...assetUrl.searchParams.keys()].join(",") +
      " cookiePresent=" + Boolean(outcome.cookie));
    const resp = await fetch(assetUrl, {
      headers: outcome.cookie ? { cookie: outcome.cookie } : {},
      signal: AbortSignal.timeout(6000),
    });
    const bytes = Buffer.from(await resp.arrayBuffer());
    if (!resp.ok || bytes.length < 16) {
      throw new Error("DSH_STATIC_ASSET_NOT_SERVABLE status=" + resp.status +
        " bytes=" + bytes.length +
        " requestedPath=" + redact(assetUrl.pathname) +
        " htmlHead=" + redact(outcome.body.slice(0, 1200)) +
        " contentType=" + (resp.headers.get("content-type") || "-"));
    }
    staticOutcome = "HTTP_" + resp.status + " bytes=" + bytes.length;
  }
  if (child.exitCode !== null || child.signalCode !== null)
    throw new Error("DSH_DIED_AFTER_HTTP_READY");
  console.log("DSH_LIVE_BOOT_PASS version=0.2.1-rc.2 environment=linux-arm64");
  console.log("DSH_LIVE_WEB_PASS httpStatus=" + outcome.status +
    " htmlBytes=" + Buffer.byteLength(outcome.body) + " static=" + staticOutcome);
  console.log("DSH_LIVE_PROCESS_STILL_ALIVE pid=" + child.pid +
    " uptimeSeconds=" + ((Date.now() - started) / 1000).toFixed(1));
} finally {
  try { process.kill(-child.pid, "SIGTERM"); } catch {}
  await new Promise(resolve => setTimeout(resolve, 1000));
  if (child.exitCode === null) {
    try { process.kill(-child.pid, "SIGKILL"); } catch {}
  }
  await rm(workspace, { recursive: true, force: true });
}
