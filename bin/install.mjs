#!/usr/bin/env node

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const repository = "zacharygcook/zach-ralph-method";
const skills = ["ralph-loop", "ralph-sprint", "ralph-status", "ralph-review"];
const just = process.platform === "win32" ? "just.exe" : "just";
const justCheck = spawnSync(just, ["--version"], { stdio: "ignore" });
if (justCheck.status !== 0) {
  console.error("Install just first: https://just.systems/man/en/installation.html");
  process.exit(12);
}

const npx = process.platform === "win32" ? "npx.cmd" : "npx";
const result = spawnSync(npx, ["skills", "add", repository, "--skill", ...skills], {
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

const legacySkill = join(process.cwd(), ".agents", "skills", "ralph-workflows");
if (existsSync(legacySkill)) {
  const removal = spawnSync(npx, ["skills", "remove", "ralph-workflows", "-y"], {
    cwd: process.cwd(),
    stdio: "inherit",
  });
  if (removal.status !== 0) {
    console.warn("Legacy ralph-workflows remains installed; remove it after verifying ralph-loop.");
  }
}

const legacyImport = "import '.agents/skills/ralph-workflows/recipes.just'";
const importLine = "import '.agents/skills/ralph-loop/recipes.just'";
const candidates = ["justfile", "Justfile", ".justfile"].map((name) =>
  join(process.cwd(), name),
);
const justfile = candidates.find(existsSync) ?? candidates[0];
const existing = existsSync(justfile) ? readFileSync(justfile, "utf8") : "";
const output = [];
let imported = false;
for (const line of existing.split(/\r?\n/)) {
  if (line === legacyImport || line === importLine) {
    if (!imported) {
      output.push(importLine);
      imported = true;
    }
    continue;
  }
  output.push(line);
}
if (!imported) {
  while (output.length && output.at(-1) === "") output.pop();
  output.push(importLine);
}
writeFileSync(justfile, `${output.join("\n").replace(/\n+$/, "")}\n`, "utf8");

console.log("\nRalph recipes are ready. Run: just init");
