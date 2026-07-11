#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const repository = "zacharygcook/zach-ralph-method";
const just = process.platform === "win32" ? "just.exe" : "just";
const justCheck = spawnSync(just, ["--version"], { stdio: "ignore" });
if (justCheck.status !== 0) {
  console.error("Install just first: https://just.systems/man/en/installation.html");
  process.exit(12);
}

const npx = process.platform === "win32" ? "npx.cmd" : "npx";
const result = spawnSync(npx, ["skills", "add", repository], {
  cwd: process.cwd(),
  stdio: "inherit",
});

if (result.error) {
  console.error(`Unable to run Skills CLI: ${result.error.message}`);
  process.exit(1);
}
if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

const importLine = "import '.agents/skills/ralph-workflows/recipes.just'";
const candidates = ["justfile", "Justfile", ".justfile"].map((name) =>
  join(process.cwd(), name),
);
const justfile = candidates.find(existsSync) ?? candidates[0];
const existing = existsSync(justfile) ? readFileSync(justfile, "utf8") : "";

if (!existing.split(/\r?\n/).includes(importLine)) {
  const separator = existing && !existing.endsWith("\n") ? "\n" : "";
  writeFileSync(justfile, `${existing}${separator}${importLine}\n`, "utf8");
}

console.log("\nRalph recipes are ready. Run: just init");
