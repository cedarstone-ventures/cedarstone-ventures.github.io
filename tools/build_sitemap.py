#!/usr/bin/env python3
"""Build sitemap.xml from what is actually in the repo.

Why this exists. Until 2026-07-27 sitemap.xml was hand-kept. Every one of its five
entries claimed `lastmod 2026-07-26` while all five pages had in fact been edited on
07-27 -- so the one file whose entire job is telling a crawler "this changed, come
back" was telling it the opposite. That is the same defect class as the `PAGES_CLAIMED
= 94` mirror in kdp-stack: a published artifact carrying a number a human had to
remember to update.

Three bindings, so the file cannot drift again:

  1. PAGES ARE DISCOVERED, not listed. Every .html in the repo is a candidate.
  2. lastmod COMES FROM GIT, not from a human. The date is the file's last commit.
  3. robots.txt IS THE AUTHORITY on what is public. A Disallow prefix removes the URL
     from the sitemap, so we can never advertise a URL we also forbid -- a real and
     common SEO defect. /review/ (the Chairman's pre-publish gallery) and /tools/ are
     excluded by exactly this route, not by a second hand-kept list that could
     disagree with robots.txt.

An unknown page ABORTS rather than getting a silent default priority. A new page is
something a human should weigh, and this vault's own lesson is to prefer tooling that
fails loudly over tooling that quietly guesses.

Usage:  python tools/build_sitemap.py [--check]
        --check exits 1 if the sitemap on disk differs from what this would write.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://deedwell.co"

# Crawl weighting is a judgement call, so it stays explicit. An .html file that is
# not named here aborts the build rather than defaulting silently.
WEIGHTS = {
    "/":              ("weekly",  "1.0"),
    "/checklist/":    ("weekly",  "0.9"),
    "/rental/":       ("weekly",  "0.9"),
    "/updates/":      ("monthly", "0.6"),
    "/privacy.html":  ("yearly",  "0.3"),
}


def disallowed_prefixes():
    """Read robots.txt so the sitemap can never contradict it."""
    robots = ROOT / "robots.txt"
    if not robots.exists():
        sys.exit("ABORT: robots.txt not found -- refusing to guess what is public.")
    out = []
    for line in robots.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        m = re.match(r"(?i)^disallow:\s*(\S+)$", line)
        if m:
            out.append(m.group(1))
    return out


def url_for(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def lastmod(path: Path) -> str:
    """The file's last commit date. Uncommitted edits fall back to today's tree."""
    # A pre-commit hook exports GIT_DIR/GIT_INDEX_FILE for its own repo context; when
    # that context is a linked worktree, this subprocess inherits it and resolves the
    # WORKTREE while being handed this checkout's paths -- every date comes back wrong
    # or empty and --check reports a drift that does not exist. Scrub git's env so the
    # query always reads the repo this script names via cwd.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    r = subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=short", "--", str(path)],
        cwd=ROOT, capture_output=True, text=True, env=env,
    )
    date = r.stdout.strip()
    if not date:
        sys.exit(f"ABORT: no git history for {path} -- commit it before it is published.")
    return date


def build() -> str:
    blocked = disallowed_prefixes()
    pages = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)

    entries, skipped = [], []
    for p in pages:
        u = url_for(p)
        if any(u.startswith(b) for b in blocked):
            skipped.append(u)
            continue
        if u not in WEIGHTS:
            sys.exit(
                f"ABORT: {u} is a public page with no crawl weighting.\n"
                f"  Add it to WEIGHTS in tools/build_sitemap.py, or Disallow it in robots.txt.\n"
                f"  Refusing to guess how important a new page is."
            )
        freq, pri = WEIGHTS[u]
        entries.append((u, lastmod(p), freq, pri))

    # Highest priority first, so the file reads as a statement of what matters.
    entries.sort(key=lambda e: (-float(e[3]), e[0]))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, mod, freq, pri in entries:
        lines += ["  <url>",
                  f"    <loc>{SITE}{u}</loc>",
                  f"    <lastmod>{mod}</lastmod>",
                  f"    <changefreq>{freq}</changefreq>",
                  f"    <priority>{pri}</priority>",
                  "  </url>"]
    lines.append("</urlset>")

    for u in skipped:
        print(f"  excluded by robots.txt: {u}")
    return "\n".join(lines) + "\n"


def main():
    check = "--check" in sys.argv
    want = build()
    target = ROOT / "sitemap.xml"
    have = target.read_text(encoding="utf-8") if target.exists() else ""

    if check:
        if have != want:
            print("DRIFTED: sitemap.xml does not match the repo.")
            print("  Run: python tools/build_sitemap.py")
            return 1
        print(f"sitemap.xml is current ({want.count('<url>')} URLs).")
        return 0

    if have == want:
        print(f"sitemap.xml already current ({want.count('<url>')} URLs).")
        return 0
    target.write_text(want, encoding="utf-8", newline="\n")
    print(f"sitemap.xml rebuilt ({want.count('<url>')} URLs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
