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
  3. A block describing the un-inspectable paperback flagship (B0GV9WSVCC) must sell
     the JOB the book does, not enumerate the interior SECTIONS its pages contain
     (EXP-013, 2026-07-23: the live 118pp interior is a build we do not own and cannot
     inspect). This exact claim rode live twice - checklist 00:05, home 02:05 - before
     a human caught it, and unverified-claim is a repeating mistake, so it gets a
     mechanism. It fires ONLY inside a paperback block that is not a spreadsheet block,
     to stay precise against the shared income/expenses/mileage vocabulary that is
     legitimate (and machine-verified) when predicated of the spreadsheets. Run
     `check_promises.py --selftest` to prove it still catches both incidents.

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

# --- rule 3: interior-contents claims about the un-inspectable flagship -------
# The trap is a SHARED vocabulary: "income", "expenses", "mileage" are legitimate
# when predicated of the SPREADSHEET (tabs/formulas, machine-verified by verify_pack)
# and forbidden when predicated of the PAPERBACK (118pp, un-inspectable). So the rule
# fires only inside a block that (a) refers to the printed object and (b) is NOT a
# spreadsheet block, and that either uses an unmistakable paperback-page phrase or
# enumerates >=3 distinct interior sections. Precision over recall, per this file.
PAPER_REFERENTS = [
    r"B0GV9WSVCC",
    r"\bpaperback\b",
    r"\bprinted (?:log ?book|logbook|journal|tracker|operations tracker|companion)\b",
    r"\bpaper (?:companion|log ?book)\b",
    r"\b\d{2,4}-page\b",
]
# markers that appear ONLY in real spreadsheet-product blocks. Deliberately NOT the
# bare word "spreadsheet" - the paperback's own copy says "never open a spreadsheet",
# so using it as an excluder would blind the rule to that very block.
SPREADSHEET_MARKERS = [
    r"\btabs?\b", r"\bformulas?\b", r"\bworkbook\b", r"\bworksheet\b",
    r"\.xlsx\b", r"gumroad", r"google sheets", r"\bexcel\b",
]
# "the printed pages contain X" phrasings - forbidden on sight inside a paper block
INTERIOR_PAGE_PHRASES = [
    r"pre-?headed pages",
    r"pre-?printed pages",
    r"pre-?labell?ed pages",
    r"ready-to-fill pages",
    r"fill-in pages",
    r"pages (?:for|to (?:record|log|track)) ",
    r"sections? for (?:bookings?|income|expenses|cleaning|cleaner|maintenance|mileage|guests?|checkouts?|turnovers?)",
]
# the flagship's interior-section vocabulary (closed list). Each entry is one
# category; enumerating >=3 of them as the printed object's contents is a claim.
SECTION_TERMS = [
    r"\bbookings?\b",
    r"\bincome\b",
    r"\bexpenses?\b",
    r"\bmileage\b",
    r"\bcleaning\b|\bcleaner schedules?\b",
    r"\bmaintenance\b",
    r"\brepairs?\b",
    r"\bsupplies\b",
    r"\bguests?\b",
    r"\b(?:check-?outs?|turnovers?|check-?ins?)\b",
    r"\bhour logs?\b",
    r"\boccupancy\b",
]

# inline tags whose text belongs to the surrounding block; block-level tags delimit.
INLINE_TAGS = r"(?i)</?(?:b|i|em|strong|span|a|small|sup|sub|u|mark|abbr|wbr)\b[^>]*>"


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


def blocks_of(text):
    """Yield the plain-text content of each block-level element.

    Inline tags (<b>, <a>, ...) are dissolved into their surrounding text so a
    referent and its enumeration are not split apart; block tags delimit. This
    keeps "the <b>Host Log Book</b> is a 118-page paperback" as ONE block while
    keeping a Gumroad card's <p> separate from a paperback card's <p>.
    """
    t = re.sub(INLINE_TAGS, " ", text)
    for seg in re.split(r"<[^>]+>", t):
        seg = re.sub(r"\s+", " ", seg).strip()
        if seg:
            yield seg


def interior_claims(path, text):
    """Rule 3: no interior-section claim about the un-inspectable paperback (EXP-013)."""
    problems = []
    for seg in blocks_of(text):
        ref, _ = find(PAPER_REFERENTS, seg)
        if not ref:
            continue  # not a block about the printed object
        if find(SPREADSHEET_MARKERS, seg)[0]:
            continue  # a spreadsheet block; its enumeration is machine-verified
        phrase, _ = find(INTERIOR_PAGE_PHRASES, seg)
        hits = [p for p in SECTION_TERMS if re.search(p, seg, re.I)]
        if not (phrase or len(hits) >= 3):
            continue
        trigpat = phrase or next(p for p in SECTION_TERMS if re.search(p, seg, re.I))
        m = re.search(trigpat, text, re.I)
        line = text[: m.start()].count("\n") + 1 if m else 0
        shown = (m.group(0) if m else trigpat) if phrase else ", ".join(
            re.search(p, seg, re.I).group(0) for p in SECTION_TERMS if re.search(p, seg, re.I)
        )
        problems.append(
            "%s:%d interior-contents claim about the un-inspectable flagship "
            "B0GV9WSVCC (EXP-013): a paperback block enumerates [%s]. Sell the JOB "
            "the book does, not the sections its pages contain." % (path, line, shown)
        )
    return problems


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

    problems.extend(interior_claims(path, text))

    return problems


# positive control for rule 3: the two claims that rode live, plus the safe copy
# they were reduced to. Proves the mechanism catches the incident, not just names it.
SELFTEST = [
    ("00:05 checklist draft", True,
     '<p>The paperback has pre-headed pages for bookings, income, expenses and mileage.</p>'),
    ("02:05 home tool card", True,
     '<div class="tool"><h3>Airbnb Host Log Book</h3><p>Bookings, income and expenses, '
     'cleaner schedules, maintenance, and tax-ready hour logs in one printed operations '
     'tracker.</p></div>'),
    ("live tool card (job, not contents)", False,
     '<div class="tool"><h3>Airbnb Host Log Book</h3><p>The paper companion, for the host '
     'who will never open a spreadsheet: a printed log book to get the numbers written '
     'down on the day they happen.</p></div>'),
    ("live prefer-paper block", False,
     '<p>The <b>Airbnb Host Log Book</b> is a 118-page, 8.5 x 11 paperback you keep at the '
     'property and write in as the year happens. It does no arithmetic.</p>'),
    ("gumroad spreadsheet enumeration", False,
     '<div class="tool"><h3>STR Tax Bundle</h3><p>Income and expense tracking, a mileage '
     'log, 1099-K reconciliation, and a Schedule E that fills itself.</p>'
     '<div class="st"><a href="https://cedarstone5.gumroad.com/l/x">Gumroad</a></div></div>'),
]


def selftest():
    ok = True
    for name, should_flag, html in SELFTEST:
        flagged = bool(interior_claims("selftest", html))
        status = "PASS" if flagged == should_flag else "FAIL"
        if flagged != should_flag:
            ok = False
        print("  [%s] %s (expected %s, got %s)"
              % (status, name, "flag" if should_flag else "clean",
                 "flag" if flagged else "clean"))
    print("selftest: %s" % ("all cases correct" if ok else "MISMATCH"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv[1:]:
        return selftest()
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
