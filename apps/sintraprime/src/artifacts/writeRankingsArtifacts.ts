import fs from "node:fs";
import path from "node:path";
import type { RankingsBundle } from "../operator/computeRankings.js";

export function writeRankingsArtifacts(bundle: RankingsBundle) {
  const base = path.join("runs", "rankings");
  const dirs = {
    operators: path.join(base, "operators"),
    fingerprints: path.join(base, "fingerprints"),
    domains: path.join(base, "domains"),
    bundles: path.join(base, "bundles"),
  };
  for (const d of Object.values(dirs)) fs.mkdirSync(d, { recursive: true });

  // write per-key artifacts
  for (const o of bundle.operators) {
    fs.writeFileSync(path.join(dirs.operators, `${safe(o.operator)}.json`), JSON.stringify(o, null, 2));
  }
  for (const f of bundle.fingerprints) {
    fs.writeFileSync(path.join(dirs.fingerprints, `${safe(f.fingerprint)}.json`), JSON.stringify(f, null, 2));
  }
  for (const d of bundle.domains) {
    fs.writeFileSync(path.join(dirs.domains, `${safe(d.domain)}.json`), JSON.stringify(d, null, 2));
  }

  // write a bundle snapshot
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const bundlePath = path.join(dirs.bundles, `${ts}.json`);
  fs.writeFileSync(bundlePath, JSON.stringify(bundle, null, 2));
  return { bundlePath };
}

function safe(s: string) {
  return s.replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 160);
}
