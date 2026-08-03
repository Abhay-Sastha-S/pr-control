#!/usr/bin/env python3
"""Load the PR Control config.

Everything organisation-specific lives in one JSON file that is deliberately
*not* part of this repository — your org, your GitHub login, your Slack
workspace and channel, your teammates, your dependency chains. The repo ships
`config.example.json`; copy it and fill it in.

Resolution order (first hit wins):
  1. $PR_CONTROL_CONFIG
  2. ./config.json               (the scratch directory you're building in)
  3. ~/.claude/pr-control/config.json
"""
import json, os, re, sys

SEARCH = [
    os.environ.get("PR_CONTROL_CONFIG"),
    "config.json",
    os.path.expanduser("~/.claude/pr-control/config.json"),
]

_REQUIRED = [("github", "owner"), ("github", "me"), ("slack", "workspace"), ("slack", "channelId")]


def config_path():
    for candidate in SEARCH:
        if candidate and os.path.exists(candidate):
            return candidate
    sys.exit(
        "No PR Control config found. Copy config.example.json to "
        "~/.claude/pr-control/config.json and fill it in, or set $PR_CONTROL_CONFIG."
    )


def load():
    path = config_path()
    with open(path) as fh:
        cfg = json.load(fh)

    missing = [f"{a}.{b}" for a, b in _REQUIRED if not (cfg.get(a) or {}).get(b)]
    if missing:
        sys.exit(f"{path} is missing required keys: {', '.join(missing)}")

    cfg.setdefault("linear", {})
    cfg.setdefault("window", {})
    cfg.setdefault("serviceRank", {})
    cfg.setdefault("deps", [])
    cfg["_path"] = path
    return cfg


def ticket_re(cfg):
    """Regex matching this org's ticket ids, e.g. ABC-1234. Never matches when
    no prefix is configured, rather than matching everything."""
    prefix = (cfg.get("linear") or {}).get("ticketPrefix") or ""
    if not prefix:
        return re.compile(r"(?!)")
    return re.compile(rf"{re.escape(prefix)}-\d+")


def org_prefix(cfg):
    return cfg["github"]["owner"] + "/"
