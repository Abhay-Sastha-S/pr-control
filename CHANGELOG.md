# Changelog

All notable changes to this plugin are documented here. `version` in
`.claude-plugin/plugin.json` is the source of truth;
`scripts/check-release.mjs` fails if it has no section below.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versioning is [semantic](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] — 2026-08-04

### Added

- **Refresh helper** — a `⟳ Refresh` control that explains the page is a
  GitHub snapshot (a shared page can't read GitHub live), shows the "as of"
  time, and one-click-copies the `/pr-control` rebuild command. Points at
  scheduling the skill for hands-off refresh.
- **Conversational Merge Copilot** — the assistant now holds context: name a
  PR once and refer to it as "it", answer a "which PR?" prompt on the next
  line, confirm a suggested action with "yes". Understands greetings, thanks,
  synonyms, and free-form phrasing, and falls back with suggestions instead of
  a dead end. Still grounded in the graph — it is not a language model and says
  so if asked.

### Fixed

- **Slack actions in the published page** — clipboard and `window.open` are
  frequently blocked in the artifact's sandboxed iframe, so "continue chat"
  silently did nothing. Copy now falls back to a select-and-`execCommand` path
  (and tells you to press ⌘/Ctrl+C if even that is blocked), and every
  open-in-Slack affordance is a real anchor the browser can follow. The reply
  box is pre-filled with a review ping. The same robust copy is used for
  resume-command and copilot buttons.

## [1.1.0] — 2026-08-03

### Added

- **Merge Copilot** — a grounded assistant panel on the merge-order view. It
  reads the built PR graph (dependencies, authorship, block state) and answers
  in plain language: what's mergeable in parallel right now, the critical path,
  who is waiting on you, what is blocking a given PR, and per-PR status. It
  drives the tree — jumping to and pulsing the PR it names, and marking PRs
  merged so the unlocked wave lights up — and composes a review ping for the
  channel. Honouring the read-only-Slack rule, it **drafts and deep-links; it
  never sends Slack or merges anything.** Runs entirely client-side over the
  data already in the page, so it works on the published page with no backend.

### Changed

- Landing page documents the three views (Pipeline, Timeline replay, Merge
  order) and the Merge Copilot, and clarifies that copilot drafts follow the
  same copy-and-deep-link path as every other Slack reply.
- Landing page rebuilt on the shared mono-display chassis used by the sibling
  plugin pages, carrying the tracker's own palette, and centred on an animated
  replica of the real merge-order view: parallel tracks with branching
  dependency wires and a scripted Merge Copilot exchange that marks a PR merged
  and lights up the wave it unlocks.

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
