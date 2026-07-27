#!/usr/bin/env python3
"""Tell search engines deedwell.co exists, and changed.

Why this exists. On 2026-07-27 at 06:07, `site:deedwell.co` returned ZERO results on
the Bing/DuckDuckGo index -- validated against a positive control on the identical
selector and route, which returned 11 rows, so the zero was the index and not the
instrument. The domain was registered 07-23. It has no backlinks and DR 0.0. robots.txt
welcomes every crawler and sitemap.xml is valid, so nothing was blocking a crawler --
nobody had ever TOLD one the site was there, and a brand-new domain with no inbound
links may simply never be discovered.

IndexNow is the one route to fix that which needs no account, no dollar and no
credential: ownership is proven by hosting a key file at the site root, exactly like a
DNS TXT verification record. Verified against the primary source (indexnow.org
/documentation, retrieved 2026-07-27 06:07): key of 8-128 chars from [a-zA-Z0-9-],
hosted at {key}.txt in the root, POST JSON with host/key/urlList, up to 10,000 URLs.
Participating engines, per indexnow.org's own home page the same morning: Microsoft
Bing, Naver, Seznam.cz, Yandex, Yep -- and a URL submitted to one is shared with all.

  NOT GOOGLE. Google does not participate. This buys us Bing and everything downstream
  of it, which includes DuckDuckGo and ChatGPT search. Pulse 4 already measured that
  Google's commercial slots for our category belong entirely to the marketplaces, so
  deedwell.co is not being played as a ranking asset either way -- the job here is to
  EXIST when someone searches the brand name after seeing the book.

THE KEY IS NOT A SECRET. It is served publicly at the site root by design; that public
fetch is how a search engine verifies us. Committing it is required by the protocol and
is not a breach of the no-secrets-in-repos rule, any more than a DNS TXT record is.

The refusal that matters: this script will NOT submit unless it has first fetched the
key file over the public internet and confirmed the bytes. Submitting against a key
file that is not live yet returns 403, which looks like a protocol failure and is
actually a deploy race -- an ambiguous result that costs a session to diagnose. Eyes
before hands, mechanically.

Usage:  python tools/indexnow_submit.py [--dry-run]
"""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "deedwell.co"
SITE = f"https://{HOST}"

# The shared endpoint forwards to every participating engine; Bing is named separately
# because it is the one that matters to us and we would rather see its own status code.
ENDPOINTS = ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]

# Documented response table, indexnow.org/documentation, retrieved 2026-07-27.
MEANING = {
    200: "OK - URL submitted successfully",
    202: "Accepted - received, key validation pending",
    400: "Bad request - invalid format",
    403: "Forbidden - key not valid (not found, or file does not contain the key)",
    422: "Unprocessable - URLs do not belong to the host, or key breaks the schema",
    429: "Too Many Requests - throttled as potential spam",
}

UA = "Mozilla/5.0 (compatible; DeedwellIndexNow/1.0; +https://deedwell.co/)"


def find_key() -> str:
    """The key file is the source of truth for the key. Never type it twice."""
    hits = []
    for p in ROOT.glob("*.txt"):
        stem = p.stem
        if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", stem):
            continue
        if p.read_bytes().decode("utf-8").strip() == stem:
            hits.append(stem)
    if not hits:
        sys.exit("ABORT: no IndexNow key file at the repo root (expected {key}.txt "
                 "whose contents are exactly {key}).")
    if len(hits) > 1:
        sys.exit(f"ABORT: {len(hits)} key files found ({', '.join(hits)}). "
                 "Ambiguous ownership proof -- keep exactly one.")
    return hits[0]


def urls_from_sitemap() -> list:
    """Submit exactly what we advertise. One source of truth, so the two cannot differ."""
    sm = ROOT / "sitemap.xml"
    if not sm.exists():
        sys.exit("ABORT: sitemap.xml not found.")
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm.read_text(encoding="utf-8"))
    if not urls:
        sys.exit("ABORT: sitemap.xml parsed to zero URLs -- refusing to submit nothing.")
    bad = [u for u in urls if not u.startswith(SITE)]
    if bad:
        sys.exit(f"ABORT: sitemap contains URLs outside {HOST}: {bad}")
    return urls


def key_file_is_live(key: str) -> bool:
    """Fetch our own ownership proof over the public internet before claiming it."""
    url = f"{SITE}/{key}.txt"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8").strip()
            code = r.status
    except urllib.error.HTTPError as e:
        print(f"  key file: HTTP {e.code} at {url} -- not deployed yet.")
        return False
    except Exception as e:
        print(f"  key file: unreachable at {url} ({e}).")
        return False

    if code != 200:
        print(f"  key file: HTTP {code} at {url}.")
        return False
    if body != key:
        print(f"  key file: served {body!r}, expected {key!r}.")
        return False
    print(f"  key file: HTTP 200 at {url}, contents match ({len(body)} chars).")
    return True


def submit(endpoint: str, payload: dict) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=data, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        print(f"  {endpoint}: transport error ({e})")
        return -1


def main():
    dry = "--dry-run" in sys.argv
    key = find_key()
    urls = urls_from_sitemap()

    print(f"IndexNow -> {HOST}")
    print(f"  key:  {key}")
    print(f"  urls: {len(urls)}")
    for u in urls:
        print(f"        {u}")

    if dry:
        print("\n--dry-run: nothing submitted.")
        return 0

    print("\nVerifying ownership proof is actually live before submitting:")
    if not key_file_is_live(key):
        print("\nREFUSED: the key file is not serving yet. Deploy first, then re-run.\n"
              "  Submitting now would return 403 and be indistinguishable from a real\n"
              "  protocol failure.")
        return 1

    payload = {"host": HOST, "key": key, "urlList": urls}
    print("\nSubmitting:")
    ok = 0
    for ep in ENDPOINTS:
        code = submit(ep, payload)
        note = MEANING.get(code, "undocumented response")
        print(f"  {ep} -> {code}  {note}")
        if code in (200, 202):
            ok += 1

    if not ok:
        print("\nFAILED: no endpoint accepted the submission.")
        return 1
    print(f"\nAccepted by {ok}/{len(ENDPOINTS)} endpoints.")
    print("NOTE: 200 means received, NOT indexed. Indexing remains the engine's call;\n"
          "      re-measure with a site: query in a few days rather than assuming.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
