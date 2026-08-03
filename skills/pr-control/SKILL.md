---
name: pr-control
description: >
  Rebuild and republish the PR Control tracker — a single page cross-referencing
  your open GitHub PRs with the review-channel messages that asked for review,
  the Linear tickets they close, and the local Claude Code sessions that wrote
  them, plus the order they have to merge in. Use when the user says
  /pr-control, "refresh the PR tracker", "update PR control", or asks where
  their PRs stand.
---

# PR Control — refresh and republish

Rebuilds the tracker from live data and republishes it. Config lives at
`~/.claude/pr-control/config.json` (see `config.example.json` in the plugin
repo); it holds the org, your GitHub login, the review channel, the Linear
workspace, merge-order ranks, and the hand-maintained dependency chains.

Work in the session scratchpad. Copy the plugin's `pipeline/` files there first,
along with your `slack_mentions.json` and `config.json` from
`~/.claude/pr-control/`.

## Refresh steps

Read the config first — every `<placeholder>` below comes from it.

1. **GitHub** — for each repo in `github.repos`:
   `gh pr list -R <owner>/<repo> --state all --limit <prLimit> --json number,title,state,isDraft,reviewDecision,headRefName,baseRefName,url,author,createdAt,updatedAt,mergedAt,labels | jq -c --arg repo <owner>/<repo> '.[] | {repo:$repo} + .'` → append to `prs.jsonl`.
2. **Slack** — search `"<slack.searchPhrase>" in:#<slack.channelName>` (channel
   `<slack.channelId>`), sorted by timestamp, 1–2 pages. Add any *new* messages
   to `slack_mentions.json` as `{ts, who, prs}`; permalinks are derived. Watch
   the channel for **newly stated dependencies** ("merge X first", companion
   PRs, deploy gates) and append them to `deps` in the config — that ordering
   exists nowhere else.
3. **Linear** — `list_issues` with `updatedAt: -P21D`, limit 250, fields
   `title,status,statusType,url` → `linear_issues.json` keyed by ticket id.
   Parse the saved tool-result file; it can exceed the token limit.
4. **Local sessions** — `python3 extract_sessions.py sessions.json`.
5. **Tickets** — `gh pr list --json number,title,body,headRefName` per repo,
   scan for the configured ticket prefix → `tickets.jsonl`. `merge.py` also
   falls back to the title and branch name.
6. **Build** — `python3 merge.py`, then
   `python3 build_page.py "<current ISO timestamp>"` → `pr-control.html`.
   Then **`node scripts/smoke-page.mjs pr-control.html`** before publishing —
   it executes the page's inline JS against a DOM shim and catches load-time
   errors that a syntax check misses.
7. **Publish** — the Artifact tool with `file_path: pr-control.html`, the
   artifact `url` from your config's `artifactUrl` (required from any
   conversation that did not originally publish it), and favicon `🔀`. **Omit
   `capabilities`** so the stored declaration carries forward.

## Rules baked into the data — don't undo them

- **Mine-only filter** — keep PRs authored by `github.me`, requested by
  `slack.meDisplayName` in the channel, or touched by a local Claude session,
  plus *foreign* PRs (`foreign: true`) that share a dependency edge with an open
  one of yours. Foreign PRs appear only in the merge-order tree.
- **Edge precedence** (a before b): channel-stated order chains > branch stacks >
  shared open tickets > same-repo open PRs oldest-first, in any repo where you
  have an open PR. Ties break on `serviceRank`: libraries first, user-facing
  apps last.
- Approval and merging are separate — whoever reviews does not merge. Merging to
  the default branch reaches the dev environment; production promotion is
  manual. Never present production as automatic.
- No Slack write tools from the page. Continuing a thread stays copy-reply plus
  a thread deep-link, with live reads via `slack_read_thread`.

After publishing, tell the user **what changed since the last sync** — new PRs,
status moves, blockers created or cleared — rather than re-describing the page.
