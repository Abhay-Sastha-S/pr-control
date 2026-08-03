#!/usr/bin/env node
// Print the CHANGELOG section for the current manifest version, so the GitHub
// release notes and the changelog can never drift apart.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const { version } = JSON.parse(readFileSync(join(root, '.claude-plugin/plugin.json'), 'utf8'));
const changelog = readFileSync(join(root, 'CHANGELOG.md'), 'utf8');

const start = changelog.indexOf(`## [${version}]`);
if (start === -1) {
  console.error(`No "## [${version}]" section in CHANGELOG.md`);
  process.exit(1);
}
// The section runs until the next version heading, or the trailing block of
// link-reference definitions if this is the oldest entry.
const rest = changelog.slice(start).split('\n').slice(1);
const end = rest.findIndex((line) => /^## \[/.test(line) || /^\[[^\]]+\]:\s*http/.test(line));

console.log((end === -1 ? rest : rest.slice(0, end)).join('\n').trim());
