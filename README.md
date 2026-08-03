# PR Control

One page for every pull request you have in flight — and, more usefully, the
**order they actually have to merge in**.

It cross-references four sources that never talk to each other: your GitHub PRs,
the review-channel messages that asked someone to look at them, the tickets they
close, and the local Claude Code sessions that wrote them.

**[abhay-sastha-s.github.io/pr-control](https://abhay-sastha-s.github.io/pr-control/)**

```bash
/plugin marketplace add Abhay-Sastha-S/pr-control
/plugin install pr-control
/pr-control
```

---

## Why it exists

Once you have more than three or four PRs open across a few repos, the question
stops being *"what's the status of this PR"* — GitHub answers that fine — and
becomes:

- **What is each one actually waiting on?** "Open" is not a status. Waiting for
  a first review, waiting on requested changes, approved and waiting for a human
  to press merge, and blocked behind someone else's deploy are four completely
  different situations, and only one of them is your move.
- **Which one do I merge first?** The real ordering lives in three places GitHub
  cannot see: a sentence in a Slack thread ("merge the backend one first or the
  page 404s"), the fact that two PRs close the same ticket, and the fact that
  two of yours are stacked branches. Get it wrong and you rebase all afternoon.
- **Did I ever actually ask for review?** A PR nobody was told about isn't in
  review, it's just open. That gap is invisible on GitHub — the PR looks
  perfectly healthy.
- **What was I doing on this one?** The reasoning is in a Claude Code session
  from four days ago, identified by a UUID you don't remember.

Every one of those answers exists. They're just in four different tools, none of
which joins to the others. This does the join, and draws the result as a merge
order you can act on top-down.

### What it computes that nothing else does

The heart of it is the **edge set** — "a must merge before b" — derived in
precedence order:

| Source | Meaning |
| --- | --- |
| Channel-stated chains | Someone said so in the review channel. Highest authority; hand-maintained in config because no API exposes it. |
| Branch stacks | `b`'s base branch is `a`'s head. Structural. |
| Shared open tickets | Two open PRs closing the same ticket ship together. |
| Same-repo ordering | Older open PRs in a repo where you have one merge first, or you rebase. |

Ties break on a configurable service rank — shared libraries merge before
services, services before user-facing apps. The result is rendered as a parallel
tree: what's ready now, what's gated, and whose deploy you're waiting on.

Foreign PRs — other people's — are pulled in **only** when they share an edge
with one of yours, so the page stays about your work while still showing the
person you're blocked behind.

---

## Nothing about your organisation is in this repo

That's the deliberate part. Every organisation-specific value — your org, your
GitHub login, your Slack workspace and channel, your teammates' names, your
Linear workspace, your dependency chains — lives in **one config file that is
not committed**:

```bash
cp config.example.json ~/.claude/pr-control/config.json
$EDITOR ~/.claude/pr-control/config.json
```

`.gitignore` covers `config.json`, `slack_mentions.json`, and every intermediate
file the pipeline produces. `scripts/check-release.mjs` fails the build if a
config file, a Slack export, or a built page is ever staged, so the repo can't
start leaking by accident.

Your `slack_mentions.json` — real names, real message timestamps — stays beside
the config in `~/.claude/pr-control/` and is never part of a commit.

---

## What it reads

Worth knowing before you run it, because the answer is "quite a lot":

- **GitHub**, via the `gh` CLI you're already authenticated with — PR metadata
  only, for the repos you list.
- **Slack**, read-only, via an MCP server — searching one channel for review
  requests. The page never gets Slack *write* tools; replying is copy-to-
  clipboard plus a deep link into the thread.
- **Linear**, read-only — issue titles and statuses.
- **`~/.claude/projects`**, read-only — your local Claude Code transcripts, scanned
  for GitHub PR URLs so each PR can link back to the session that wrote it, with
  a ready-to-paste `claude --resume` command. Transcript *content* never leaves
  your machine; only the session id, project directory, and the existing summary
  line are used.

Everything runs locally. The only thing that goes anywhere is the finished page,
and only when you publish it.

---

## Install

```bash
/plugin marketplace add Abhay-Sastha-S/pr-control
/plugin install pr-control
```

Then configure it once, and run `/pr-control` whenever you want a refresh.

**Requirements:** Python 3.9+, Node 18+ (for the page smoke test), the `gh` CLI
authenticated, and — for the Slack and Linear columns — those MCP servers
connected in Claude Code. Without them the page still builds; those sections are
simply empty.

## The pipeline

```
gh pr list ─────────────► prs.jsonl ──┐
slack search ──► slack_mentions.json ─┤
linear issues ─► linear_issues.json ──┼──► merge.py ──► prdata.json
extract_sessions.py ──► sessions.json ┤                      │
gh pr list (bodies) ──► tickets.jsonl ┘                      ▼
                                              build_page.py ──► pr-control.html
                                                                     │
                                            scripts/smoke-page.mjs ──┴──► publish
```

| File | Does |
| --- | --- |
| `pipeline/prconfig.py` | Finds and validates the config; fails loudly rather than guessing |
| `pipeline/extract_sessions.py` | Scans `~/.claude/projects` for PR references. Fully generic — no config needed |
| `pipeline/merge.py` | The join and the edge computation. Everything specific comes from config |
| `pipeline/build_page.py` | Injects the dataset plus a `meta` block into the template |
| `pipeline/tracker_template.html` | The page. Holds no organisation strings — it labels itself from `meta` |
| `scripts/smoke-page.mjs` | Executes the built page's JS against a DOM shim |

**The smoke test earns its place.** The page is one large inline script, and
`node --check` only proves it parses — a `const` used before its declaration
parses perfectly and then renders a blank page. `smoke-page.mjs` actually
executes it and fails on load-time errors. It caught exactly that bug during
packaging.

## Releasing

`version` in `.claude-plugin/plugin.json` is the source of truth.

```bash
# bump the version, add a matching "## [x.y.z]" section to CHANGELOG.md
node scripts/check-release.mjs
claude plugin validate . --strict
claude plugin tag .
git push origin main --follow-tags
```

## Credits

- **[Claude Code](https://claude.com/claude-code)**, by
  [Anthropic](https://www.anthropic.com/) — the sessions column reads its local
  transcript format, and the skill is what drives the refresh.
- **[GitHub CLI](https://cli.github.com/)** (`gh`) — every PR fact comes from it.
- **[Slack](https://slack.com/)** and **[Linear](https://linear.app/)** — read
  through their MCP servers. Both are their companies' products; this only reads
  from them.
- **[jq](https://jqlang.github.io/jq/)** — shapes the `gh` output in the refresh
  steps.
- **No runtime dependencies** — Python standard library and one inline HTML page.
  Nothing is bundled or vendored.
- **Written with** [Claude Code](https://claude.com/claude-code), which is
  co-author on the commits that built this.

## Trademarks and affiliation

Claude, Claude Code, and Anthropic are trademarks of Anthropic. GitHub, Slack,
and Linear are trademarks of their respective owners. This project is
**unofficial** and is not affiliated with, endorsed by, or supported by any of
them.

## License

MIT — see [LICENSE](LICENSE).
