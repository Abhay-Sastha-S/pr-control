#!/usr/bin/env python3
"""Inject the merged dataset into the tracker template.

    python3 build_page.py "<ISO timestamp>"  ->  pr-control.html

Everything the page needs to label itself — org, your login, channel, reviewer
name, merge-order ranks — rides along in `meta`, so the template carries no
organisation-specific strings of its own.
"""
import json, sys
import prconfig

CFG = prconfig.load()
GH = CFG["github"]
SL = CFG["slack"]

data = json.load(open("prdata.json"))

meta = {
    "snapshot": sys.argv[1] if len(sys.argv) > 1 else "",
    "windowStart": (CFG.get("window") or {}).get("start", ""),
    "org": GH["owner"],
    "me": GH["me"],
    "channelId": SL["channelId"],
    "channelName": SL.get("channelName", "review"),
    "channelLink": f"https://{SL['workspace']}/archives/{SL['channelId']}",
    "reviewer": SL.get("reviewerLabel", "review"),
    "linearWorkspace": (CFG.get("linear") or {}).get("workspace", ""),
    "serviceRank": CFG.get("serviceRank", {}),
    "linearCount": sum(1 for p in data["prs"] if p.get("tickets")),
}

blob = json.dumps(
    {"prs": data["prs"], "edges": data["edges"], "meta": meta},
    separators=(",", ":"),
).replace("</", "<\\/")

page = open("tracker_template.html").read().replace("__PRDATA__", blob)
open("pr-control.html", "w").write(page)
print(f"pr-control.html written — {len(data['prs'])} PRs, {len(data['edges'])} edges")
