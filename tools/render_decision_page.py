"""Build /review/decide/ - the page that lets the Chairman actually SEE the top-of-funnel
branch before he merges it.

WHY THIS EXISTS. Three changes have been waiting on one look from him, and on
2026-07-28 (pulse 11) it turned out that look was IMPOSSIBLE to give: every render of
every change rode on the very branch it existed to get reviewed. The pre-publish
gallery is on `main` and served; the evidence was not. A mechanism built to break a
circular dependency had the dependency inside it.

So this script renders BOTH SIDES ITSELF, from two git refs, and writes the result to
`main` where it is served. It never reads a picture somebody else built.

HOW IT AVOIDS THE OBVIOUS TRAP. It does not check out anything. It exports both trees
with `git archive` into temp dirs and serves each on its own loopback port, so the
working tree is never touched and no branch is ever moved. Pulse 11 lost a branch to a
stray reset; a renderer that leaves HEAD exactly where it found it cannot repeat that.

POSITIVE CONTROLS ARE THE POINT, NOT A GARNISH. Two screenshots of two trees prove
nothing if the trees are the same, or if the selector missed. Before it writes a single
image this asserts, against the SERVED DOM and the real PDF bytes, that each claimed
difference is actually present on the AFTER side and actually absent on the BEFORE
side. If any assertion fails it writes nothing and exits 1. A zero from an unproven
instrument is not evidence - this repo has paid for that lesson more than once.

NOTHING PUBLISHED MAY OUTLIVE ITS SOURCE. The sources here are two commits, not two
files, so the manifest records both shas and `--check` refuses when either ref has
moved. The instant `feat/top-of-funnel` merges, this page IS stale by construction -
that is correct, and it is the signal to delete it.

Usage:
  python tools/render_decision_page.py            # build
  python tools/render_decision_page.py --check    # stale? exit 1 with what to do
"""
import argparse
import asyncio
import functools
import hashlib
import http.server
import io
import json
import os
import socketserver
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "review" / "decide"
IMG = OUT / "img"

BEFORE_REF = "main"
AFTER_REF = "feat/top-of-funnel"

PDF_REL = "files/Deedwell-Schedule-E-Deduction-Checklist.pdf"
SUBSCRIBE = "https://deedwell.gumroad.com/subscribe"

# The three things this page pictures. Freshness is bound to THESE BLOBS, not to the
# two branch tips, and that distinction is not pedantry - it was a live defect. The
# first version compared `main`'s sha to the one recorded at render time, so the very
# commit that PUBLISHED this page moved main and made the page declare itself stale
# while every picture on it was still exactly right. Bind to what the picture is a
# picture OF: if index.html, /checklist/ and the PDF are byte-identical on both refs to
# what was rendered, the page is true no matter how many commits have landed around it.
PICTURED = ["index.html", "checklist/index.html", PDF_REL]

# Cloudflare Web Analytics. Every page under the site root carries it - the analytics
# organ walks the tree, so a new page that omits it fails `build_site_analytics.py
# --check`. Copied verbatim from the served pages; the token is public by design.
BEACON = (
    '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
    "data-cf-beacon='{\"token\": \"478e11c5d4574ad4b70f275d35088b7d\"}'></script>"
)

CEDAR = (31, 61, 47)
PAPER = (250, 247, 240)
INK = (26, 26, 26)
LINE = (228, 220, 201)


# ---------------------------------------------------------------- git plumbing

def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def sha_of(ref):
    try:
        return git("rev-parse", ref)
    except subprocess.CalledProcessError:
        return None


def blob_ids(ref):
    """git's own content hash for each pictured file at a ref. Cheap, exact, and it
    cannot be fooled by a commit that touched something else."""
    return {p: git("rev-parse", f"{ref}:{p}") for p in PICTURED}


def export(ref, dest):
    """Materialise a ref's tree without touching the working tree or moving HEAD."""
    dest.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", ref],
        check=True, capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
        tf.extractall(dest)
    return dest


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory):
    handler = functools.partial(_Quiet, directory=str(directory))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    import threading
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


# ---------------------------------------------------------------- compositing

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]


def _font(size):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def pair(before, after, out_path, panel_w=820, gutter=26, cap_h=44):
    """BEFORE on the left, AFTER on the right, each labelled, on one canvas.

    Both panels are scaled to the same width so a height difference is a REAL height
    difference and not an artefact of the render. The labels are burned into the image
    on purpose: a screenshot gets forwarded, cropped and re-sent, and an unlabelled
    before/after pair is one forward away from being read backwards.
    """
    def prep(im):
        if im.width != panel_w:
            im = im.resize((panel_w, max(1, round(im.height * panel_w / im.width))), Image.LANCZOS)
        return im.convert("RGB")

    b, a = prep(before), prep(after)
    body_h = max(b.height, a.height)
    canvas = Image.new("RGB", (panel_w * 2 + gutter, body_h + cap_h), PAPER)
    d = ImageDraw.Draw(canvas)

    for x, label, colour in ((0, "BEFORE  \u00b7  what is live now", (110, 104, 92)),
                             (panel_w + gutter, "AFTER  \u00b7  what one merge publishes", CEDAR)):
        d.rectangle([x, 0, x + panel_w - 1, cap_h - 1], fill=colour)
        d.text((x + 14, cap_h // 2), label, fill=(244, 240, 230), font=_font(19), anchor="lm")

    canvas.paste(b, (0, cap_h))
    canvas.paste(a, (panel_w + gutter, cap_h))
    for x in (0, panel_w + gutter):
        d.rectangle([x, cap_h, x + panel_w - 1, cap_h + body_h - 1], outline=LINE)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=88, optimize=True)
    return out_path


def pdf_pages_text(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    out = [p.get_text() for p in doc]
    doc.close()
    return out


def pdf_render_page(pdf_path, idx, dpi=150):
    """Render one page of a PDF at a page index chosen by the CALLER.

    Deliberately dumb. The first version of this located the page itself and, when the
    phrase was absent (which is the whole definition of the BEFORE side), fell back to
    "the last page" - so it rendered page 2 of the old PDF against page 1 of the new
    one and would have shown a before/after pair of two different pages. The caller
    finds the page ONCE, in the tree that actually contains the change, and renders
    that same index on both sides.
    """
    import fitz
    doc = fitz.open(pdf_path)
    if idx >= doc.page_count:
        doc.close()
        raise IndexError(f"{pdf_path} has {doc.page_count} pages, wanted index {idx}")
    pix = doc[idx].get_pixmap(dpi=dpi)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    doc.close()
    return im


# ---------------------------------------------------------------- rendering

async def shots(before_port, after_port, failures):
    from playwright.async_api import async_playwright

    out = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def load(port, path, w, h):
            page = await browser.new_page(viewport={"width": w, "height": h},
                                          device_scale_factor=2)
            await page.goto(f"http://127.0.0.1:{port}{path}", wait_until="networkidle")
            return page

        async def seam(page):
            """The band of the homepage between the free-checklist magnet and About.

            That is exactly where #alerts was inserted, so the same clip on both trees
            shows the seam itself rather than two similar-looking long pages.
            """
            box = await page.evaluate(
                """() => {
                     const f = document.querySelector('#free');
                     const a = document.querySelector('#about');
                     if (!f || !a) return null;
                     const fr = f.getBoundingClientRect(), ar = a.getBoundingClientRect();
                     const y = fr.top + window.scrollY;
                     return {x: 0, y, width: document.documentElement.clientWidth,
                             height: (ar.top + window.scrollY) - y};
                   }"""
            )
            return box

        # ---- 1 + 2: the homepage seam, desktop and phone
        for tag, w, h, name in (("desktop", 1100, 900, "01_home_band.jpg"),
                                ("phone", 390, 844, "02_home_phone.jpg")):
            imgs = {}
            for side, port in (("before", before_port), ("after", after_port)):
                page = await load(port, "/", w, h)

                has = await page.evaluate("() => !!document.querySelector('#alerts')")
                if side == "before" and has:
                    failures.append(f"home/{tag}: BEFORE already has #alerts - the two trees are not different")
                if side == "after" and not has:
                    failures.append(f"home/{tag}: AFTER has no #alerts - nothing to show")
                if side == "after" and has:
                    btn = await page.evaluate(
                        """() => {const b=document.querySelector('#alerts .btn');
                                  if(!b) return null;
                                  const r=b.getBoundingClientRect();
                                  return {href:b.getAttribute('href'),h:Math.round(r.height)};}"""
                    )
                    if not btn:
                        failures.append(f"home/{tag}: AFTER #alerts has no .btn")
                    else:
                        if btn["href"] != SUBSCRIBE:
                            failures.append(f"home/{tag}: button href {btn['href']!r} != {SUBSCRIBE}")
                        if btn["h"] < 44:
                            failures.append(f"home/{tag}: button {btn['h']}px tall, under the 44px tap target")

                sw = await page.evaluate("() => document.documentElement.scrollWidth")
                if sw > w:
                    failures.append(f"home/{tag}/{side}: scrollWidth {sw} > viewport {w} (horizontal overflow)")

                clip = await seam(page)
                if clip is None:
                    failures.append(f"home/{tag}/{side}: #free or #about missing - cannot locate the seam")
                    await page.close()
                    continue
                # full_page=True is NOT optional here: without it the screenshot is the
                # VIEWPORT, so a clip in page coordinates below the fold is rejected as
                # "outside the resulting image" - which is exactly where this seam sits.
                png = await page.screenshot(clip=clip, full_page=True)
                imgs[side] = Image.open(io.BytesIO(png))
                await page.close()
            if len(imgs) == 2:
                out[name] = (imgs["before"], imgs["after"])

        # ---- 3 + 4: the free-checklist landing page
        texts = {}
        pages = {}
        for side, port in (("before", before_port), ("after", after_port)):
            page = await load(port, "/checklist/", 1100, 900)
            body = await page.evaluate("() => document.body.innerText")
            texts[side] = body
            rows = await page.evaluate(
                "() => document.querySelectorAll('table.dl tr:not(.grp)').length"
            )
            head = await page.evaluate(
                """() => {const h=document.querySelector('h1');
                          return h ? h.innerText.trim() : null;}"""
            )
            full = await page.screenshot(full_page=True)
            top = await page.screenshot(clip={"x": 0, "y": 0, "width": 1100, "height": 1150},
                                        full_page=True)
            pages[side] = (Image.open(io.BytesIO(full)), Image.open(io.BytesIO(top)), rows, head)
            await page.close()

        if "ordinary short-term-rental expense" not in texts["before"]:
            failures.append("checklist BEFORE: the short-term-rental lead sentence is not there - "
                            "either main already changed or the selector is blind")
        if "ordinary short-term-rental expense" in texts["after"]:
            failures.append("checklist AFTER: still opens by disqualifying a long-term landlord")
        if "Management fees" not in texts["after"]:
            failures.append("checklist AFTER: no Schedule E line 11 (Management fees) row")
        if "Management fees" in texts["before"]:
            failures.append("checklist BEFORE: already has line 11 - the two trees are not different")
        if pages["after"][2] != pages["before"][2]:
            failures.append(f"checklist: row count moved {pages['before'][2]} -> {pages['after'][2]}; "
                            "the headline 35 is printed inside a LIVE pin image and cannot change")

        out["03_checklist_top.jpg"] = (pages["before"][1], pages["after"][1])
        out["04_checklist_full.jpg"] = (pages["before"][0], pages["after"][0])

        await browser.close()
    return out, texts, pages


async def verify_page():
    """Serve the repo as it now stands and LOOK at the page that was just written.

    Returns the path of a proof screenshot, or None (having printed why) if the page
    does not hold up. The image check is `naturalWidth`, not the presence of a <img>
    tag: a src that 404s still parses perfectly.
    """
    from playwright.async_api import async_playwright

    httpd, port = serve(REPO)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 1000})
            await page.goto(f"http://127.0.0.1:{port}/review/decide/", wait_until="networkidle")

            bad = await page.evaluate(
                """() => [...document.images]
                     .filter(i => !i.complete || i.naturalWidth === 0)
                     .map(i => i.getAttribute('src'))"""
            )
            n = await page.evaluate("() => document.images.length")
            sw = await page.evaluate("() => document.documentElement.scrollWidth")
            beacon = await page.evaluate(
                "() => !!document.querySelector('script[data-cf-beacon]')")

            # Deliberately OUTSIDE the repo. Written into review/decide/img/ it would be
            # hashed into the manifest on the next build and then overwritten by this
            # very step, so --check would report the page as hand-edited every time.
            proof = Path(tempfile.gettempdir()) / "deedwell_decide_proof.jpg"
            await page.screenshot(path=str(proof), full_page=True, type="jpeg", quality=70)
            await browser.close()
    finally:
        httpd.shutdown()

    if bad:
        print("FAIL - the page renders but these images do not load:")
        for b in bad:
            print("  -", b)
        return None
    if n == 0:
        print("FAIL - the page loaded with zero images")
        return None
    if sw > 1280:
        print(f"FAIL - horizontal overflow: scrollWidth {sw} > 1280")
        return None
    if not beacon:
        print("FAIL - no analytics beacon; build_site_analytics.py --check will refuse")
        return None
    return proof


# ---------------------------------------------------------------- the page

def render_html(before_sha, after_sha, built, images):
    def fig(name, tag, title, note):
        return f"""
  <section>
    <span class="tag">{tag}</span>
    <h2>{title}</h2>
    <p class="note">{note}</p>
    <img src="img/{name}" alt="{title} - before and after">
  </section>"""

    body = "".join([
        fig("01_home_band.jpg", "Change 1 of 3 &middot; the homepage",
            "A way to join the list, where four of six pins land",
            "Four of our six live Pinterest pins send people to this page, and in the whole history of "
            "this repository it has never carried an email ask - not once. The band below is deliberately "
            "the quietest thing on the page: it sits <em>after</em> the free checklist, never in front of "
            "it, so it reads as an optional follow-on to a gift rather than a toll gate. Cedar button, not "
            "gold; gold stays reserved for buy-the-book and take-the-checklist. No form and no new account: "
            "the list is hosted by Gumroad, our own storefront."),
        fig("02_home_phone.jpg", "Change 1 &middot; on a phone",
            "The same band at 390px",
            "Most Pinterest traffic is a phone. Centred text stops being comfortable past about three lines "
            "and this copy runs to nine on a narrow screen, so the two long blocks go left-aligned under "
            "720px while the heading and button stay centred. Judged from this render, not from the markup."),
        fig("03_checklist_top.jpg", "Change 2 of 3 &middot; the free checklist page",
            "It opened by telling a landlord it was not for them",
            "The live page opens <em>&ldquo;every one of these is an ordinary short-term-rental expense&rdquo;</em> "
            "and leads with costs only an Airbnb host pays. That sentence was written on 22 July, three days "
            "before the Deedwell pivot, and twelve later commits missed it because a rebrand sweep hunts old "
            "brand <em>names</em> and this defect never used one. We are about to offer this exact page to five "
            "<em>rental-housing</em> associations as a member benefit."),
        fig("04_checklist_full.jpg", "Change 2 &middot; the whole page",
            "Regrouped so neither buyer is disqualified",
            "Twenty-six lines that apply to any rental first - led by mortgage interest, taxes, insurance, "
            "depreciation and management fees - then nine that only a short stay incurs, under "
            "<em>&ldquo;skip these nine if your tenant has a lease.&rdquo;</em> The count stays at 35 because that "
            "number is printed inside a live pin image and a published pin cannot be edited; two overlapping "
            "pairs were merged and the freed slots went to Schedule E lines 11 and 13, the two an Airbnb host "
            "never pays. Coverage goes from 13 of 15 expense lines to 15 of 15. No tax wording was touched."),
        fig("05_pdf_capture.jpg", "Change 3 of 3 &middot; the PDF people download",
            "The free PDF was a one-way door",
            "The checklist we give away carried exactly one URL and it was a product page. Somebody prints it, "
            "keeps it, and has no way back to us that is not a shop. One line now sits under the mileage note - "
            "the rate genuinely does change most years, which is the honest reason to want to be told."),
    ])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>Deedwell &mdash; the top of the funnel, before and after</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--cedar:#1F3D2F;--paper:#FAF7F0;--ink:#1A1A1A;--dim:#6f6a5c;--line:#e4dcc9;--gold:#8F7620;
 --serif:'Fraunces',Georgia,serif;--sans:'Inter',system-ui,sans-serif}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6}}
.wrap{{max-width:1040px;margin:0 auto;padding:0 20px}}
header{{background:var(--cedar);color:#F4F0E6;padding:34px 0 30px;margin-bottom:34px}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(1.6rem,4.5vw,2.4rem);line-height:1.15;margin-bottom:10px}}
header p{{color:#C9BCA3;font-size:.98rem;max-width:64ch}}
.eyebrow{{font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;color:#C9BCA3;margin-bottom:12px}}
.stamp{{margin-top:16px;padding-top:12px;border-top:1px solid rgba(201,188,163,.28);
 font-size:.82rem;color:#A99B82;max-width:78ch;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
.ask{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--gold);
 padding:22px 24px;margin-bottom:40px}}
.ask h2{{font-family:var(--serif);font-size:1.25rem;margin-bottom:8px}}
.ask p{{color:var(--dim);font-size:.95rem;max-width:70ch}}
.ask p+p{{margin-top:10px}}
.ask b{{color:var(--ink)}}
section{{margin-bottom:44px;padding-bottom:34px;border-bottom:1px solid var(--line)}}
section:last-of-type{{border-bottom:0}}
h2{{font-family:var(--serif);font-weight:600;font-size:clamp(1.15rem,3vw,1.5rem);margin-bottom:6px}}
.note{{color:var(--dim);font-size:.94rem;max-width:74ch;margin-bottom:16px}}
img{{max-width:100%;height:auto;display:block;border:1px solid var(--line);background:#fff}}
.tag{{display:inline-block;font-size:.65rem;letter-spacing:.14em;text-transform:uppercase;
 color:var(--gold);border:1px solid currentColor;padding:.22em .55em;margin-bottom:10px}}
footer{{padding:30px 0 60px;color:var(--dim);font-size:.86rem}}
footer p+p{{margin-top:8px}}
a{{color:var(--cedar)}}
</style>
</head>
<body>

<header>
  <div class="wrap">
    <p class="eyebrow">Cedarstone Ventures LLC &middot; internal &middot; not indexed, not linked</p>
    <h1>The top of the funnel &mdash; before, and after one merge</h1>
    <p>Three changes have been waiting on one look from you. They are the same decision, so they
       are now one branch and one merge. Nothing below is live. Every picture on this page was
       rendered from the two actual git trees a few seconds before it was written &mdash; left is
       exactly what a stranger sees on deedwell.co right now, right is exactly what they would see
       after the merge.</p>
    <p class="stamp">BEFORE = main @ {before_sha[:7]} &nbsp;&middot;&nbsp; AFTER = feat/top-of-funnel @ {after_sha[:7]}
      &nbsp;&middot;&nbsp; rendered {built}<br>
      Bound to the three files it pictures, not to the branch tips: if any of them has changed
      since, this page says so rather than quietly lying.
      <code>python tools/render_decision_page.py --check</code></p>
  </div>
</header>

<div class="wrap">

  <div class="ask">
    <h2>What is actually being asked</h2>
    <p><b>Yes</b> publishes all three at once. <b>No</b>, or no answer, keeps the site exactly as it is &mdash;
       nothing here can go live by itself.</p>
    <p>This is the last thing standing between us and the first outbound act this company has ever
       made: five landlord trade associations, written and address-verified, offering the free
       checklist as a member benefit. <b>Sending that mail before this merges would spend our one
       first impression on tens of thousands of landlords, hand them a PDF with no way back to us,
       and land them on a page whose first sentence tells them it is for somebody else.</b> That is
       the whole reason the send is gated behind your look rather than the other way round.</p>
    <p>Cost if it is wrong: three pages of copy, revertible with one command, no money and no
       account involved. Cost of it not being seen: the send stays parked.</p>
  </div>
{body}
</div>

<footer>
  <div class="wrap">
    <p>Robots-excluded and linked from nowhere. Delete this directory once the branch is merged or dropped &mdash;
       it is a snapshot of a decision, not a page.</p>
    <p>Gabriel, Office of the CEO &middot; Cedarstone Ventures LLC</p>
  </div>
</footer>

<!-- Cloudflare Web Analytics. Privacy-first: no cookies, no cross-site tracking.
     The token is PUBLIC by design and grants nothing. Every page under the site root
     carries it; build_site_analytics.py --check refuses when one does not. -->
{BEACON}
</body>
</html>
"""


# ---------------------------------------------------------------- freshness

def hashes(paths):
    out = {}
    for p in sorted(paths):
        b = p.read_bytes()
        out[p.name] = {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
    return out


def check():
    mf = OUT / "MANIFEST.json"
    if not mf.exists():
        print(f"decision page: NOT BUILT ({mf} missing)")
        print("  fix: python tools/render_decision_page.py")
        return 1
    m = json.loads(mf.read_text(encoding="utf-8"))
    problems = []
    moved = []

    for key, ref in (("before", m["before_ref"]), ("after", m["after_ref"])):
        if sha_of(ref) is None:
            problems.append(f"{ref} no longer exists - the decision this page pictured "
                            f"is over; delete review/decide/")
            continue
        if sha_of(ref) != m[f"{key}_sha"]:
            moved.append(f"{ref} has moved since the render")
        for path, was in m["pictured"][key].items():
            try:
                now = git("rev-parse", f"{ref}:{path}")
            except subprocess.CalledProcessError:
                problems.append(f"{path} no longer exists on {ref}")
                continue
            if now != was:
                problems.append(f"{path} CHANGED on {ref}; the {key.upper()} side of "
                                f"the pictures showing it is now a lie")

    for name, rec in m["images"].items():
        p = IMG / name
        if not p.exists():
            problems.append(f"{name} is missing")
            continue
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() != rec["sha256"]:
            problems.append(f"{name} was edited by hand after the build")

    if problems:
        print("decision page: STALE")
        for x in problems:
            print("  -", x)
        print("  fix: python tools/render_decision_page.py   (or delete review/decide/ if merged)")
        return 1
    print(f"decision page: fresh - {m['before_ref']}@{m['before_sha'][:7]} vs "
          f"{m['after_ref']}@{m['after_sha'][:7]}, {len(m['images'])} images")
    for x in moved:
        # Not a failure. Commits land around this page all day; only a change to a file
        # it actually pictures can make it lie.
        print(f"  (note) {x}, but every pictured file is byte-identical - still true)")
    return 0


# ---------------------------------------------------------------- build

def build():
    before_sha, after_sha = sha_of(BEFORE_REF), sha_of(AFTER_REF)
    if not before_sha or not after_sha:
        print(f"FAIL: need both {BEFORE_REF} and {AFTER_REF}")
        return 1
    if before_sha == after_sha:
        print("FAIL: the two refs are the same commit - there is no decision to render")
        return 1

    failures = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bdir = export(BEFORE_REF, td / "before")
        adir = export(AFTER_REF, td / "after")
        bsrv, bport = serve(bdir)
        asrv, aport = serve(adir)
        try:
            pairs, texts, pages = asyncio.run(shots(bport, aport, failures))
        finally:
            bsrv.shutdown()
            asrv.shutdown()

        # ---- the PDF, from the real bytes of each tree
        needle = "deedwell.co/updates"
        btexts = pdf_pages_text(bdir / PDF_REL)
        atexts = pdf_pages_text(adir / PDF_REL)
        idx = next((i for i, t in enumerate(atexts) if needle.lower() in t.lower()), None)
        if idx is None:
            failures.append(f"PDF AFTER: no {needle!r} on any page - the capture line did not land")
        if any(needle.lower() in t.lower() for t in btexts):
            failures.append("PDF BEFORE: already carries the capture line - the trees are not different")
        if len(btexts) != len(atexts):
            failures.append(f"PDF: page count moved {len(btexts)} -> {len(atexts)}; "
                            "this was meant to be one added line, not a re-layout")
        if idx is not None and not failures:
            pairs["05_pdf_capture.jpg"] = (pdf_render_page(bdir / PDF_REL, idx),
                                           pdf_render_page(adir / PDF_REL, idx))
            print(f"  PDF change found on page {idx + 1} of {len(atexts)}; both sides rendered from it")

    if failures:
        print("FAIL - nothing written. The renders would not have shown what the page claims:")
        for f in failures:
            print("  -", f)
        return 1

    IMG.mkdir(parents=True, exist_ok=True)
    for name, (b, a) in pairs.items():
        pair(b, a, IMG / name)
        print(f"  wrote {name:26} {(IMG / name).stat().st_size:>8,} B")

    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (OUT / "index.html").write_text(
        render_html(before_sha, after_sha, built, sorted(pairs)), encoding="utf-8")

    (OUT / "MANIFEST.json").write_text(json.dumps({
        "built_utc": built,
        "builder": "tools/render_decision_page.py",
        "before_ref": BEFORE_REF, "before_sha": before_sha,
        "after_ref": AFTER_REF, "after_sha": after_sha,
        "pictured": {"before": blob_ids(BEFORE_REF), "after": blob_ids(AFTER_REF)},
        "images": hashes(IMG.glob("*.jpg")),
    }, indent=2, sort_keys=True), encoding="utf-8")

    # ---- the artifact itself, served and looked at. Writing five JPEGs and an HTML
    # file proves five JPEGs and an HTML file exist; it does not prove the page RENDERS
    # them. A broken relative path here would ship the Chairman a page of empty frames
    # and every check above would still be green.
    shot = asyncio.run(verify_page())
    if shot is None:
        return 1
    print(f"  self-check: page renders, all {len(pairs)} images resolve -> {shot}")

    print(f"\nPASS - {len(pairs)} before/after pairs, every difference positive-controlled.")
    print(f"  BEFORE {BEFORE_REF}@{before_sha[:7]}   AFTER {AFTER_REF}@{after_sha[:7]}")
    print("  https://deedwell.co/review/decide/  (once main is pushed)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="refuse if either ref moved or an image was hand-edited")
    args = ap.parse_args()
    sys.exit(check() if args.check else build())
