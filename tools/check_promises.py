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
  4. The IRS document credited NEAREST a 2026 mileage rate must be the document that
     actually sets that rate. 2026 is a split-rate year with two different sources.

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

# --- rule 4: which IRS document is credited for which 2026 mileage rate -------
# 2026 is a split-rate year and the two halves have DIFFERENT sources: Notice 2026-10
# sets 72.5c from Jan 1, and Announcement 2026-11 raises it to 76c from Jul 1.
#
# On 2026-07-26 /rental/ printed both rates side by side and closed the block with
# "Source: IRS Announcement 2026-11" - one document credited for two rates, on the
# single figure the page exists to be trusted about, on the landing page a printed QR
# code points at. The same page's FAQ schema and body copy named BOTH documents
# correctly, so a page-level "does it mention both?" test passes and catches nothing.
# The book had the identical defect on p7 the same morning; fixing one surface did not
# fix the other, and unverified-claim is a repeating mistake, so it gets a mechanism.
#
# The rule is SENTENCE BINDING: a sentence that names exactly one of the two documents
# and quotes a rate that document does not set has mis-attributed it. That is decidable
# with no guessing, and it is the shape all three of the morning's instances took.
#
# The first draft of this rule used proximity instead - "the nearest citation to a rate
# must be that rate's source" - and it fired twice on already-correct prose, because a
# sentence like "the 72.5c rate is from Notice 2026-10; the increase to 76c was made in
# Announcement 2026-11" puts the wrong document nearer the second figure while being
# perfectly clear to a reader. A noisy checker gets ignored, so proximity was dropped.
#
# WHAT THIS DOES NOT COVER, stated plainly because the 06:14 lesson was a gate that
# claimed more than it checked:
#   - An attribution physically separated from its figure ("Source: X" under a two-
#     column rate block) is invisible to a sentence rule. On /rental/ that is now
#     handled structurally instead - each citation sits inside the same card as its
#     own rate - which is a better fix than a checker anyway.
#   - This script only walks this repo's HTML. The same defect shipped the same
#     morning in kdp-stack (the printed book, deedwell_rental_records.py) and in the
#     brain (the Amazon listing copy). Those surfaces have NO mechanism yet.
#
# 11:0x, AND THE FIRST BULLET IS WHY: the lead-magnet PDF served out of files/ - the
# download offered on BOTH /checklist/ and /rental/, and the destination of the QR
# code printed permanently inside the book - still read "IRS Announcement 2026-11."
# for BOTH halves, four hours after the same defect was fixed everywhere else. Its
# generator (kdp-stack/build/deedwell_lead_magnet.py) had already been corrected; the
# artifact was simply never rebuilt and re-copied. Source fixed, artifact stale.
#
# Measured, not assumed: rule 4 could not have caught it even if it walked PDFs. In
# print the citation stands as its own sentence - sentences() carves out exactly
# "[IRS Announcement 2026-11.]", which contains no rate, so the sentence rule cannot
# fire. That is the FIRST bullet's blind spot again, in a second form. Print callouts
# are visual units, not grammatical ones, so served PDFs get a PAGE-scoped rule below.
# HTML and served PDFs are now both covered; kdp-stack's own build sources and the
# brain's listing copy still are not.
RATE_SOURCES = [
    (r"72\.5\s*(?:\u00a2|cents?\b)", "72.5c (Jan 1 - Jun 30)", "IRS Notice 2026-10"),
    (r"\b76\s*(?:\u00a2|cents?\b)", "76c (Jul 1 - Dec 31)", "IRS Announcement 2026-11"),
]
CITE_NOTICE = r"Notice\s*2026-10"
CITE_ANNOUNCE = r"(?:Announcement|Ann\.)\s*2026-11"  # our own printed copy abbreviates
# ";" ends a clause on purpose: our own correct copy pairs the two rates across a
# semicolon, and reading that as one sentence would score it as "names both".
SENTENCE_END = r"[.;!?]\s"

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


def flatten(text):
    """Markup-free text the SAME LENGTH as the original, so offsets still map to lines.

    Inline tags and entities become spaces; block tags become spaces ending in a period,
    because a paragraph break IS a sentence break. Length preservation is the point:
    an earlier draft rebuilt the string and had to guess at line numbers.
    """
    def blank(m):
        return " " * len(m.group(0))

    def stop(m):
        return " " * (len(m.group(0)) - 1) + "."

    t = re.sub(INLINE_TAGS, blank, text)
    t = re.sub(r"&cent;", " cents", t)          # same length, keeps the figure readable
    t = re.sub(r"&[a-z]+;|&#\d+;", blank, t, flags=re.I)
    t = re.sub(r"<[^>]+>", stop, t)
    return t


def sentences(flat):
    """(offset, text) for each sentence, offsets into the flattened == original text."""
    out, start = [], 0
    for m in re.finditer(SENTENCE_END, flat):
        out.append((start, flat[start:m.end()]))
        start = m.end()
    out.append((start, flat[start:]))
    return out


def mileage_sources(path, text):
    """Rule 4: a sentence citing ONE IRS document must not quote the other's rate."""
    problems = []
    flat = flatten(text)
    for start, sentence in sentences(flat):
        has_notice = re.search(CITE_NOTICE, sentence, re.I)
        has_announce = re.search(CITE_ANNOUNCE, sentence, re.I)
        if bool(has_notice) == bool(has_announce):
            continue  # names both documents, or neither - nothing to mis-attribute
        cited = "IRS Notice 2026-10" if has_notice else "IRS Announcement 2026-11"
        for rate_pat, rate_label, sets_it in RATE_SOURCES:
            if sets_it == cited:
                continue  # this document does set this rate
            m = re.search(rate_pat, sentence, re.I)
            if m:
                line = flat[: start + m.start()].count("\n") + 1
                problems.append(
                    "%s:%d cites %s beside the %s mileage rate, which it does not set "
                    "- that rate is set by %s. 2026 is a split-rate year and the two "
                    "halves have different sources; a reader sent to the wrong document "
                    "will not find the number."
                    % (path, line, cited, rate_label, sets_it)
                )
    return problems


def mileage_sources_page(path, page_text, page_no):
    """Rule 4, PAGE-scoped, for print artifacts we serve.

    A printed callout is a visual unit: the reader sees the rate and the line of
    small type under it as one thing, whatever the sentence boundaries are. So the
    unit here is the page - if a page quotes a rate and names exactly ONE of the two
    documents anywhere on it, that document had better be the one that sets the rate.

    Deliberately conservative in the same direction rule 4 already chose when its
    proximity draft was dropped for noise: naming BOTH documents anywhere on the page
    clears the page. LIMIT, stated rather than glossed - a page that cites both but
    pairs one with the wrong rate passes this check. Catching that needs layout
    geometry, not text. What it does catch is the whole-artifact miss that actually
    shipped: one document credited for a split year.
    """
    flat = " ".join(page_text.split())
    has_notice = re.search(CITE_NOTICE, flat, re.I)
    has_announce = re.search(CITE_ANNOUNCE, flat, re.I)
    if bool(has_notice) == bool(has_announce):
        return []
    cited = "IRS Notice 2026-10" if has_notice else "IRS Announcement 2026-11"
    problems = []
    for rate_pat, rate_label, sets_it in RATE_SOURCES:
        if sets_it == cited:
            continue
        if re.search(rate_pat, flat, re.I):
            problems.append(
                "%s page %d quotes the %s mileage rate but the only IRS document "
                "named on that page is %s, which does not set it - that rate is set "
                "by %s. A reader sent to the wrong document will not find the number."
                % (path, page_no, rate_label, cited, sets_it)
            )
    return problems


def pdf_pages(path):
    """Per-page text of a served PDF.

    Import failure is a HARD error, never a skip. A checker that cannot read its
    target must not report green - that is precisely how the 08:07 sentry ended up
    matching a regex against a byte[] and checking nothing at all.
    """
    try:
        from pypdf import PdfReader
    except ImportError:          # pragma: no cover - environment, not logic
        raise SystemExit(
            "check_promises: pypdf is required to read served PDFs (pip install pypdf). "
            "Refusing to pass without checking them."
        )
    return [(p.extract_text() or "") for p in PdfReader(path).pages]


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
    problems.extend(mileage_sources(path, text))

    return problems


# positive control for rule 4. The two flagging fixtures are the real sentences that
# shipped on 2026-07-26 - one from the printed book's p7, one from the Amazon listing
# description - and the clean ones are our current correct copy, including the two
# already-right prose constructions that an earlier proximity draft of this rule
# falsely flagged. A rule that fires on correct copy gets switched off, so those two
# stay here permanently as regression guards.
RATE_SELFTEST = [
    ("book p7 as it shipped: one document for both halves", True,
     '<p>2026 is a rare split year: 72.5 cents a mile from January 1 to June 30, then '
     '76 cents from July 1 to December 31 (IRS Announcement 2026-11).</p>'),
    ("Amazon listing description as it shipped", True,
     "<p>A mileage log built for 2026's split rate (72.5 cents through June, 76 cents "
     "from July, per IRS Announcement 2026-11).</p>"),
    ("current book footer: each half to its own document", False,
     '<p>2026: 72.5 cents/mile to Jun 30 (Notice 2026-10); 76 cents from Jul 1 '
     '(Ann. 2026-11). Standard rate OR actual, not both.</p>'),
    ("current body copy: one sentence naming both documents", False,
     '<p>72.5 cents per mile for trips from 1 January through 30 June 2026 (IRS '
     'Notice&nbsp;2026-10), and 76 cents per mile from 1 July through 31 December '
     '2026 (IRS Announcement&nbsp;2026-11, Internal Revenue Bulletin 2026-29).</p>'),
    ("current FAQ schema: two clauses across a semicolon", False,
     'The business standard mileage rate is 72.5 cents per mile for trips from '
     'January 1 through June 30, 2026, and 76 cents per mile from July 1 through '
     'December 31, 2026. The 72.5 cent rate is from IRS Notice 2026-10; the mid-year '
     'increase to 76 cents was made in IRS Announcement 2026-11.'),
    ("current rate cards: each citation inside its own card", False,
     '<div class="half"><p class="val">72.5&cent; per mile</p>'
     '<p class="cite">Set by IRS Notice 2026-10</p></div>'
     '<div class="half"><p class="val">76&cent; per mile</p>'
     '<p class="cite">Raised by IRS Announcement 2026-11, 13 July 2026</p></div>'),
]


# positive control for the PAGE-scoped rule. The flagging fixture is the REAL page-1
# callout of the lead magnet as it was served on deedwell.co, extracted from the
# shipped PDF - not a paraphrase. The clean fixture is the same callout after the
# rebuild. Both keep the standalone citation sentence that defeats the sentence rule,
# because that structure IS the thing under test.
PDF_SELFTEST = [
    ("lead magnet p1 as served: one document for a split year", True,
     "2026 changed the mileage rate halfway through the year. "
     "72.5 cents a mile from 1 January to 30 June, then 76 cents from 1 July. "
     "IRS Announcement 2026-11. Total each half of the year separately."),
    ("lead magnet p1 rebuilt: each half to its own document", False,
     "2026 changed the mileage rate halfway through the year. "
     "72.5 cents a mile from 1 January to 30 June, then 76 cents from 1 July. "
     "IRS Notice 2026-10, revised by Announcement 2026-11. Total each half separately."),
    ("a page with no rate on it at all", False,
     "Schedule E line numbers per the current IRS instructions. Not tax advice."),
]

# The reason the page rule had to exist, kept executable so it cannot be forgotten:
# the sentence rule is PROVED blind to the fixture above. If a future change ever
# makes mileage_sources catch it, this assertion fails loudly and the page rule can
# be reconsidered - rather than two rules quietly overlapping forever.
SENTENCE_RULE_IS_BLIND_TO = PDF_SELFTEST[0][2]


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
    cases = ([(n, f, h, interior_claims) for n, f, h in SELFTEST]
             + [(n, f, h, mileage_sources) for n, f, h in RATE_SELFTEST]
             + [(n, f, h, lambda p, t: mileage_sources_page(p, t, 1))
                for n, f, h in PDF_SELFTEST])
    for name, should_flag, html, rule in cases:
        flagged = bool(rule("selftest", html))
        status = "PASS" if flagged == should_flag else "FAIL"
        if flagged != should_flag:
            ok = False
        print("  [%s] %s (expected %s, got %s)"
              % (status, name, "flag" if should_flag else "clean",
                 "flag" if flagged else "clean"))

    # why the page rule exists, asserted rather than described
    blind = not mileage_sources("selftest", SENTENCE_RULE_IS_BLIND_TO)
    print("  [%s] sentence rule is blind to the shipped PDF callout "
          "(this is why the page rule exists)" % ("PASS" if blind else "FAIL"))
    if not blind:
        ok = False

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

    # Served PDFs are public copy too. files/ is what deedwell.co actually hands the
    # reader - and the QR printed inside the book points at a page offering it.
    pdfs = []
    for base, dirs, files in os.walk(os.path.join(ROOT, "files")):
        for f in sorted(files):
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(base, f))
    for path in sorted(pdfs):
        for i, page_text in enumerate(pdf_pages(path)):
            problems.extend(mileage_sources_page(label(path), page_text, i + 1))

    print("checked %d html file(s) and %d served pdf(s)" % (len(targets), len(pdfs)))
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
