#!/usr/bin/env node
// Release consistency check, plus the guard that matters most for this repo:
// nothing organisation-specific may ever be committed. The pipeline runs
// against real PRs, a real Slack channel, and real colleagues' names, and all
// of that has to stay in ~/.claude/pr-control/ and out of git.

import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const problems = [];
const check = (cond, message) => { if (!cond) problems.push(message); };

const readJson = (rel) => {
  try { return JSON.parse(readFileSync(join(root, rel), 'utf8')); }
  catch (err) { problems.push(`${rel}: ${err.message}`); return null; }
};

const plugin = readJson('.claude-plugin/plugin.json');
const marketplace = readJson('.claude-plugin/marketplace.json');

// ---------------------------------------------------------------- manifests
if (plugin && marketplace) {
  for (const f of ['name', 'version', 'description', 'author', 'homepage', 'repository', 'license']) {
    check(plugin[f], `plugin.json is missing "${f}"`);
  }
  check(/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(plugin.version || ''), `version "${plugin.version}" is not semver`);

  const entry = (marketplace.plugins || []).find((p) => p.name === plugin.name);
  check(entry, `no marketplace entry named "${plugin.name}"`);
  if (entry) {
    check(entry.displayName === plugin.displayName, 'displayName differs between the manifests');
    check(entry.source === './', 'marketplace entry source should be "./"');
  }

  if (existsSync(join(root, 'CHANGELOG.md'))) {
    check(
      readFileSync(join(root, 'CHANGELOG.md'), 'utf8').includes(`## [${plugin.version}]`),
      `CHANGELOG.md has no "## [${plugin.version}]" section`,
    );
  } else problems.push('CHANGELOG.md is missing');
}

// ------------------------------------------------------------ shipped files
for (const f of [
  'pipeline/prconfig.py', 'pipeline/merge.py', 'pipeline/build_page.py',
  'pipeline/extract_sessions.py', 'pipeline/tracker_template.html',
  'scripts/smoke-page.mjs', 'config.example.json',
  'skills/pr-control/SKILL.md', 'README.md', 'LICENSE', 'docs/index.html',
]) {
  check(existsSync(join(root, f)), `${f} is missing`);
}

const skill = join(root, 'skills/pr-control/SKILL.md');
if (existsSync(skill)) {
  const front = readFileSync(skill, 'utf8').split('---')[1] || '';
  check(/^\s*name:\s*pr-control\s*$/m.test(front), 'SKILL.md must declare "name: pr-control"');
}

// --------------------------------------------------- python actually parses
for (const f of ['prconfig', 'merge', 'build_page', 'extract_sessions']) {
  try {
    execFileSync('python3', ['-m', 'py_compile', join(root, `pipeline/${f}.py`)], { stdio: 'pipe' });
  } catch (err) {
    problems.push(`pipeline/${f}.py does not compile: ${String(err.stderr || err.message).trim()}`);
  }
}

// ------------------------------------------------------------- leak guard
let tracked = [];
try {
  tracked = execFileSync('git', ['ls-files'], { cwd: root, stdio: 'pipe' }).toString().split('\n').filter(Boolean);
} catch { /* not a git repo yet — the file checks above still apply */ }

const FORBIDDEN_FILES = [
  /(^|\/)config\.json$/,
  /(^|\/)slack_mentions\.json$/,
  /(^|\/)linear_issues\.json$/,
  /(^|\/)sessions\.json$/,
  /(^|\/)prdata\.json$/,
  /(^|\/)pr-control\.html$/,
];
for (const file of tracked) {
  if (file.startsWith('tests/fixtures/')) continue; // synthetic, placeholders only
  for (const pattern of FORBIDDEN_FILES) {
    if (pattern.test(file)) problems.push(`${file} is tracked but must never be committed — it holds live org data`);
  }
}

// Any real Slack workspace or channel id that slipped into a tracked file.
const ALLOWED_LITERALS = new Set(['your-workspace.slack.com', 'C0000000000']);
const TEXT = /\.(py|html|json|md|mjs|js|yml|yaml|sh)$/;
for (const file of tracked) {
  if (!TEXT.test(file)) continue;
  const body = readFileSync(join(root, file), 'utf8');
  for (const m of body.match(/[A-Za-z0-9-]+\.slack\.com/g) || []) {
    if (!ALLOWED_LITERALS.has(m)) problems.push(`${file} contains a real Slack workspace: ${m}`);
  }
  for (const m of body.match(/\bC0[A-Z0-9]{8,}\b/g) || []) {
    if (!ALLOWED_LITERALS.has(m)) problems.push(`${file} contains a real Slack channel id: ${m}`);
  }
}

// The template must stay organisation-neutral — it labels itself from meta.
const tpl = join(root, 'pipeline/tracker_template.html');
if (existsSync(tpl)) {
  const body = readFileSync(tpl, 'utf8');
  check(body.includes('const M = META'), 'tracker_template.html lost its meta wiring');
  check(!/\.replace\('[a-z0-9-]+\/','/.test(body), 'tracker_template.html has a hardcoded org prefix — use ORGP');
}

const label = plugin ? `${plugin.name} ${plugin.version}` : 'release';
if (problems.length) {
  console.error(`✖ ${label} — ${problems.length} problem${problems.length === 1 ? '' : 's'}`);
  for (const p of problems) console.error(`  · ${p}`);
  process.exit(1);
}
console.log(`✔ ${label} — manifests agree, pipeline compiles, nothing organisation-specific is tracked`);
