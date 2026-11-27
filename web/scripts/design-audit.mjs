#!/usr/bin/env node
/**
 * SintraPrime design audit — deterministic UI quality checks.
 *
 * Pattern (deterministic, no-new-deps quality rules for AI-generated
 * frontends) inspired by pbakaus/impeccable (Apache-2.0).
 *
 * Checks (all against web/DESIGN.md):
 *   1. HEX_OUTSIDE_TOKENS — hex color literals in component/code files.
 *      Colors belong in the Tailwind theme (tailwind.config.ts), the token
 *      module (src/design/tokens.ts), or the canonical component classes
 *      (src/index.css). Everywhere else they are violations.
 *   2. IMG_MISSING_ALT — <img> tags without an alt attribute (alt="" is fine).
 *   3. INLINE_STYLE — inline style={...} / style="..." in components.
 *
 * Usage:  node scripts/design-audit.mjs        (from web/)
 * Exit:   0 = pass, 1 = findings.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(__dirname, '..');
const SRC_ROOT = join(WEB_ROOT, 'src');

// Files that ARE the design system — hex literals are legal here and only here.
const TOKEN_FILES = new Set([
  'tailwind.config.ts', // web/tailwind.config.ts (theme tokens)
  join('src', 'design', 'tokens.ts'),
  join('src', 'index.css'), // canonical component classes
]);

const SCAN_EXTS = new Set(['.ts', '.tsx', '.js', '.jsx', '.css']);
const SKIP_DIRS = new Set(['node_modules', 'dist', 'build', '.git', 'coverage']);

const HEX_RE = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/g;
const IMG_RE = /<img\b[^>]*>/g;
const ALT_RE = /\balt\s*=/;
const INLINE_STYLE_RE = /\bstyle\s*=\s*(\{|")/;

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if ([...SCAN_EXTS].some((ext) => full.endsWith(ext))) out.push(full);
  }
  return out;
}

function isTokenFile(absPath) {
  const rel = relative(WEB_ROOT, absPath);
  return TOKEN_FILES.has(rel);
}

function isComponentFile(absPath) {
  return /\.(tsx|jsx|ts|js)$/.test(absPath);
}

const findings = [];

function report(rule, file, line, excerpt) {
  findings.push({ rule, file: relative(WEB_ROOT, file), line, excerpt: excerpt.trim().slice(0, 120) });
}

function auditFile(file) {
  const text = readFileSync(file, 'utf8');
  const lines = text.split('\n');
  const tokenFile = isTokenFile(file);

  lines.forEach((line, i) => {
    const lineNo = i + 1;

    // 1. Hex outside tokens
    if (!tokenFile) {
      HEX_RE.lastIndex = 0;
      let m;
      while ((m = HEX_RE.exec(line)) !== null) {
        report('HEX_OUTSIDE_TOKENS', file, lineNo, `hardcoded color ${m[0]} — use a theme token or tokens.ts`);
      }
    }

    // 2. img without alt
    if (isComponentFile(file)) {
      IMG_RE.lastIndex = 0;
      let m;
      while ((m = IMG_RE.exec(line)) !== null) {
        if (!ALT_RE.test(m[0])) {
          report('IMG_MISSING_ALT', file, lineNo, '<img> without alt attribute');
        }
      }

      // 3. inline style
      if (INLINE_STYLE_RE.test(line)) {
        report('INLINE_STYLE', file, lineNo, 'inline style= — move to a class or token');
      }
    }
  });
}

const files = walk(SRC_ROOT);
for (const f of files) auditFile(f);

console.log(`design-audit: scanned ${files.length} files under src/`);
if (findings.length === 0) {
  console.log('PASS — no design violations found.');
  process.exit(0);
}

const byRule = {};
for (const f of findings) {
  byRule[f.rule] = byRule[f.rule] || [];
  byRule[f.rule].push(f);
}

for (const [rule, list] of Object.entries(byRule)) {
  console.log(`\n[${rule}] ${list.length} finding(s):`);
  for (const f of list) console.log(`  ${f.file}:${f.line} — ${f.excerpt}`);
}

console.log(`\nFAIL — ${findings.length} design violation(s) in ${files.length} files.`);
console.log('See web/DESIGN.md §9 and web/src/design/CHECKLIST.md.');
process.exit(1);
