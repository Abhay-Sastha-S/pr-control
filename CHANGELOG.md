# Changelog

All notable changes to this plugin are documented here. `version` in
`.claude-plugin/plugin.json` is the source of truth;
`scripts/check-release.mjs` fails if it has no section below.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versioning is [semantic](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] — 2026-08-03

First public release.

### Added

- **`/pr-control` skill** — rebuilds the tracker from GitHub, the review
  channel, Linear, and local Claude Code sessions, then republishes it.
- **The join** — one dataset cross-referencing PR state, the channel message
  that asked for review, the tickets a PR closes, and the local sessions that
  wrote it, with a ready-to-paste `claude --resume` per session.
- **Merge-order computation** — an edge set built in precedence order from
  channel-stated chains, branch stacks, shared open tickets, and same-repo
  ordering, with ties broken by a configurable service rank. Rendered as a
  parallel tree of what's ready now and what's gated behind whose deploy.
- **Foreign-PR linking** — other people's PRs appear only when they share an
  edge with an open one of yours.
- **`waitingOn` per PR** — distinguishes waiting on first review, on requested
  changes, on a human merge after approval, and blocked behind an upstream
  deploy.
- **`scripts/smoke-page.mjs`** — executes the built page's inline JS against a
  DOM shim, catching load-time errors that a syntax check cannot. It caught a
  use-before-declaration bug during packaging that would have rendered a blank
  page.
- **Config-driven throughout** — org, login, channel, workspace, service ranks,
  and dependency chains all live in an uncommitted config file;
  `config.example.json` documents the shape.
- Project site, release checks, and CI matching the other plugins in this set.

[Unreleased]: https://github.com/Abhay-Sastha-S/pr-control/compare/pr-control--v1.0.0...HEAD
[1.0.0]: https://github.com/Abhay-Sastha-S/pr-control/releases/tag/pr-control--v1.0.0
