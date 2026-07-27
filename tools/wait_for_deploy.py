#!/usr/bin/env python3
"""Block until the bytes GitHub Pages SERVES match the bytes we committed.

Why this exists. On 2026-07-27 at 10:2x a pulse pushed `5919f5e`, re-read the live
page immediately, and got the OLD bytes back: `/checklist/` still had no `72.5` and
`/rental/` still said `totall`. GitHub Pages builds asynchronously, so **a push is not
a deploy**. The same pulse then hit the mirror-image trap: after the served bytes had
confirmed the fix, a browser navigation to the new anchor reported it missing, because
the NAVIGATION was cached while the probe was not. Both cost diagnosis time, and both
are the same missing thing -- nobody could ask "has it actually landed yet?" and get an
answer from evidence.

This is that answer. For every published page it compares the sha256 of the local file
against the sha256 of what the origin actually returns, and polls until they agree or
the timeout expires. It is the machine form of this vault's own rule: claim success
only from the served artifact, never from the confirmation that the push succeeded.

NEWLINES ARE NORMALISED BEFORE HASHING, and that is not a shortcut. This repo is
checked out on Windows with `core.autocrlf` behaviour that stores LF and hands the
working tree CRLF -- git says so on nearly every commit ("LF will be replaced by CRLF").
Pages serves the stored LF bytes. Hashing raw bytes would therefore report every page
as never-deployed, forever: a check that can only ever fail is worse than no check,
because the first person to see it red will switch it off.

The URL for each file is taken from `build_sitemap.url_for`, not restated here. That
module already resolves index.html -> "/" and honours robots.txt as the authority on
what is public, and a second copy of that mapping would be a second thing to keep true.

Usage:
    python tools/wait_for_deploy.py                 # all published pages
    python tools/wait_for_deploy.py --timeout 600
    python tools/wait_for_deploy.py checklist/index.html   # just these

Exit 0 = every page checked is live and byte-current. Exit 1 = timed out, and it
prints exactly which pages are still stale rather than a bare failure.
"""

import argparse
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sitemap import url_for  # noqa: E402  - reused, deliberately not restated

ROOT = Path(__file__).resolve().parent.parent
SITEMAP = ROOT / "sitemap.xml"
UA = "Mozilla/5.0 (compatible; DeedwellDeployCheck/1.0)"


def norm(b: bytes) -> str:
    """Hash newline-normalised content. See the CRLF note in the docstring."""
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def published_urls() -> list:
    """The sitemap is the authority on what is public -- it is built from robots.txt."""
    if not SITEMAP.exists():
        sys.exit("ABORT: sitemap.xml not found. Run tools/build_sitemap.py first.")
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", SITEMAP.read_text(encoding="utf-8"))
    if not urls:
        sys.exit("ABORT: sitemap.xml parsed to zero URLs -- refusing to check nothing.")
    return urls


def pairs(only: list) -> list:
    """Map each local .html file to its live URL via build_sitemap.url_for."""
    urls = published_urls()
    out = []
    for p in sorted(ROOT.rglob("*.html")):
        if ".git" in p.parts:
            continue
        try:
            path_part = url_for(p)
        except Exception:
            continue
        match = [u for u in urls if u.endswith(path_part)]
        if not match:
            continue  # excluded by robots.txt, so not something we publish
        rel = p.relative_to(ROOT).as_posix()
        if only and rel not in only:
            continue
        out.append((rel, p, match[0]))
    return out


def fetch(url: str) -> bytes:
    # Cache-bust: a plain fetch can be answered from an intermediate cache, which is
    # exactly how a stale page gets "verified" as fresh.
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        f"{url}{sep}_dc={int(time.time() * 1000)}",
        headers={"User-Agent": UA, "Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="repo-relative .html paths (default: all)")
    ap.add_argument("--timeout", type=int, default=420, help="seconds (default 420)")
    ap.add_argument("--interval", type=int, default=15, help="seconds between polls")
    args = ap.parse_args()

    targets = pairs(args.files)
    if not targets:
        sys.exit("ABORT: no published pages matched -- refusing to report success on nothing.")

    print(f"Waiting for {len(targets)} page(s) to serve their committed bytes:")
    for rel, _, url in targets:
        print(f"  {rel:<28} -> {url}")

    deadline = time.time() + args.timeout
    pending = list(targets)
    while True:
        still = []
        for rel, path, url in pending:
            want = norm(path.read_bytes())
            try:
                got = norm(fetch(url))
            except urllib.error.HTTPError as e:
                print(f"  .. {rel}: HTTP {e.code}")
                still.append((rel, path, url))
                continue
            except Exception as e:
                print(f"  .. {rel}: {type(e).__name__}")
                still.append((rel, path, url))
                continue
            if got == want:
                print(f"  OK {rel}  served == committed  ({want[:12]})")
            else:
                still.append((rel, path, url))
        pending = still
        if not pending:
            print(f"\nDeployed: all {len(targets)} page(s) serve their committed bytes.")
            return 0
        if time.time() >= deadline:
            print(f"\nTIMED OUT after {args.timeout}s. Still stale:", file=sys.stderr)
            for rel, _, url in pending:
                print(f"  {rel} -> {url}", file=sys.stderr)
            print(
                "\nThis is a real signal, not flakiness: the origin is still returning\n"
                "older bytes than HEAD. Do NOT announce or verify against it yet.",
                file=sys.stderr,
            )
            return 1
        print(f"  .. {len(pending)} still stale, re-checking in {args.interval}s")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
