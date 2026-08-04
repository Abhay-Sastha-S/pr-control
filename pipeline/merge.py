#!/usr/bin/env python3
"""Merge GitHub PRs + Slack mentions + Linear tickets + local Claude sessions
into one dataset, and compute the order the open PRs have to merge in.

Everything organisation-specific comes from the config (see prconfig.py).
"""
import json, datetime, re
import prconfig

CFG = prconfig.load()
GH = CFG["github"]
SLACK_CFG = CFG["slack"]
ME = GH["me"]
ME_SLACK = SLACK_CFG.get("meDisplayName", "")
REVIEWER = SLACK_CFG.get("reviewerLabel", "review")
CHANNEL = SLACK_CFG.get("channelName", "the review channel")
TICKET_RE = prconfig.ticket_re(CFG)
LINEAR_WS = (CFG.get("linear") or {}).get("workspace", "")

prs = {}
with open("prs.jsonl") as fh:
    for line in fh:
        p = json.loads(line)
        key = f"{p['repo']}#{p['number']}"
        prs[key] = p

slack = json.load(open("slack_mentions.json"))
sessions = json.load(open("sessions.json"))
linear = json.load(open("linear_issues.json"))

tickets_map = {}
with open("tickets.jsonl") as fh:
    for line in fh:
        t = json.loads(line)
        tickets_map[f"{t['repo']}#{t['number']}"] = t["tickets"]

# Ordering that no API knows about — usually stated in the review channel.
# kind "order": merge and deploy left to right; kind "companion": ship together.
DEPS = CFG["deps"]


CID = slack["channel_id"]
WS = slack["workspace"]

def permalink(ts, thread_ts=None):
    t = thread_ts or ts
    return f"https://{WS}/archives/{CID}/p{ts.replace('.','')}?thread_ts={t}&cid={CID}"

# attach slack mentions
slack_map = {}
for m in slack["mentions"]:
    when = datetime.datetime.fromtimestamp(float(m["ts"]), datetime.timezone.utc).isoformat()
    for pr in m["prs"]:
        slack_map.setdefault(pr, []).append({
            "who": m["who"], "when": when, "ts": m["ts"],
            "thread_ts": m.get("thread_ts", m["ts"]),
            "link": permalink(m["ts"], m.get("thread_ts")),
            "exact": True,
        })
for m in slack["channel_only_mentions"]:
    for pr in m["prs"]:
        slack_map.setdefault(pr, []).append({
            "who": m["who"], "when": m["date"], "ts": None, "thread_ts": None,
            "link": f"https://{WS}/archives/{CID}", "exact": False,
        })

# attach local sessions
sess_map = {}
for s in sessions:
    for pr, count in s["prs"].items():
        sess_map.setdefault(pr, []).append({
            "session": s["session"], "project": s["project"],
            "subagent": s["subagent"], "mtime": s["mtime"],
            "summary": s["summary"], "hits": count,
        })
for v in sess_map.values():
    v.sort(key=lambda x: (x["subagent"], -x["hits"] * 0 - x["mtime"]))

import os
_dir_index = {}
for root in ["~/Documents", "~/Desktop", "~/Downloads", "~"]:
    r = os.path.expanduser(root)
    try:
        for d in os.listdir(r):
            full = os.path.join(r, d)
            if os.path.isdir(full):
                _dir_index[full.replace("/", "-")] = full
    except OSError:
        pass

def resolve_project(slug):
    return _dir_index.get(slug, "")

CUTOFF = (CFG.get("window") or {}).get("start", "1970-01-01")

out = []
for key, p in prs.items():
    mentioned = key in slack_map
    local = key in sess_map
    recent = (p.get("updatedAt") or "") >= CUTOFF
    if not (mentioned or local or p["state"] == "OPEN" or recent):
        continue
    sess = []
    for s in sess_map.get(key, [])[:3]:
        path = resolve_project(s["project"])
        cmd = f"claude --resume {s['session']}"
        if path:
            cmd = f"cd {path} && " + cmd
        sess.append({**s, "path": path, "resume": cmd})
    tix = []
    fallback = sorted(set(TICKET_RE.findall(f"{p.get('title','')} {p.get('headRefName','')}")))
    for t in (tickets_map.get(key) or fallback)[:4]:
        li = linear.get(t)
        tix.append({
            "id": t,
            "url": (li or {}).get("url") or (f"https://linear.app/{LINEAR_WS}/issue/{t}" if LINEAR_WS else ""),
            "status": (li or {}).get("status", ""),
            "statusType": (li or {}).get("statusType", ""),
            "ticketTitle": (li or {}).get("title", ""),
        })
    # Deploy stage inferred from Linear (see memory: myfi-pr-deploy-lifecycle):
    #   In Review = on dev (1) · Ready For Prod = ready for prod (2) · Done = on prod (3)
    def _lin_stage(t):
        s = (t.get("status") or "").strip().lower()
        if t.get("statusType") == "completed" or s == "done":
            return 3
        if "ready" in s and "prod" in s:
            return 2
        if s == "in review":
            return 1
        return 0
    lin = max([_lin_stage(t) for t in tix], default=0)
    # Combine GitHub state + Linear deploy stage into one lifecycle status.
    if p["state"] == "CLOSED":
        status = "closed"
    elif lin >= 3:
        status = "prod"                       # merged + deployed to prod (Linear Done)
    elif p["state"] == "MERGED" or lin >= 2:
        status = "readyprod"                  # merged to main, not yet on prod
    elif lin >= 1:
        status = "dev"                        # deployed on dev (Linear In Review), still open
    elif p.get("isDraft"):
        status = "draft"
    else:
        rd = p.get("reviewDecision") or ""
        status = "changes" if rd == "CHANGES_REQUESTED" else "in1000x"
    deployStage = ["none", "dev", "readyprod", "prod"][lin]
    out.append({
        "id": key,
        "repo": p["repo"],
        "number": p["number"],
        "title": p["title"],
        "author": (p.get("author") or {}).get("login", ""),
        "state": p["state"],
        "status": status,
        "draft": bool(p.get("isDraft")),
        "reviewDecision": p.get("reviewDecision") or "",
        "branch": p.get("headRefName", ""),
        "base": p.get("baseRefName", ""),
        "url": p["url"],
        "createdAt": p.get("createdAt"),
        "updatedAt": p.get("updatedAt"),
        "mergedAt": p.get("mergedAt"),
        "labels": [l["name"] for l in (p.get("labels") or [])],
        "slack": sorted(slack_map.get(key, []), key=lambda m: str(m["when"])),
        "sessions": sess,
        "tickets": tix,
        "deployStage": deployStage,
    })

# Slack-mentioned PRs we couldn't fetch from GitHub (private/not in list window)
for key, mentions in slack_map.items():
    if key in prs:
        continue
    repo, num = key.rsplit("#", 1)
    out.append({
        "id": key, "repo": repo, "number": int(num), "title": "(not fetched from GitHub)",
        "author": "", "state": "UNKNOWN", "status": "unknown", "draft": False,
        "reviewDecision": "", "branch": "", "base": "",
        "url": f"https://github.com/{repo}/pull/{num}",
        "createdAt": None, "updatedAt": None, "mergedAt": None, "labels": [],
        "slack": sorted(mentions, key=lambda m: str(m["when"])),
        "sessions": [{**s, "resume": f"claude --resume {s['session']}"} for s in sess_map.get(key, [])[:3]],
    })

# wire dependencies onto PRs
by_id = {p["id"]: p for p in out}
for p in out:
    p["deps"] = []
for d in DEPS:
    chain = d["chain"]
    for i, pid in enumerate(chain):
        if pid not in by_id:
            continue
        entry = {"kind": d["kind"], "chain": chain, "note": d.get("note", ""),
                 "ticket": d.get("ticket", ""), "owner": d.get("owner", "")}
        if d["kind"] == "order":
            entry["before"] = chain[:i]
            entry["after"] = chain[i + 1:]
        by_id[pid]["deps"].append(entry)

# compute what each PR is waiting on
for p in out:
    wait = ""
    st = p["status"]
    if st == "prod":
        wait = "Done — merged and deployed to prod"
    elif st == "readyprod":
        wait = "Ready for prod — merged to main, awaiting the prod build (manual)"
    elif st == "dev":
        wait = "On dev — deployed to dev; merge to main when it's proven out"
    elif p["state"] == "OPEN":
        if p["draft"]:
            wait = "Author — still a draft"
        elif st == "changes":
            wait = "Author — changes requested"
        elif p.get("reviewDecision") == "APPROVED":
            wait = f"Human merge — {REVIEWER} approved, merging stays with a human"
        else:
            wait = f"In {REVIEWER} — review requested" if p["slack"] else f"Not yet posted to #{CHANNEL} for review"
    if p["state"] != "CLOSED":
        for d in p["deps"]:
            if d["kind"] == "order":
                unmerged = [b for b in d.get("before", []) if by_id.get(b, {}).get("state") not in ("MERGED", None) and b in by_id]
                if unmerged:
                    who = d.get("owner") or "upstream"
                    wait = f"Blocked — {', '.join(unmerged)} must merge/deploy first ({who})"
    p["waitingOn"] = wait

# ---- dependency edges over the FULL set (a must merge/deploy before b) ----
SERVICE_RANK = CFG["serviceRank"]
def rank(pid):
    return SERVICE_RANK.get(pid.rsplit("#", 1)[0], 1)
def order_pair(x, y):
    rx, ry = rank(x), rank(y)
    if rx != ry:
        return (x, y) if rx < ry else (y, x)
    cx, cy = by_id[x].get("createdAt") or "", by_id[y].get("createdAt") or ""
    return (x, y) if cx <= cy else (y, x)

edges, seen_pairs = [], set()
def add_edge(a, b, typ, note="", owner=""):
    if a == b or a not in by_id or b not in by_id:
        return
    k = (frozenset((a, b)), typ)
    if k in seen_pairs:
        return
    seen_pairs.add(k)
    edges.append({"a": a, "b": b, "type": typ, "note": note, "owner": owner})

for d in DEPS:
    ch = [c for c in d["chain"] if c in by_id]
    if d["kind"] == "order":
        for i in range(len(ch) - 1):
            add_edge(ch[i], ch[i + 1], "order", d.get("note", ""), d.get("owner", ""))
    else:
        for i in range(len(ch)):
            for j in range(i + 1, len(ch)):
                a, b = order_pair(ch[i], ch[j])
                add_edge(a, b, "companion", d.get("note", "ship together"))

from collections import defaultdict
open_by_ticket = defaultdict(list)
for p in out:
    if p["state"] == "OPEN":
        for t in p["tickets"]:
            open_by_ticket[t["id"]].append(p["id"])
for t, ids in open_by_ticket.items():
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = order_pair(ids[i], ids[j])
            add_edge(a, b, "ticket", f"both under {t}")

heads = {p["branch"]: p["id"] for p in out if p.get("branch")}
for p in out:
    if p["state"] == "OPEN" and p.get("base") in heads:
        add_edge(heads[p["base"]], p["id"], "stack", f"stacked on branch {p['base']}")

# ---- mine + linked-foreign selection ----
def is_mine(p):
    return (p["author"] == ME
            or (bool(ME_SLACK) and any(m["who"] == ME_SLACK for m in p["slack"]))
            or bool(p["sessions"]))
mine_ids = {p["id"] for p in out if is_mine(p)}

# same-repo soft ordering: in every repo where I have an open PR, chain ALL
# open PRs (anyone's) oldest-first — an older PR ahead of yours in the same
# repo merges first and likely forces a rebase
my_open_repos = {p["repo"] for p in out if p["id"] in mine_ids and p["state"] == "OPEN"}
open_by_repo = defaultdict(list)
for p in out:
    if p["state"] == "OPEN" and p["repo"] in my_open_repos and not p.get("isDraft"):
        open_by_repo[p["repo"]].append(p["id"])
for ids in open_by_repo.values():
    ids.sort(key=lambda i: by_id[i].get("createdAt") or "")
    for i in range(len(ids) - 1):
        add_edge(ids[i], ids[i + 1], "repo", "same repo — merge oldest first to avoid rebase churn")

linked = set()
for e in edges:
    if e["a"] in mine_ids and e["b"] not in mine_ids:
        linked.add(e["b"])
    if e["b"] in mine_ids and e["a"] not in mine_ids:
        linked.add(e["a"])

for p in out:
    p["mine"] = p["id"] in mine_ids
    p["foreign"] = p["id"] in linked

out = [p for p in out if p["mine"] or p["foreign"]]
kept = {p["id"] for p in out}
edges = [e for e in edges if e["a"] in kept and e["b"] in kept]

out.sort(key=lambda p: p.get("createdAt") or "9999")
counts = {}
for p in out:
    counts[p["status"]] = counts.get(p["status"], 0) + 1
json.dump({"prs": out, "edges": edges}, open("prdata.json", "w"), indent=0)
print(len(out), "PRs in dataset |", sum(1 for p in out if p["foreign"]), "foreign linked |", len(edges), "edges")
print("status counts:", counts)
print("edges:", *[f"{e['a']} -[{e['type']}]-> {e['b']}" for e in edges], sep="\n  ")
