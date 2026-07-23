#!/usr/bin/env python
"""Cedarstone site: catch promises the page itself falsifies.

ASCII-only. No dependencies. Exit 0 = clean, exit 1 = a live contradiction.

WHY THIS EXISTS
---------------
On 2026-07-23 06:20 a commit wired real email capture into /checklist/ and shipped.
It did not re-read what those pages already promised. Two public pages kept saying
"nothing to unsubscribe from" - one of them the homepage - for seven hours, on the
single asset whose entire job is to be trusted with an email address. The second
engine caught one instance; a sweep found the other.

The failure was not the sentence. It was that adding a CAPABILITY to a page silently
falsifies COPY elsewhere on that page, and nothing was watching. A rule you read is
not a mechanism, so this is a script and not a paragraph in a note.

WHAT IT CHECKS
--------------
Only pairs that are precisely decidable from the HTML. A noisy checker gets ignored,
which is worse than no checker, so this deliberately refuses to guess:

  1. A page that offers email capture - directly, OR by linking to a page of ours that
     does - must not carry an absolute never-capture promise.
  2. A page that claims "no form" must not contain a form control.

Rule 1 follows one hop of local links on purpose. The first draft of this script only
looked at the page's own markup, and it reproduced the exact blind spot it was written
to close: it caught /checklist/ (which hosts the capture link) and cleared the homepage
(which only points at it) - the very instance the human sweep had to find by hand. A
promise about email is broken by where the button GOES, not by where it sits.

Add a rule only when both halves are mechanically detectable.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- rule 1: capture offered vs. absolute never-capture promise --------------
CAPTURE_MARKERS = [
    r"gumroad\.com/subscribe",
    r"gumroad\.com/follow",
    r"<form[^>]*\bsubscribe\b",
    r"type=[\"']email[\"']",
]
NEVER_CAPTURE_PHRASES = [
    r"nothing to unsubscribe from",
    r"we (?:will )?never email you",
    r"there is no list",
    r"we don'?t collect (?:any )?emails",
    r"no email is (?:ever )?collected",
]

# --- rule 2: "no form" claim vs. an actual form control ----------------------
NO_FORM_PHRASES = [
    r"no form to fill in",
    r"\bno form\b",
]
FORM_CONTROLS = [r"<form\b", r"<input\b", r"<textarea\b", r"<select\b"]


def find(patterns, text):
    """Return (pattern, 1-indexed line) for the first match of any pattern."""
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return p, text[: m.start()].count("\n") + 1
    return None, None


def local_links(text):
    """Local href targets on the page, normalised to a repo-relative html file."""
    out = []
    for href in re.findall(r'href=["\']([^"\'#?]+)', text, re.I):
        if re.match(r"^(?:[a-z]+:|//|#)", href, re.I):
            continue
        p = href.strip().lstrip("/")
        if p.endswith("/") or p == "":
            p = p + "index.html"
        elif not p.lower().endswith(".html"):
            continue
        out.append(p)
    return out


def check_file(path, text, capture_pages=None):
    problems = []
    capture_pages = capture_pages or {}

    cap, cap_line = find(CAPTURE_MARKERS, text)
    via = None
    if not cap:
        # one hop: a promise about email is broken by where the button GOES.
        for target in local_links(text):
            if target in capture_pages:
                cap, cap_line, via = capture_pages[target], 0, target
                break
    if cap:
        bad, bad_line = find(NEVER_CAPTURE_PHRASES, text)
        if bad:
            where = (
                "/%s/ at line %d" % (cap, cap_line)
                if via is None
                else "reached in one click via %s, which offers capture (/%s/)" % (via, cap)
            )
            problems.append(
                "%s:%d absolute never-capture promise /%s/ on a page that offers "
                "email capture (%s)" % (path, bad_line, bad, where)
            )

    claim, claim_line = find(NO_FORM_PHRASES, text)
    if claim:
        ctl, ctl_line = find(FORM_CONTROLS, text)
        if ctl:
            problems.append(
                "%s:%d claims /%s/ but the page contains a form control "
                "(/%s/ at line %d)" % (path, claim_line, claim, ctl, ctl_line)
            )

    return problems


def main():
    targets = sys.argv[1:]
    if not targets:
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "tools", "node_modules")]
            for f in files:
                if f.lower().endswith(".html"):
                    targets.append(os.path.join(base, f))

    def label(path):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        return path.replace("\\", "/") if rel.startswith("..") else rel

    texts = {}
    for path in sorted(targets):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            texts[path] = fh.read()

    # which of our pages actually offer capture, keyed the way local hrefs resolve
    capture_pages = {}
    for path, text in texts.items():
        cap, _ = find(CAPTURE_MARKERS, text)
        if cap:
            # keyed ONLY by repo-relative path. An earlier draft also keyed by
            # basename, which made every link to "/" resolve to some subdirectory's
            # index.html and look like capture - a false positive waiting to happen,
            # and here it produced a right answer with a wrong reason.
            capture_pages[label(path)] = cap

    problems = []
    for path in sorted(targets):
        problems.extend(check_file(label(path), texts[path], capture_pages))

    print("checked %d html file(s)" % len(targets))
    if problems:
        print("")
        print("PROMISE CONTRADICTIONS (%d):" % len(problems))
        for p in problems:
            print("  " + p)
        print("")
        print("A public page is making a promise the same page falsifies. Fix the copy.")
        return 1
    print("no promise contradictions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
