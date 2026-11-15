// Stamps the real site URL and API URL into the static files at deploy time.
import { cpSync, rmSync, mkdirSync, readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";
const env = process.env;
let site = (env.SITE_URL || (env.VERCEL_PROJECT_PRODUCTION_URL ? "https://" + env.VERCEL_PROJECT_PRODUCTION_URL : "")).replace(/\/+$/, "");
if (!site) { console.warn("SITE_URL not set; using http://localhost:3000"); site = "http://localhost:3000"; }
const api = (env.API_URL || "").replace(/\/+$/, "");
rmSync("dist", { recursive: true, force: true }); mkdirSync("dist");
const skip = new Set(["dist", "build.mjs", "vercel.json", "node_modules"]);
const stamp = /\.(html|xml|txt|webmanifest)$/;
function walk(src, dst) {
  for (const f of readdirSync(src)) {
    if (src === "." && skip.has(f)) continue;
    const s = join(src, f), d = join(dst, f);
    if (statSync(s).isDirectory()) { mkdirSync(d); walk(s, d); }
    else if (stamp.test(f)) writeFileSync(d, readFileSync(s, "utf8").replaceAll("%SITE%", site));
    else cpSync(s, d);
  }
}
walk(".", "dist");
writeFileSync("dist/config.js", "window.API=" + JSON.stringify(api) + ";\n");
console.log("Built for", site, "API:", api || "(not set)");
