#!/usr/bin/env python
"""Cedarstone site: catch promises the page itself falsifies.

ASCII-only SOURCE. Exit 0 = clean, exit 1 = a live contradiction.

DEPENDENCIES: the standard library, EXCEPT that reading served PDFs needs `pypdf`
(pip install pypdf). This header said "No dependencies" for six hours after the live
PDF path landed, which is the same defect class this file exists to catch - a claim
the artifact falsifies. pdf_pages() raises rather than skipping, so a missing pypdf
fails the run loudly instead of reporting green on unchecked files.

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
  4. A SENTENCE that names exactly one of the two 2026 mileage documents must not
     quote the rate the other one sets. 2026 is a split-rate year with two different
     sources. (Proximity - "the document credited NEAREST the rate" - was tried first
     and dropped for noise; see the rule 4 block. Served PDFs get a PAGE-scoped
     variant, because a print callout is a visual unit and not a grammatical one.)
  5. An unsubscribe / auto-delivery promise must not be made while no sending platform
     is wired anywhere in the repo. Auto-relaxes the hour an ESP exists.
  6. Every page-count claim on every page - prose, stat tile, or the JSON-LD Book node -
     must equal BOOK_PAGES, the one place the shipped book's length is typed. This is a
     SWEEP and not a reminder for a reason: see the rule 6 block.
  8. A page denying analytics or third-party scripts must not itself load an off-domain
     <script src>. Bought the morning analytics shipped to six pages while privacy.html
     kept inviting readers to "check: this site loads no third-party scripts at all".
     (Rule 7 - a COMMENT denying a capability the repo has - arrives with the homepage
     capture branch; the numbering is deliberate so the two merge without collision.)

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

# --- rule 5: a delivery promise with no delivery mechanism -------------------
# 2026-07-26. /updates/ promised "every email carries an unsubscribe link" and
# "Unsubscribe anytime" while there is no sending platform at all: registration is a
# mailto: into an ordinary Zoho mailbox, so a hand-written reply cannot carry a link.
# Same class as the registration form that silently dropped every paying customer on
# 07-22 - a capability asserted to buyers with nothing behind it.
#
# Both halves are mechanically detectable, which is this file's bar for a rule:
#   the claim      -> affirmative unsubscribe/auto-delivery phrasing, below
#   the capability -> a sending platform WIRED anywhere in the repo (ESP_WIRING)
# It AUTO-RELAXES: the hour an ESP is actually wired, ESP_WIRING matches and these
# promises become legal to make. So the rule encodes the open blocker rather than
# banning the words forever. The run prints WHERE it relaxed, so a rule that has
# quietly switched itself off is visible in one line of output.
#
# LIMIT, stated rather than implied: it distinguishes "some sending platform exists"
# from "none at all". It cannot tell whether a configured ESP is wired correctly, and
# a broken-but-present ESP passes. That is a weaker check than it looks, deliberately -
# the incident it exists for is the total absence, which is unambiguous.
#
# 2026-07-27, AND THIS LIMIT IS NOW LIVE RATHER THAN THEORETICAL: Gumroad is wired, so
# this rule has relaxed and unsubscribe promises are no longer blocked. But nobody has
# yet confirmed that a Gumroad CREATOR BROADCAST actually carries an unsubscribe link -
# help.gumroad.com is login-gated, and gumroad.com/privacy only covers Gumroad's own
# marketing mail. So the guard that would have caught exactly that claim is now off,
# while the fact behind the claim is still unverified. Today's copy does not make the
# promise (privacy.html says outright that we will not describe a footer we have not
# sent). If a future session wants to promise it, VERIFY IT IN A REAL SENT EMAIL first;
# this rule will no longer stop you.
# The verb list is not decoration. The first draft matched only "carries an unsubscribe
# link" - the exact string that happened to ship - so "every email INCLUDES an
# unsubscribe link" would have re-shipped the identical false promise past a green
# check. A rule that only catches the wording of the last incident is a rule that
# catches the last incident.
SENDING_PROMISES = [
    r"(?:carr(?:ies|y)|includes?|has|have|contains?|comes? with) an unsubscribe link",
    r"unsubscribe in one click",
    r"one[- ]click unsubscribe",
    r"click the unsubscribe link",
    r"unsubscribe (?:anytime|any time|at any time|whenever you (?:want|like)|at will)",
    r"opt out (?:anytime|any time|at any time|whenever you (?:want|like))",
    r"check your inbox",
    r"arrives? in your inbox",
    r"(?:sent?|sends|deliver(?:s|ed)?|email(?:ed)?)[^.;!?]{0,40}?\bto your inbox\b",
]
# An affirmative pattern preceded by a negator is our own honest disclosure, not a
# promise: "there is NO unsubscribe link, because there is no marketing platform".
#
# The negator must be in the SAME CLAUSE. A plain proximity window would have excused
# the real incident: the dead generator's "No spam - unsubscribe in one click" puts a
# negator ten characters before the claim, but it negates *spam*, not the unsubscribe.
# So the lookback is cut at the nearest clause break first. Caught by writing the
# selftest fixture before trusting the rule.
PROMISE_NEGATORS = r"(?:\bno\b|\bnot\b|\bnever\b|\bwithout\b|\bcannot\b|\bcan'?t\b)"
# escaped, not literal: this file declares itself ASCII-only and a literal em/en dash
# here broke that in the same commit that added the rule.
CLAUSE_BREAK = (r"(?:&mdash;|&ndash;|[.;:," + chr(0x2014) + chr(0x2013)
                + r"]|\s[-]\s)")


# A promise REPORTED is not a promise MADE. "that page also said every email would
# carry an unsubscribe link, which was never possible" is this site telling the truth
# about its own past copy, and a rule that fires on it is a rule somebody switches off -
# the same trap comment-blanking closed at 13:13, met again in visible prose.
#
# Found by running against the real pages, not the fixtures: widening the verb list to
# close Codex's "includes/has" gap immediately fired on privacy.html's own post-mortem.
# The narrow fix would have been to drop the infinitive forms, but that loses the real
# promise "every email WILL CARRY an unsubscribe link". So the vocabulary stays wide
# and the frame is what decides: reported speech in the same clause excuses the claim.
REPORTING_VERBS = (r"(?:\bsaid\b|\bsays\b|\btold\b|\bpromised\b|\bclaimed\b|\bstated\b|"
                   r"\bassured\b|\bused to (?:say|read)\b|\bstood here\b|\buntil \d{4})")


def _clause_before(before):
    """The clause the claim actually sits in - a lookback cut at the nearest break."""
    return re.split(CLAUSE_BREAK, before)[-1]


def _negated(before):
    """True when a negator governs the claim - same clause, not merely nearby."""
    return bool(re.search(PROMISE_NEGATORS, _clause_before(before), re.I))


def _reported(before):
    """True when the claim is quoted as something once said, not asserted now."""
    return bool(re.search(REPORTING_VERBS, _clause_before(before), re.I))
# WIRING, NOT MENTION. The first draft matched a bare vendor name anywhere in any
# scanned file, which put the OFF SWITCH FOR THE WHOLE RULE inside our own prose: this
# site's voice is to say plainly what we do not run, so one honest sentence - "we do
# not use MailerLite or Mailchimp" - or one `<!-- evaluate Buttondown later -->` would
# have silently disabled rule 5 site-wide, on every page, permanently and invisibly.
# It also counted ANY external form action, so a search box pointing at DuckDuckGo
# would have done the same. Not live when found (measured: `sending platform: NONE`),
# but a guard whose off switch sits in the copy it guards is not a guard.
#
# So a vendor counts only where a MACHINE acts on it - a form action, a script or
# iframe src, a hosted-page link, or a config key - never in body text.
_ESP_VENDOR = (r"(?:mailerlite|convertkit|buttondown|formspree|mailchimp|list-manage|"
               r"sendgrid|klaviyo|substack|listmonk|beehiiv|emailoctopus|kit\.com)")
ESP_WIRING = [
    r"data-netlify\s*=\s*[\"']?true",                      # a form Netlify processes
    r"<form[^>]*\bnetlify\b",
    r"<form[^>]+action\s*=\s*[\"'][^\"']*" + _ESP_VENDOR,  # posts to the vendor
    r"<(?:script|iframe)[^>]+src\s*=\s*[\"'][^\"']*" + _ESP_VENDOR,   # embedded widget
    r"href\s*=\s*[\"']https?://[^\"']*" + _ESP_VENDOR,     # hosted signup page
    _ESP_VENDOR + r"[^\n]{0,40}?(?:api[_-]?key|endpoint|_url\b|token)",   # config, not
    r"(?:api[_-]?key|endpoint|token)[^\n]{0,40}?" + _ESP_VENDOR,         # prose
    # 2026-07-27: Gumroad became our sending platform (hosted signup at
    # /subscribe, broadcasts from the dashboard). It is deliberately NOT in
    # _ESP_VENDOR, and that is the whole point of this entry: we link to Gumroad
    # for CHECKOUT on three pages, and a store link is not a sending platform.
    # A bare vendor here would let href=".../l/<product>" flip the rule off, which
    # is the same off-switch-in-our-own-content defect the comment above describes,
    # just moved from prose into markup. Only the subscribe endpoint is a capability.
    r"href\s*=\s*[\"']https?://[^\"']*gumroad\.com/(?:subscribe|follow)\b",
]


def _external_form_capture(text):
    """A form that POSTs an email address off-site is a sending platform by any name.

    Scoped to the form element, which is the whole point: an external `action` alone
    proves nothing (a site search box has one), and an email input alone proves nothing
    (rule 1 already handles local capture). Together, inside one form, they are a real
    hosted capture endpoint even from a vendor this file has never heard of.

    LIMIT: an unclosed <form> is not matched.
    """
    for m in re.finditer(r"<form\b[^>]*>.*?</form>", text, re.S | re.I):
        block = m.group(0)
        if (re.search(r"action\s*=\s*[\"']https?://", block, re.I)
                and re.search(r"type\s*=\s*[\"']?email", block, re.I)):
            return True
    return False


def _published_copy(text):
    """Blank out HTML comments and <style> blocks, preserving offsets so lines stay true.

    Rule 5 is about promises made to a READER, and neither a comment nor a stylesheet
    makes one. The comment half is not a loophole - it is here because the first real
    run flagged updates/index.html's own post-mortem, which quotes the dead 2026-07-22
    copy verbatim ("Check your inbox for a confirmation") to warn the next author off
    reinstating it. A check that fires on the incident report is a check somebody
    switches off.

    NAMED PRECISELY, because the previous claim - "rule 5 reads visible copy only" -
    was overstated and Codex was right to file it. What is still scanned: meta tags,
    <title>, JSON-LD inside <script>, and attribute values. That is DELIBERATE, not an
    oversight: a meta description and an FAQ schema are published copy that Google and
    the AI engines quote back to a reader, so an unsubscribe promise made there is made
    to a reader just the same. What is not scanned: comments and CSS.
    """
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    return re.sub(r"<style\b[^>]*>.*?</style>", blank, text, flags=re.S | re.I)


def sending_promises(path, text, esp_present=False):
    """Flag an unsubscribe / auto-delivery promise when nothing can send mail."""
    if esp_present:
        return []
    problems = []
    text = _published_copy(text)
    for pat in SENDING_PROMISES:
        for m in re.finditer(pat, text, re.I):
            before = text[max(0, m.start() - 90):m.start()]
            if _negated(before):
                continue  # our own disclosure that the mechanism does not exist
            if _reported(before):
                continue  # our own post-mortem quoting copy we withdrew
            line = text.count("\n", 0, m.start()) + 1
            problems.append(
                "%s:%d promises /%s/ but no sending platform exists anywhere in the "
                "repo, so nothing can deliver it" % (path, line, m.group(0)))
    return problems


def esp_configured(root):
    """True if a sending platform is actually WIRED anywhere in the served site.

    Returns (bool, where) so the run can print WHICH file relaxed the rule. Silent
    relaxation is how a disabled guard stays disabled: `sending platform: present` with
    no location is unfalsifiable at a glance.
    """
    for base, dirs, files in sorted(os.walk(root)):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "tools")]
        for name in sorted(files):
            if not name.endswith((".html", ".js", ".toml", ".yml", ".yaml")):
                continue
            full = os.path.join(base, name)
            try:
                body = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            body = _published_copy(body)   # a commented-out vendor is not a platform
            pat, line = find(ESP_WIRING, body)
            if pat:
                return True, "%s:%d" % (os.path.relpath(full, root), line)
            if name.endswith(".html") and _external_form_capture(body):
                return True, "%s (external form posting an email field)" % (
                    os.path.relpath(full, root))
    return False, None


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
# The shorthand forms are NOT optional extras: the commit that introduced this rule
# wrote "72.5c/76c" in its own message while the rule could not match it, so the rule
# was blind to the way we ourselves abbreviate. `c\b` needs the word boundary - it
# matches "76c" and "76 c" but not "76 cm" or "76 copies". "cents?" is tried first so
# the longer form still reports the longer match.
_C = r"(?:\u00a2|cents?\b|c\b)"
RATE_SOURCES = [
    (r"72\.5\s*" + _C, "72.5c (Jan 1 - Jun 30)", "IRS Notice 2026-10"),
    (r"\b76\s*" + _C, "76c (Jul 1 - Dec 31)", "IRS Announcement 2026-11"),
]
CITE_NOTICE = r"Notice\s*2026-10"
CITE_ANNOUNCE = r"(?:Announcement|Ann\.)\s*2026-11"  # our own printed copy abbreviates
# ";" ends a clause on purpose: our own correct copy pairs the two rates across a
# semicolon, and reading that as one sentence would score it as "names both".
#
# A "." only ends a sentence when what follows is NOT lowercase-or-digit. Without that,
# "Ann. 2026-11" split at the abbreviation and left "2026-11" stranded in the next
# fragment, so CITE_ANNOUNCE could never match the abbreviated form the rule claimed to
# support - and the selftest fixture using "Ann. 2026-11" was passing for the wrong
# reason. The same guard covers "I.R.B. 2026-29", "Rev. Proc.", "Jun. 30".
# LIMIT: a genuine sentence that begins with a digit ("...in July. 76 cents applies
# from then.") is merged with its predecessor. That direction is safe - a merged
# sentence names both documents and is skipped - and we do not write that way.
SENTENCE_END = r"[;!?]\s|\.\s(?![a-z0-9])"

# Correct prose that DESCRIBES the mid-year change necessarily quotes the old rate in
# the same sentence as the new one: "Announcement 2026-11 raised the rate from 72.5
# cents to 76 cents" is accurate, and the first draft of this rule flagged it. The
# exemption is directional, which is what makes it safe: it excuses the wrong rate only
# when it is the FROM value and the cited document's own rate is the TO value. Reverse
# the documents - "Notice 2026-10 raised the rate from 72.5 to 76 cents" - and the
# wrong rate is 76c, which is not the FROM value, so it still flags.
# (The pattern is built per-rate inside _describes_transition, not stored here - a
# constant computed and never used is the defect Codex filed against build_review_
# gallery.py's `ledgers`, and one in this file would be the same mistake.)

# inline tags whose text belongs to the surrounding block; block-level tags delimit.
INLINE_TAGS = r"(?i)</?(?:b|i|em|strong|span|a|small|sup|sub|u|mark|abbr|wbr)\b[^>]*>"


# --- rule 8: a privacy denial the page's own <head> falsifies --------------------
#
# 2026-07-28. Cloudflare Web Analytics was wired into all six pages one morning and
# the prose describing it was not touched, so privacy.html said "We run no analytics"
# and, worse, invited the reader to "check: this site loads no third-party scripts at
# all" - on a page that was at that moment loading static.cloudflareinsights.com. A
# reader who accepted the invitation would have caught us lying on the one page whose
# entire job is to be believed. That is the same shape as the incident that created
# this whole file (a CAPABILITY added, COPY elsewhere silently falsified), which is
# why it belongs here and not in a note.
#
# Both halves are mechanically detectable, this file's bar for a rule:
#   the claim      -> a denial of analytics / third-party scripts in published copy
#   the capability -> a <script src> pointing off-domain, in the same file
#
# Scoped per BLOCK and skipping blocks that carry a retraction marker, for the reason
# rule 7 had to learn the hard way: retracting a false sentence means quoting it, and
# the corrected privacy.html quotes both denials verbatim. A guard that fires on the
# incident report is a guard somebody deletes.
#
# Google Fonts is deliberately NOT counted as the trigger, though it is a third-party
# REQUEST: it is a stylesheet, not a script, and folding it in would make the rule
# argue a judgement call instead of a fact. The honest disclosure of it is a copy
# decision, made on the page; this rule polices only the mechanical contradiction.
ANALYTICS_DENIAL = [
    r"we run\s*(?:<[^>]+>\s*)?no analytics",
    r"no analytics (?:has ever been|is|are)\s+(?:installed|running|used)",
    r"loads? no third-party scripts",
    r"no third-party scripts at all",
    r"we (?:run|use) no (?:tracking|tracker)",
]
THIRD_PARTY_SCRIPT = [
    r"<script[^>]+\bsrc\s*=\s*[\"']https?://(?!deedwell\.co\b)[^\"']+",
]
RETRACTION_MARKER = (r"(?:Until \d{4}-\d{2}-\d{2}|was wrong|were wrong|CORRECTED|"
                     r"Corrected|corrected|no longer (?:true|says)|used to (?:say|read)|"
                     r"this policy (?:described|said)|an earlier version)")


def privacy_denial_vs_scripts(path, text):
    """Rule 8. A denial of analytics on a page that loads an off-domain script."""
    script, s_line = find(THIRD_PARTY_SCRIPT, text)
    if not script:
        return []
    out = []
    for m in re.finditer(r"<p\b[^>]*>.*?</p>", text, flags=re.S | re.I):
        block = m.group(0)
        if re.search(RETRACTION_MARKER, block):
            continue                       # it is retracting the claim, not making it
        pat, off = find(ANALYTICS_DENIAL, block)
        if not pat:
            continue
        out.append(
            "%s:%d denies analytics/third-party scripts (/%s/) while this page loads "
            "an off-domain <script src> (line %d). The reader is invited to check and "
            "will find it. Say what actually runs, or mark the sentence retracted."
            % (path, text[: m.start()].count("\n") + off, pat, s_line))
    return out


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


def _describes_transition(sentence, wrong_pat, own_pat):
    """True when the wrong rate appears as the FROM value of a change TO the cited
    document's own rate - i.e. correct prose about the mid-year increase.

    Directional on purpose. Only "from <wrong> ... to <own>" is excused; "from <own>
    ... to <wrong>" is exactly the mis-attribution the rule exists for and still fires.
    """
    return bool(re.search(r"\bfrom\b\s*" + wrong_pat + r"[^.;!?]{0,60}?\bto\b\s*" + own_pat,
                          sentence, re.I))


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
        own = next(p for p, _, s in RATE_SOURCES if s == cited)
        for rate_pat, rate_label, sets_it in RATE_SOURCES:
            if sets_it == cited:
                continue  # this document does set this rate
            m = re.search(rate_pat, sentence, re.I)
            if m and _describes_transition(sentence, rate_pat, own):
                continue  # "X raised the rate FROM <other> TO <its own>" - accurate
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


# --- rule 6: every page-count claim must name the same book -------------------
#
# 2026-07-28 01:0x. The homepage said "108 pages" in the hero and in the buy
# section, rendered a cover image reading "108 PAGES - 8.5 x 11 IN", and then two
# sections down said 94 in the "Inside the book" heading, 94 in the closing stat
# tile, and '"numberOfPages": 94' in the JSON-LD Book node that crawlers and
# answer engines read. /rental/, /checklist/ and /updates/ all said 108. One page
# contradicted itself about what the buyer receives, on the landing page four of
# our six live Pinterest pins point at.
#
# The rule that should have stopped this ALREADY EXISTED. cedarstone-ops' enforcer
# carries `derive-dont-restate`, and its cost field names "the site" among the
# surfaces the 26 July 94->108 repagination left false. It fires on Write|Edit.
# Nobody was editing the homepage - the false number simply sat there - so a
# defect that needs NO ACTION to persist was unreachable by a trigger that needs
# one. That asymmetry is the whole reason this is a sweep and not another rule:
# an at-the-moment-of-action reminder cannot catch a claim that is already wrong
# and untouched. Everything the enforcer covers still stands; this covers the
# half it structurally cannot see.
#
# Deliberately a CONSISTENCY check against one declared constant, not a live read
# of Amazon: a gate that needs the network is a gate that gets disabled, and this
# one runs in .githooks/pre-commit. BOOK_PAGES is the single place a repagination
# is typed, so the next one cannot half-land across the site the way this one did.
#
# Known and intended: the DIGITAL pdf is 109 pages (108 record pages plus a front
# page). If a page ever claims 109 this rule fires, and that is correct - it
# forces the copy to say "record pages" rather than leaving a buyer to reconcile
# two numbers. Markdown logs (this incident is written up in several) are
# structurally out of reach: main() walks *.html only, and skips tools/.
BOOK_PAGES = 108     # measured from the shipped print interior
                     # out/Deedwell_Rental_Property_Record_Book.pdf on 2026-07-28:
                     # 108 /Type/Page objects, /Count 108. Corroborated by Amazon's
                     # detail page ("Print length 108 pages") and four "108" on the
                     # live Etsy listing. Change this ONLY together with the
                     # artifact, then run --selftest.

# A page count is a claim about THE BOOK only in forms that cannot mean anything
# else. This rule's first real firing was a false positive, on true copy: the
# review page says "All 42 expense ledger pages ... the twelve monthly rent rolls
# close the same way - 54 pages that add themselves up, in all" (42 + 12 = 54, a
# SUBSET of the book, arithmetically right). A bare "NN pages" in running prose is
# therefore NOT a length claim, and that fixture is now a permanent control below.
# The four qualifying forms, each justified by a real string in our own copy:
#   attributive  "108-page, 8.5 x 11 record book"       (/checklist/)
#   house phrase "the same 108 record pages as a PDF"   (home, /rental/)
#   spec pair    "94 pages, 8.5 x 11"                   (the stat tile that shipped)
#   heading      "<h2>94 pages, in the order the year happens.</h2>"  (ditto)
# plus the JSON-LD key, which is unambiguous wherever it appears.
PAGE_CLAIM = re.compile(r"(?<![\d.])(\d{2,4})(\s*-\s*|\s+)(record\s+)?pages?\b", re.I)
JSON_PAGE_CLAIM = re.compile(r'"numberOfPages"\s*:\s*(\d{2,4})')
TRIM_SIZE = re.compile(r"8\.5\s*(?:x\s*)?11\b", re.I)
HEADING = re.compile(r"<h[1-6][^>]*>.*?</h[1-6]>", re.I | re.S)


def page_count_claims(text):
    """(line, value, snippet) for every claim about the BOOK'S LENGTH in one file.

    Tags and entities are blanked to spaces of EQUAL LENGTH - the same discipline
    flatten() uses - so a claim split across markup ("<b>94</b><span>pages") reads
    as one phrase while offsets still map to real line numbers.
    """
    def blank(m):
        return " " * len(m.group(0))

    flat = re.sub(r"<[^>]+>", blank, text)
    flat = re.sub(r"&[a-z]+;|&#\d+;", blank, flat, flags=re.I)

    # headings do not nest, so a non-greedy span is safe here
    heads = [(m.start(), m.end()) for m in HEADING.finditer(text)]

    hits = {}
    for m in JSON_PAGE_CLAIM.finditer(flat):
        hits[m.start()] = int(m.group(1))
    for m in PAGE_CLAIM.finditer(flat):
        attributive = "-" in m.group(2)
        house_phrase = m.group(3) is not None
        spec_pair = bool(TRIM_SIZE.search(flat, m.end(), m.end() + 40))
        in_heading = any(a <= m.start() < b for a, b in heads)
        if attributive or house_phrase or spec_pair or in_heading:
            hits[m.start()] = int(m.group(1))

    return [(flat.count("\n", 0, k) + 1, v,
             " ".join(flat[max(0, k - 45):k + 45].split()))
            for k, v in sorted(hits.items())]


def page_counts_agree(texts_by_label):
    problems = []
    for label in sorted(texts_by_label):
        for line, value, snippet in page_count_claims(texts_by_label[label]):
            if value != BOOK_PAGES:
                problems.append(
                    "%s:%d page-count claim says %d, the shipped book is %d "
                    "(...%s...)" % (label, line, value, BOOK_PAGES, snippet))
    return problems


PAGECOUNT_SELFTEST = [
    # the three that actually shipped, verbatim from index.html before the fix
    ("the section heading that shipped", True,
     '<p class="fine">108 pages, 8.5 &times; 11.</p>'
     '<h2><span class="num">94</span> pages, in the order the year happens.</h2>'),
    ("the closing stat tile that shipped", True,
     '<div class="stat"><b>94</b><span>pages, 8.5&nbsp;&times;&nbsp;11</span></div>'),
    ("the JSON-LD Book node crawlers and answer engines read", True,
     '<script type="application/ld+json">'
     '{"@type":"Book","numberOfPages": 94,"inLanguage":"en-US"}</script>'),
    # the correct forms already live on the other pages must stay silent
    ("108-page hyphenated, as /checklist/ writes it", False,
     'the <b>Rental Property Record&nbsp;Book</b> is the 108-page, '
     '8.5&nbsp;&times;&nbsp;11 record book the list came from'),
    ("108 record pages, as /rental/ writes it", False,
     '<p class="meta">108 record pages &middot; 8.5 x 11 inches &middot; published</p>'),
    # negative controls: a gate that nags on ordinary work is a gate somebody
    # switches off, and every one of these sits on the real pages today
    ("trim size and mapped lines are not page counts", False,
     '<div class="stat"><b>16</b><span>Schedule&nbsp;E lines mapped</span></div>'
     '<div class="stat"><b>2</b><span>2026 mileage rates, split by date</span></div>'
     '<p>Nothing decorative. Every page exists because a landlord has to record.</p>'),
    ("css that merely contains the digits", False,
     '<style>.links a.btn{font-size:.94rem} .sig{padding-top:44px;font-size:.94rem}'
     '</style>'),
    ("a caption naming a page NUMBER, not a count", False,
     '<p>Page 5 &mdash; Your Schedule E Map. Lines per the 2025 IRS instructions '
     'for Schedule E (Form 1040).</p>'),
    # THIS RULE'S OWN FIRST REAL FIRING WAS A FALSE POSITIVE, on true copy, and it
    # is kept verbatim from review/index.html so no future tightening can lose it.
    # A SUBSET count in running prose is not a claim about the book's length.
    ("a subset count in prose: 42 ledgers + 12 rent rolls = 54 self-totalling", False,
     '<p class="note">All 42 expense ledger pages (p.33 and p.74 here) end in a '
     '15-box strip that totals the page by Schedule E line. The twelve monthly '
     'rent rolls close the same way, though totalled by property onto Schedule E '
     'line 3 rather than by line &mdash; 54 pages that add themselves up, in all.'
     '</p>'),
]


def check_file(path, text, capture_pages=None, esp_present=False):
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
    problems.extend(sending_promises(path, text, esp_present))
    problems.extend(privacy_denial_vs_scripts(path, text))

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
    # --- the four gaps Codex filed against babf160, each proved before it was fixed ---
    ("shorthand rates: the abbreviation the rule's OWN commit message used", True,
     '<p>2026 split year: 72.5c to Jun 30, then 76c from Jul 1 '
     '(IRS Announcement 2026-11).</p>'),
    ("abbreviated citation: 'Ann. 2026-11' must not hide behind a sentence split", True,
     '<p>Deduct 72.5 cents a mile for every trip you made in 2026 (Ann. 2026-11).</p>'),
    ("correct prose describing the increase must NOT flag", False,
     '<p>IRS Announcement 2026-11 raised the rate from 72.5 cents to 76 cents.</p>'),
    ("...but the SAME shape with the documents swapped still must flag", True,
     '<p>IRS Notice 2026-10 raised the rate from 72.5 cents to 76 cents.</p>'),
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


# positive control for rule 5: the three that actually shipped - two live on
# /updates/ until 2026-07-26, one latent in a landing generator - and the corrected
# copy that replaced them. The generator fixture is the one that matters most: it is
# the case a naive proximity guard would have waved through.
SENDING_SELFTEST = [
    ("updates hero, live until 07-26", True,
     '<p class="micro">Email only. A handful of tax-relevant notes a year. '
     'Unsubscribe anytime.</p>'),
    ("updates address block, live until 07-26", True,
     '<p>We do not sell or rent it, and every email carries an unsubscribe link.</p>'),
    ("dead landing generator (negator governs *spam*, not the claim)", True,
     '<p class="trust">Instant download. No spam &mdash; unsubscribe in one click.</p>'),
    ("corrected updates hero", False,
     '<p class="micro">Email only. A handful of tax-relevant notes a year. Reply '
     '&ldquo;stop&rdquo; to any of them and we delete your address.</p>'),
    ("corrected address block", False,
     '<p>There is no unsubscribe link, because there is no marketing platform behind '
     'this &mdash; the notes are written and sent from an ordinary mailbox.</p>'),
    ("corrected privacy disclosure", False,
     '<p>Because there is no sending platform, our notes carry no unsubscribe link. '
     'Reply &ldquo;stop&rdquo; to any of them and we delete the address.</p>'),
    ("the page's own post-mortem, quoting the dead copy it warns against", False,
     '<!-- The registration form that stood here until 2026-07-22 told them "You are\n'
     '     registered. Check your inbox for a confirmation." Nothing was sent. -->'),
    # --- the wording gaps Codex filed against 001c78c: the same false promise, said
    # --- a different way, would have shipped past a green check.
    ("same promise, different verb: 'includes'", True,
     '<p>We do not sell or rent it, and every email includes an unsubscribe link.</p>'),
    ("same promise, different verb: 'has'", True,
     '<p>Every email has an unsubscribe link at the bottom.</p>'),
    ("same promise, loose phrasing", True,
     '<p>You can unsubscribe whenever you want.</p>'),
    ("auto-delivery promised in a different tense", True,
     '<p>We will send the checklist straight to your inbox.</p>'),
    ("a stylesheet is not copy and promises nobody anything", False,
     '<style>.note:after{content:"unsubscribe anytime"}</style>'),
    # The REAL privacy.html sentence the widened verb list fired on. Found by running
    # against the served pages, not by imagining a case: this is the site telling the
    # truth about copy it withdrew, and a checker that fires on the incident report is
    # a checker somebody switches off. Kept verbatim so nobody re-breaks it.
    ("privacy.html's own post-mortem, in visible prose", False,
     '<p>It had said a registered owner\'s address was kept for <i>one</i> purpose, '
     'while the registration page promised three uses of it &mdash; and that page also '
     'said every email would carry an unsubscribe link, which was never possible, '
     'because there is no sending platform to put one in.</p>'),
    # ...and the guard that keeps that exemption honest: a reporting verb in some OTHER
    # clause must not launder a promise the page is making right now.
    ("a real promise is not excused by a 'said' in a different clause", True,
     '<p>We said it before and we will say it again: every email carries an '
     'unsubscribe link.</p>'),
]


# positive control for rule 5's CAPABILITY half - the switch that decides whether the
# rule runs at all. Codex filed that a bare vendor mention flipped it, which put the
# off switch for the whole rule inside our own honest prose. Wiring counts; talking
# does not. Every fixture here is a sentence or snippet we plausibly write.
# The real beacon tag, as the analytics commit wrote it into all six pages. Named once
# because it appears in four fixtures, and because a tag full of double quotes inlined
# four times is how the first draft of this block shipped a SyntaxError into the
# pre-commit gate. No literal newlines in these fixtures either: HTML does not need
# them. A fixture should exercise the rule, not the quoting.
_BEACON = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js">'
           '</script>')

PRIVACY_SELFTEST = [
    ("the VERBATIM live contradiction: denial + the beacon that shipped", True,
     "<p>We run <b>no analytics</b>. You can check: this site loads no third-party "
     "scripts at all.</p>" + _BEACON),
    ("the denial alone, with no off-domain script, is TRUE and must stay silent", False,
     "<p>We run <b>no analytics</b>. You can check: this site loads no third-party "
     "scripts at all.</p>"),
    ("the REAL retraction, which quotes both denials to bury them", False,
     "<p>Then on 2026-07-28 it was wrong in the other direction. For a few hours this "
     "page still said 'we run no analytics' and invited you to 'check: this site loads "
     "no third-party scripts at all' - while the page you were reading loaded one. "
     "Corrected the same day.</p>" + _BEACON),
    ("honest disclosure naming the tool must stay silent", False,
     "<p>Since 2026-07-28 we run one analytics tool: Cloudflare Web Analytics. It uses "
     "no cookies and does not fingerprint you.</p>" + _BEACON),
    ("a retraction elsewhere must not silence a LIVE denial", True,
     "<p>An earlier version of this policy was wrong about the checklist.</p>"
     "<p>We run no analytics.</p>" + _BEACON),
    ("an inline (non-src) script must not count as third-party", False,
     "<p>We run <b>no analytics</b>.</p><script>var a=1;</script>"),
]

ESP_SELFTEST = [
    ("our own honest denial must NOT count as a platform", False,
     '<p>We do not use MailerLite, Mailchimp or any other sending platform.</p>'),
    ("a commented-out vendor must NOT count", False,
     '<!-- TODO: evaluate Buttondown once the list is worth paying for -->'),
    ("an unrelated external form (site search) must NOT count", False,
     '<form action="https://duckduckgo.com/"><input type="text" name="q"></form>'),
    ("prose naming the category must NOT count", False,
     '<p>Tools like ConvertKit and Substack charge per subscriber.</p>'),
    ("a form POSTing to a vendor DOES count", True,
     '<form action="https://assets.mailerlite.com/jsonp/1/forms/x/subscribe">'
     '<input type="email" name="fields[email]"></form>'),
    ("an embedded vendor widget DOES count", True,
     '<script src="https://f.convertkit.com/ckjs/ck.5.js"></script>'),
    ("a Netlify-processed form DOES count", True,
     '<form name="signup" data-netlify="true"><input type="email"></form>'),
    ("a hosted signup page linked from our copy DOES count", True,
     '<a href="https://cedarstone.buttondown.email/">Get the notes</a>'),
    ("an unknown vendor posting an email field off-site DOES count", True,
     '<form action="https://some-esp-we-never-heard-of.io/f/abc">'
     '<label>Email</label><input type="email" name="email"></form>'),
    ("a config key naming a vendor DOES count", True,
     'const MAILERLITE_API_KEY = process.env.ML_KEY;'),
]


def selftest():
    ok = True
    cases = ([(n, f, h, interior_claims) for n, f, h in SELFTEST]
             + [(n, f, h, mileage_sources) for n, f, h in RATE_SELFTEST]
             + [(n, f, h, lambda p, t: mileage_sources_page(p, t, 1))
                for n, f, h in PDF_SELFTEST]
             + [(n, f, h, lambda p, t: sending_promises(p, t, esp_present=False))
                for n, f, h in SENDING_SELFTEST]
             + [(n, f, h, lambda p, t: page_counts_agree({p: t}))
                for n, f, h in PAGECOUNT_SELFTEST])
    for name, should_flag, html, rule in cases:
        flagged = bool(rule("selftest", html))
        status = "PASS" if flagged == should_flag else "FAIL"
        if flagged != should_flag:
            ok = False
        print("  [%s] %s (expected %s, got %s)"
              % (status, name, "flag" if should_flag else "clean",
                 "flag" if flagged else "clean"))

    # rule 5's capability half: WIRING counts, MENTION does not. Exercised through the
    # same two predicates esp_configured() uses, so a fixture passing here means the
    # walk over real files would agree.
    for name, should_wire, html in ESP_SELFTEST:
        body = _published_copy(html)
        wired = bool(find(ESP_WIRING, body)[0]) or _external_form_capture(body)
        status = "PASS" if wired == should_wire else "FAIL"
        if wired != should_wire:
            ok = False
        print("  [%s] esp capability: %s (expected %s, got %s)"
              % (status, name, "wired" if should_wire else "not wired",
                 "wired" if wired else "not wired"))

    # rule 5 must AUTO-RELAX, or it is a permanent ban on words rather than a check on
    # capability. Asserted with the worst fixture: the promise that shipped.
    relaxes = not sending_promises(
        "selftest", SENDING_SELFTEST[1][2], esp_present=True)
    print("  [%s] rule 5 permits the promise once a sending platform exists"
          % ("PASS" if relaxes else "FAIL"))
    if not relaxes:
        ok = False

    for name, should_flag, html in PRIVACY_SELFTEST:
        flagged = bool(privacy_denial_vs_scripts("selftest", html))
        status = "PASS" if flagged == should_flag else "FAIL"
        if flagged != should_flag:
            ok = False
        print("  [%s] rule 8: %s (expected %s, got %s)"
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

    # rule 5's capability half, measured once across the served site
    esp_present, esp_where = esp_configured(ROOT)

    problems = []
    for path in sorted(targets):
        problems.extend(
            check_file(label(path), texts[path], capture_pages, esp_present))

    # rule 6 is cross-file on purpose: the defect it exists for was one page
    # disagreeing with four others, which no per-file check can see.
    problems.extend(
        page_counts_agree({label(p): texts[p] for p in sorted(targets)}))

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

    # the book length is printed on every run, green or not: a pass that does not
    # say WHAT it agreed with is how a stale constant survives a green checker.
    print("checked %d html file(s) and %d served pdf(s) "
          "[sending platform: %s] [book: %d pages]"
          % (len(targets), len(pdfs),
             ("WIRED at %s - rule 5 relaxed" % esp_where) if esp_present else "NONE",
             BOOK_PAGES))
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
