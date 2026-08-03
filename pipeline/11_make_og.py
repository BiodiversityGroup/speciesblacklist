"""
Draw the shared-link preview card, site/og-image.png, at 1200x630.

The advocacy case for this register travels by link, so the card is the first --
often the only -- thing a reader sees.  It is drawn rather than photographed for
the same reason the page carries no photography: most of these animals have
never been photographed, and that absence is the subject.  A stock parrot would
argue the opposite of what the register says.

So the card is the register itself, in miniature: the ruled masthead, one real
tier-5 record set in monospace, the field of 2,408 marks coloured by the same
restriction ramp the page uses, and the four headline figures.  Every number and
every mark is read out of site/data.json at draw time -- nothing here is typed in
by hand -- so the card cannot quietly go stale when IUCN publishes and the
pipeline reruns.  The colours are the :root tokens from index.html, light theme.

Run after 10_build_site.py.  Outputs: site/og-image.png
Requires: Pillow, and the Windows core fonts (Georgia / Consolas / Segoe UI)
that index.html names first in each of its font stacks.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SITE = os.path.join(PROJ, "site")
OUT = os.path.join(SITE, "og-image.png")

# The record to feature.  A tier-5, never-assessed bird: it carries both blind
# spots at once -- one specimen, and no IUCN assessment to speak for it -- and a
# bird lands with readers who would scroll past another combtooth blenny.
FEATURE = "Caprimulgus centralasicus"

W, H, PAD = 1200, 630, 56
CW = W - 2 * PAD

# ---- tokens, lifted from :root in index.html (light theme) -----------------
GROUND, SURFACE = "#EDEEF0", "#F7F8F9"
INK, INK2, INK3 = "#171A21", "#4A5260", "#767E8C"
RULE, RULE2, ACCENT = "#D3D7DE", "#C0C6D0", "#3B4E8C"
TIER = {1: "#D9C08A", 2: "#C99B4F", 3: "#B4762B", 4: "#90501A", 5: "#6B300F"}

FONTS = "C:/Windows/Fonts/"


def serif(sz, bold=False):
    return ImageFont.truetype(FONTS + ("georgiab.ttf" if bold else "georgia.ttf"), sz)


def mono(sz, bold=False):
    return ImageFont.truetype(FONTS + ("consolab.ttf" if bold else "consola.ttf"), sz)


def sans(sz, weight="r"):
    face = {"r": "segoeui.ttf", "sb": "seguisb.ttf", "b": "segoeuib.ttf"}[weight]
    return ImageFont.truetype(FONTS + face, sz)


def ls_width(text, font, track=0.0):
    """Width of text drawn with `track` px of extra space after each glyph."""
    return sum(font.getlength(c) + track for c in text) - (track if text else 0)


def ls_text(d, xy, text, font, fill, track=0.0):
    """Draw with letter-spacing.  Pillow has no tracking, so step per glyph."""
    x, y = xy
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += font.getlength(c) + track


def eyebrow(d, xy, text, size=12, fill=INK3):
    """.eyebrow from index.html: sans semibold, uppercase, .13em tracking."""
    ls_text(d, xy, text.upper(), sans(size, "sb"), fill, track=size * 0.13)


def wrap(text, font, width, limit):
    """Greedy wrap to `width` px.  Raises if it needs more than `limit` lines --
    a silently overflowing label is worse than a failed build."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.getlength(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > limit:
        raise SystemExit(f"og card: {text!r} needs {len(lines)} lines, {limit} allowed")
    return lines


def balanced(text, font, width, limit):
    """Wrap without orphans: same line count as a greedy wrap to `width`, but
    set to the narrowest measure that still achieves it, which evens the lines.
    Greedy alone leaves things like a lone 'century.' on the second line."""
    n = len(wrap(text, font, width, limit))
    lo, hi = 1, int(width)
    while lo < hi:
        mid = (lo + hi) // 2
        try:
            fits = len(wrap(text, font, mid, n)) <= n
        except SystemExit:
            fits = False
        hi, lo = (mid, lo) if fits else (hi, mid + 1)
    return wrap(text, font, lo, n)


data = json.load(open(os.path.join(SITE, "data.json"), encoding="utf-8"))
meta, species = data["meta"], data["species"]
c, v = meta["counts"], meta["validation"]

img = Image.new("RGB", (W, H), GROUND)
d = ImageDraw.Draw(img)

# ---- masthead: a register header, ruled ------------------------------------
MAST_H = 80
d.rectangle([0, 0, W, MAST_H], fill=SURFACE)
d.rectangle([0, MAST_H, W, MAST_H + 2], fill=INK)          # .mast border-bottom

f_eb = sans(13, "sb")
ls_text(d, (PAD, 33), "THE BIODIVERSITY GROUP", f_eb, ACCENT, track=13 * 0.13)
right = f"IUCN RED LIST v{meta['redlist_version'].replace('-', chr(0x2011))}  \u00b7  RICHARDSON 2023"
ls_text(d, (W - PAD - ls_width(right, f_eb, 13 * 0.13), 33), right, f_eb, INK3, track=13 * 0.13)

# ---- title -----------------------------------------------------------------
ls_text(d, (PAD, 110), "The Species Black List", serif(62, bold=True), INK, track=-62 * 0.025)

# ---- lede ------------------------------------------------------------------
f_lede = serif(21)
lede = ("Vertebrates the IUCN Red List cannot yet speak for \u2014 ranked by how "
        "narrowly restricted the record says they are.")
d.text((PAD, 194), wrap(lede, f_lede, CW, 1)[0], font=f_lede, fill=INK2)

# ---- featured evidence: a real record, monospace, ruled in its tier colour --
rec = next(s for s in species if s["n"] == FEATURE)
EV_TOP, EV_BOT = 236, 310
d.rectangle([PAD, EV_TOP, PAD + 3, EV_BOT], fill=TIER[4])
ex = PAD + 20
f_ev = mono(17)
for i, line in enumerate(balanced(rec["e"], f_ev, CW - 20, 2)):
    d.text((ex, EV_TOP + 1 + i * 25), line, font=f_ev, fill=INK)
status = "never assessed by IUCN" if rec["l"] == "ne" else "IUCN: Data Deficient"
eyebrow(d, (ex, EV_TOP + 57),
        f"{rec['c']}  \u00b7  {status}  \u00b7  tier {rec['t']}, most restricted", 12)

# ---- the field: one mark per species, the whole register -------------------
# Same construction as drawField() on the page -- species in register order,
# square marks, one colour per tier -- flattened to a band that fits the card.
FIELD_TOP = 356
eyebrow(d, (PAD, FIELD_TOP - 24), "Every species in the register, one mark each", 12)

f_leg = sans(12)
lo_lab, hi_lab = "less restricted", "known from one place"
RAMP = 5 * 13 - 4          # five 10px swatches on a 13px pitch
lx = W - PAD - (f_leg.getlength(lo_lab) + 10 + RAMP + 10 + f_leg.getlength(hi_lab))
d.text((lx, FIELD_TOP - 25), lo_lab, font=f_leg, fill=INK3)
sx = lx + f_leg.getlength(lo_lab) + 10
for t in (1, 2, 3, 4, 5):
    d.rectangle([sx + (t - 1) * 13, FIELD_TOP - 23,
                 sx + (t - 1) * 13 + 9, FIELD_TOP - 14], fill=TIER[t])
d.text((sx + RAMP + 10, FIELD_TOP - 25), hi_lab, font=f_leg, fill=INK3)

PITCH, GAP = 6, 1
cols, size = CW // PITCH, PITCH - GAP
for i, s in enumerate(species):
    x = PAD + (i % cols) * PITCH
    y = FIELD_TOP + (i // cols) * PITCH
    d.rectangle([x, y, x + size - 1, y + size - 1], fill=TIER.get(s["t"], TIER[1]))
rows = -(-len(species) // cols)
FIELD_BOT = FIELD_TOP + rows * PITCH

# ---- headline figures: the .counts row, same numbers, same wording ---------
C_TOP = FIELD_BOT + 26
C_BOT = C_TOP + 104
cells = [
    (f"{c['dd']:,}", "Data Deficient \u2014 IUCN looked, and could not say"),
    (f"{c['priority_dd']:,}", "of those in the priority stratum (tier 4\u20135)"),
    (f"{c['ne']}", "never assessed by IUCN at all"),
    (f"{v['high']['rate']}%", "of reassessed priority species proved threatened"),
]
d.rectangle([PAD, C_TOP, PAD + CW - 1, C_BOT], fill=RULE)   # 1px gutters show through
colw = (CW - 3) / 4
f_num, f_lab = mono(33, bold=True), sans(13)
for i, (num, lab) in enumerate(cells):
    x0 = PAD + round(i * (colw + 1))
    d.rectangle([x0, C_TOP + 1, x0 + round(colw) - 1, C_BOT - 1], fill=SURFACE)
    ls_text(d, (x0 + 17, C_TOP + 16), num, f_num, INK, track=-33 * 0.02)
    for j, line in enumerate(balanced(lab, f_lab, round(colw) - 34, 2)):
        d.text((x0 + 17, C_TOP + 62 + j * 18), line, font=f_lab, fill=INK2)
d.rectangle([PAD, C_TOP, PAD + CW - 1, C_BOT], outline=RULE2, width=1)

# ---- footer ----------------------------------------------------------------
FOOT = C_BOT + 22
d.text((PAD, FOOT), "speciesblacklist.org", font=sans(15, "sb"), fill=ACCENT)
f_fine = sans(13)
fine = f"{len(species):,} species  \u00b7  open data, CC BY 4.0"
d.text((W - PAD - f_fine.getlength(fine), FOOT + 1), fine, font=f_fine, fill=INK3)

if FOOT + 20 >= H:
    raise SystemExit(f"og card: content runs past the canvas (footer at {FOOT})")

img.save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  {img.size[0]}x{img.size[1]}  "
      f"{os.path.getsize(OUT) / 1024:.0f} KB  "
      f"field {rows} rows x {cols} cols for {len(species):,} species")
