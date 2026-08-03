#!/usr/bin/env python3
"""Extract PR references from local Claude Code session files."""
import json, os, re, glob, sys

ROOT = os.path.expanduser("~/.claude/projects")
PR_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/(\d+)")
out = []

for f in glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True):
    rel = os.path.relpath(f, ROOT)
    parts = rel.split(os.sep)
    project = parts[0]
    is_subagent = "subagents" in parts
    prs = {}
    summary = ""
    first_prompt = ""
    try:
        with open(f, "r", errors="ignore") as fh:
            for line in fh:
                if not summary and '"type":"summary"' in line.replace(" ", ""):
                    try:
                        summary = json.loads(line).get("summary", "")[:100]
                    except Exception:
                        pass
                if not first_prompt and '"type":"user"' in line.replace(" ", ""):
                    try:
                        rec = json.loads(line)
                        msg = rec.get("message", {})
                        c = msg.get("content")
                        if isinstance(c, str):
                            first_prompt = c[:100]
                        elif isinstance(c, list):
                            for blk in c:
                                if isinstance(blk, dict) and blk.get("type") == "text":
                                    first_prompt = blk.get("text", "")[:100]
                                    break
                    except Exception:
                        pass
                for m in PR_RE.finditer(line):
                    org, repo, num = m.group(1), m.group(2), m.group(3)
                    prs[f"{org}/{repo}#{num}"] = prs.get(f"{org}/{repo}#{num}", 0) + 1
    except Exception:
        continue
    if not prs:
        continue
    out.append({
        "session": os.path.basename(f)[:-6],
        "project": project,
        "subagent": is_subagent,
        "mtime": int(os.path.getmtime(f)),
        "summary": summary or first_prompt,
        "prs": prs,
    })

out.sort(key=lambda s: -s["mtime"])
dest = sys.argv[1] if len(sys.argv) > 1 else "sessions.json"
with open(dest, "w") as fh:
    json.dump(out, fh, indent=1)
print(f"{len(out)} sessions with PR refs -> {dest}")
