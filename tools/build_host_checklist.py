#!/usr/bin/env python3
"""Build the free host checklist PDF served at /files/ and offered on /host/.

Writes files/Deedwell-STR-Turnover-Restock-Checklist.pdf: US Letter, two pages,
print-friendly (black and grey, cedar green accents only, no filled panels that
waste toner). Page 1 is the room-by-room changeover list; page 2 is the restock
tracker and the damage / left-behind log.

Run from the repo root:  python3 tools/build_host_checklist.py

WHY A SCRIPT AND NOT A HAND-MADE PDF. This repo has already paid for a served PDF
whose source was fixed and whose artifact was never rebuilt (see rule 4 and rule 10
in check_promises.py). The copy lives here, the bytes are rebuilt from it, and
`invariant=1` makes the output byte-stable so a no-op rebuild shows no git diff.

ASCII-only SOURCE: non-ASCII characters are written as escapes.

Fonts: Liberation Sans (SIL Open Font License 1.1), copied into tools/fonts/ from
cedarstone-kdp-stack so the build needs nothing outside this repo.

The PDF is registered in check_promises.py FORWARDED_ASSETS as "forwarded": it is
meant to be printed and passed around, so every page carries deedwell.co/host in
the footer as the one route back to us.
"""

import os
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "tools", "fonts")
OUT = os.path.join(ROOT, "files", "Deedwell-STR-Turnover-Restock-Checklist.pdf")
# Page-1 picture shown on /host/ and used as its share card. Rendered FROM the PDF
# on every build, so the picture of the checklist cannot drift from the checklist.
PREVIEW = os.path.join(ROOT, "assets", "host-checklist-p1.jpg")
PREVIEW_W = 800

pdfmetrics.registerFont(TTFont("Sans", os.path.join(FONTS, "LiberationSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Sans-Bold", os.path.join(FONTS, "LiberationSans-Bold.ttf")))

CEDAR = HexColor("#1F3D2F")
INK = HexColor("#1A1A1A")
GREY = HexColor("#5C5C5C")
RULE = HexColor("#9A9A9A")
HAIR = HexColor("#C8C8C8")

W, H = letter                   # 612 x 792 pt
M = 36                          # 0.5 in margin all round
DOT = " \u00b7 "

TITLE = "Short-Term Rental Turnover & Restock Checklist"
FOOTER = ("Deedwell" + DOT + "deedwell.co/host" + DOT + "Free to print and share. "
          "A general checklist; adapt it to your property and local rules.")

# --- page 1 copy --------------------------------------------------------------
HEADER_FIELDS = ["Date", "Unit", "Check-out", "Next check-in", "Cleaner"]

SECTIONS = [
    ("Walk through first (before cleaning)", [
        "Deal with any urgent safety hazard first",
        "Photograph each room as you found it",
        "Note anything damaged, missing or left behind (log on page 2)",
        "Check the trash, fridge and dishwasher for what guests left",
    ]),
    ("Bedrooms", [
        "Strip all beds; check mattress protectors and pillows for stains",
        "Fresh linens on every bed; spare set in the closet",
        "Dust surfaces, lamps and headboards; check under beds",
        "Empty drawers and closets; hangers back in place",
    ]),
    ("Bathrooms", [
        "Clean and disinfect toilet, sink, shower and tub",
        "Clear hair from drains; wipe mirrors and fixtures",
        "Fresh towels set out: ____ bath  ____ hand  ____ washcloths",
        "Refill soap, shampoo, conditioner; at least 2 spare toilet rolls",
    ]),
    ("Kitchen", [
        "Run and empty the dishwasher; put everything back in its place",
        "Wipe counters, stovetop, microwave inside and out",
        "Clear the fridge of guest food; wipe shelves",
        "Check coffee, tea, salt, pepper, oil, dish soap, sponges",
    ]),
    ("Living areas", [
        "Vacuum and mop all floors, including under furniture",
        "Wipe remotes, light switches and door handles",
        "Reset furniture, cushions and throws to your listing photos",
        "Check the Wi-Fi works; house manual and guest book in place",
    ]),
    ("Safety check", [
        "Test smoke and CO alarms (follow the manufacturer's instructions; "
        "check replacement dates)",
        "Fire extinguisher accessible, charged, pin and seal intact",
        "First-aid kit stocked",
        "Exterior lights work; walkways clear",
        "Fix any safety problem before the next check-in",
    ]),
    ("Close out", [
        "Thermostat at your between-stays setting",
        "Windows and doors locked; door code changed if you use codes",
        "Photograph each room again, finished",
        "Message your co-host or next guest about anything that needs follow-up",
    ]),
]
LEFT_SECTIONS = 4               # sections 1-4 in the left column, 5-7 on the right
# /host/ says the safety check is "to initial every turnover", so the section carries a
# real initials line. Change the page copy if this ever goes.
SIGN_OFF = {"Safety check": "Checked by (initials)"}

NOTE = ("Cleaning safety: follow each product's label for gloves, ventilation and "
        "contact time. Never mix cleaning products.")

# --- page 2 copy --------------------------------------------------------------
RESTOCK_ITEMS = [
    "Toilet paper", "Paper towels", "Trash bags", "Dish soap", "Dishwasher tabs",
    "Laundry detergent", "Hand soap", "Shampoo", "Conditioner", "Body wash",
    "Coffee", "Tea", "Sugar", "Sponges", "Light bulbs", "Batteries (alarms, remotes)",
]
RESTOCK_BLANKS = 5
DAMAGE_ROWS = 8


def wrap(text, font, size, width):
    """Greedy word wrap by measured width. Returns a list of lines."""
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w) if cur else w
        if pdfmetrics.stringWidth(trial, font, size) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def checkbox(c, x, y, s=8.5):
    """An empty square, bottom-left at (x, y)."""
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.rect(x, y, s, s, stroke=1, fill=0)


def page_header(c, page_no):
    """Wordmark, title, cedar rule. Returns the y below it."""
    top = H - M
    c.setFillColor(CEDAR)
    c.setFont("Sans-Bold", 15)
    c.drawString(M, top - 15, "Deedwell")
    c.setFont("Sans", 8.5)
    c.setFillColor(GREY)
    c.drawRightString(W - M, top - 13, "Page %d of 2" % page_no)
    c.setFillColor(INK)
    c.setFont("Sans-Bold", 17)
    c.drawString(M, top - 38, TITLE)
    c.setStrokeColor(CEDAR)
    c.setLineWidth(2)
    c.line(M, top - 48, W - M, top - 48)
    return top - 48


def page_footer(c):
    c.setStrokeColor(HAIR)
    c.setLineWidth(0.6)
    c.line(M, M + 14, W - M, M + 14)
    c.setFont("Sans", 7.5)
    c.setFillColor(GREY)
    c.drawString(M, M + 3, FOOTER)


def header_fields(c, y):
    """Date / Unit / Check-out / Next check-in / Cleaner as labelled write-on lines."""
    c.setFont("Sans-Bold", 8.5)
    c.setFillColor(INK)
    # two rows: three fields, then two wider fields
    rows = [HEADER_FIELDS[:3], HEADER_FIELDS[3:]]
    gap = 14
    for r, fields in enumerate(rows):
        base = y - 22 - r * 22
        col_w = (W - 2 * M - gap * (len(fields) - 1)) / len(fields)
        for i, label in enumerate(fields):
            x = M + i * (col_w + gap)
            c.drawString(x, base, label)
            lx = x + pdfmetrics.stringWidth(label, "Sans-Bold", 8.5) + 5
            c.setStrokeColor(RULE)
            c.setLineWidth(0.7)
            c.line(lx, base - 2, x + col_w, base - 2)
    return y - 22 - 22 - 12


def section_block(c, x, y, width, number, title, items, draw=True):
    """One numbered section with checkbox items. Returns the y below it.

    draw=False measures without drawing, so the columns can be balanced first.
    """
    size, lead = 10, 12.6
    if draw:
        c.setFillColor(CEDAR)
        c.circle(x + 7, y - 6.5, 7, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Sans-Bold", 8.5)
        c.drawCentredString(x + 7, y - 9.5, str(number))
        c.setFillColor(CEDAR)
        c.setFont("Sans-Bold", 11)
        c.drawString(x + 19, y - 10.5, title)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.6)
        c.line(x, y - 17, x + width, y - 17)
    y -= 30
    text_x = x + 15
    text_w = width - 15
    for item in items:
        lines = wrap(item, "Sans", size, text_w)
        if draw:
            checkbox(c, x + 1, y - 1)
            c.setFillColor(INK)
            c.setFont("Sans", size)
            for i, ln in enumerate(lines):
                c.drawString(text_x, y + 0.5 - i * lead, ln)
        y -= lead * len(lines) + 7
    sign = SIGN_OFF.get(title)
    if sign:
        y -= 3
        if draw:
            c.setFillColor(INK)
            c.setFont("Sans-Bold", 9)
            c.drawString(text_x, y, sign)
            lx = text_x + pdfmetrics.stringWidth(sign, "Sans-Bold", 9) + 6
            c.setStrokeColor(RULE)
            c.setLineWidth(0.7)
            c.line(lx, y - 2, lx + 70, y - 2)
        y -= 14
    return y - 12


def note_box(c, x, y, width, draw=True):
    size, lead, pad = 9.2, 11.8, 9
    lines = wrap(NOTE, "Sans", size, width - 2 * pad)
    h = pad * 2 + lead * len(lines) - 2
    if draw:
        c.setStrokeColor(CEDAR)
        c.setLineWidth(1)
        c.rect(x, y - h, width, h, stroke=1, fill=0)
        c.setFillColor(INK)
        for i, ln in enumerate(lines):
            if i == 0 and ln.startswith("Cleaning safety:"):
                c.setFont("Sans-Bold", size)
                c.drawString(x + pad, y - pad - size + 1, "Cleaning safety:")
                c.setFont("Sans", size)
                c.drawString(x + pad + pdfmetrics.stringWidth("Cleaning safety: ",
                                                              "Sans-Bold", size),
                             y - pad - size + 1, ln[len("Cleaning safety: "):])
            else:
                c.setFont("Sans", size)
                c.drawString(x + pad, y - pad - size + 1 - i * lead, ln)
    return y - h


def page_one(c):
    y = page_header(c, 1)
    y = header_fields(c, y)
    gutter = 24
    col_w = (W - 2 * M - gutter) / 2
    left_x, right_x = M, M + col_w + gutter
    floor = M + 24                      # nothing may go below the footer rule

    ly = y
    for n, (title, items) in enumerate(SECTIONS[:LEFT_SECTIONS], start=1):
        ly = section_block(c, left_x, ly, col_w, n, title, items)
    ry = y
    for n, (title, items) in enumerate(SECTIONS[LEFT_SECTIONS:], start=LEFT_SECTIONS + 1):
        ry = section_block(c, right_x, ry, col_w, n, title, items)
    ry = note_box(c, right_x, ry, col_w)
    lowest = min(ly, ry)
    if lowest < floor:
        raise SystemExit("page 1 overflows the footer by %.1f pt" % (floor - lowest))
    page_footer(c)


def table(c, y, title, sub, cols, rows, row_h, check_cols=(), yn_cols=()):
    """A ruled table. cols = [(label, width_fraction)]. Returns the y below it."""
    width = W - 2 * M
    c.setFillColor(CEDAR)
    c.setFont("Sans-Bold", 12.5)
    c.drawString(M, y - 14, title)
    if sub:
        c.setFillColor(GREY)
        c.setFont("Sans", 8.5)
        c.drawString(M + pdfmetrics.stringWidth(title, "Sans-Bold", 12.5) + 10, y - 14, sub)
    y -= 22
    xs = [M]
    for _, frac in cols:
        xs.append(xs[-1] + frac * width)
    # header row
    hh = 17
    c.setStrokeColor(CEDAR)
    c.setLineWidth(1.2)
    c.line(M, y, W - M, y)
    c.setFillColor(INK)
    c.setFont("Sans-Bold", 8.5)
    for i, (label, _) in enumerate(cols):
        c.drawString(xs[i] + 5, y - 12, label)
    y -= hh
    c.line(M, y, W - M, y)
    # body rows
    c.setFont("Sans", 9)
    for r, cell in enumerate(rows):
        top = y
        y -= row_h
        c.setFillColor(INK)
        if cell:
            c.drawString(xs[0] + 5, y + (row_h - 9) / 2 + 1.5, cell)
        for ci in check_cols:
            cx = (xs[ci] + xs[ci + 1]) / 2 - 4.25
            checkbox(c, cx, y + (row_h - 8.5) / 2)
        for ci in yn_cols:
            # "Y [ ]  N [ ]" centred in the cell
            mid = (xs[ci] + xs[ci + 1]) / 2
            by = y + (row_h - 8.5) / 2
            c.setFont("Sans", 8.5)
            c.drawString(mid - 27, by + 1, "Y")
            checkbox(c, mid - 18, by)
            c.drawString(mid + 5, by + 1, "N")
            checkbox(c, mid + 15, by)
            c.setFont("Sans", 9)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.6)
        c.line(M, y, W - M, y)
    # column dividers over header and body
    c.setStrokeColor(HAIR)
    c.setLineWidth(0.6)
    body_top = y + row_h * len(rows) + hh
    for x in xs[1:-1]:
        c.line(x, body_top, x, y)
    c.setStrokeColor(CEDAR)
    c.setLineWidth(1.2)
    c.line(M, y, W - M, y)
    return y


def page_two(c):
    y = page_header(c, 2)
    floor = M + 24
    rows = RESTOCK_ITEMS + [""] * RESTOCK_BLANKS
    y = table(c, y - 12, "Restock tracker", "Set a par level once; count what is on hand each turnover.",
              [("Item", 0.46), ("Par level", 0.18), ("On hand", 0.18), ("Reorder?", 0.18)],
              rows, 16.2, check_cols=(3,))
    y = table(c, y - 20, "Damage, missing and left-behind log", None,
              [("Date", 0.12), ("Room", 0.15), ("What", 0.33), ("Photo taken?", 0.15),
               ("Action / reported to", 0.25)],
              [""] * DAMAGE_ROWS, 24.5, yn_cols=(3,))
    if y < floor:
        raise SystemExit("page 2 overflows the footer by %.1f pt" % (floor - y))
    page_footer(c)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    c = canvas.Canvas(OUT, pagesize=letter, invariant=1)
    c.setTitle(TITLE)
    c.setAuthor("Deedwell, a brand of Cedarstone Ventures LLC")
    c.setSubject("Free printable turnover checklist, restock tracker and damage log "
                 "for short-term rental hosts. deedwell.co/host")
    c.setCreator("tools/build_host_checklist.py")
    page_one(c)
    c.showPage()
    page_two(c)
    c.showPage()
    c.save()
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    write_preview()
    return 0


def write_preview():
    """Render page 1 to a JPEG. Needs pymupdf; fails loudly rather than leave the
    preview showing an older checklist than the one that downloads."""
    try:
        import pymupdf
    except ImportError:
        raise SystemExit("pymupdf is required to refresh %s (pip install pymupdf)"
                         % os.path.relpath(PREVIEW, ROOT))
    doc = pymupdf.open(OUT)
    page = doc[0]
    zoom = PREVIEW_W / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    pix.save(PREVIEW, jpg_quality=82)
    print("wrote %s (%dx%d)" % (os.path.relpath(PREVIEW, ROOT), pix.width, pix.height))


if __name__ == "__main__":
    sys.exit(main())
