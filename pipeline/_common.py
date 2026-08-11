"""Shared helpers for the Species Black List pipeline."""
import csv, functools, json, os, re

# --- sentence segmentation -------------------------------------------------------
# Splitting on (?<=[.;])\s+ cuts a sentence wherever the corpus abbreviates a repeated
# genus, which it does whenever two congeners share a range:
#
#   "The Kanabos perch (Badis kanabos) and the Assam perch (B. | assamensis) are both
#    known only from a few localities in the lower Brahmaputra River drainage."
#
# The kept half names the species and states no restriction, so it scored tier 1 while
# the restriction sat in the discarded half. 82 species were mis-tiered this way, a
# third of tier 1, some of them tier 5 ("are each known only from a single specimen").
#
# Two guards: a boundary must be followed by something that can begin a sentence, which
# a lower-case epithet cannot; and the token before the period must not be an
# abbreviation -- a lone initial, or a short form like "St." that IS followed by a
# capital and so survives the first guard.
#
# This lives here rather than in 03 because 03, 04, 07 and 10 all segment the same
# corpus, and 04 is the held-out test. If they disagree, the test scores a classifier
# that is not the one which built the register.
BOUNDARY = re.compile(r"(?<=[.;])\s+(?=[A-Z\"'(“‘])")
ABBREV_END = re.compile(
    r"(?:\b[A-Z]|\b(?:St|Mt|Ste|Dr|Fr|Sr|Jr|Mr|Mrs|Prof|ca|cf|no|nos|var|subsp|"
    r"ssp|approx|et al|spp|sp|fig|figs|pp|vol|Is|Mts))\.$")


def best_evidence(hits, score_fn):
    """Pick the sentence that becomes a species' evidence, tier and quoted record.

    `hits` is [(site, sentence, block_text)]; `score_fn(sentence, block)` returns the
    scorer's tuple whose first element is the tier.

    Ranks by the tier the sentence actually PRODUCES, then by length. The older rule tested
    for "known only|confined to" and otherwise took the longest sentence -- the scorer's
    original vocabulary, frozen while the scorer was widened three times, so selector and
    scorer could disagree about what counts as a restriction. Phrynomedusa bokermanni was
    scored tier 2 from a long sentence shared with another frog while its own account,
    "known only from a single locality in coastal southeast Brazil", sat unread in the same
    block.

    Scoring the candidates and taking the best makes the two consistent by construction, and
    it cannot drift again because there is no second vocabulary left to fall behind.

    This lives here because the rule was duplicated in 03, 04 and twice in 07. Fixing one
    copy made the register disagree with the scorer's own output file, which is worse than
    all four being wrong together.
    """
    return max(hits, key=lambda h: (score_fn(h[1], h[2])[0], len(h[1])))


def sentences(text):
    """Split into sentences without cutting at an abbreviated genus."""
    out, start = [], 0
    for m in BOUNDARY.finditer(text):
        if ABBREV_END.search(text[start:m.start()].rstrip()):
            continue
        out.append(text[start:m.start()])
        start = m.end()
    out.append(text[start:])
    return [x for x in out if x.strip()]


BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "build_2026")

# Taxonomy arrives from three places with three conventions: IUCN shouts its
# class (ACTINOPTERYGII), GBIF sometimes returns a class that is really an order
# (Squamata) or nothing at all for fish, and the recovery paths fall back to
# order.  Left alone, the deliverable's class column mixes all three.  Everything
# is normalised to the eight vertebrate classes below.
CANON = {
    "ACTINOPTERYGII": "Actinopterygii", "ACTINOPTERI": "Actinopterygii",
    "CHONDRICHTHYES": "Chondrichthyes", "ELASMOBRANCHII": "Chondrichthyes",
    "HOLOCEPHALI": "Chondrichthyes", "AMPHIBIA": "Amphibia",
    "REPTILIA": "Reptilia", "SQUAMATA": "Reptilia", "TESTUDINES": "Reptilia",
    "CROCODYLIA": "Reptilia", "RHYNCHOCEPHALIA": "Reptilia",
    "AVES": "Aves", "MAMMALIA": "Mammalia", "MYXINI": "Myxini",
    "PETROMYZONTI": "Petromyzonti", "CEPHALASPIDOMORPHI": "Petromyzonti",
    "SARCOPTERYGII": "Sarcopterygii", "DIPNOI": "Sarcopterygii",
}


@functools.lru_cache(maxsize=1)
def order_to_class():
    """ORDER -> canonical class, learned from the IUCN index rather than hardcoded."""
    out = {}
    with open(os.path.join(BUILD, "iucn_2026_index.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cls = CANON.get(r["class"].upper())
            if cls and r["order"]:
                out.setdefault(r["order"].upper(), cls)
    return out


def normalise_class(value):
    """Map any class-ish or order-ish string onto one vertebrate class."""
    if not value:
        return ""
    # tolerate the "fish (Cypriniformes)" shape used by the NE paths
    v = value.strip().strip(")").split("(")[-1].strip().upper()
    return CANON.get(v) or order_to_class().get(v) or value.strip().title()


@functools.lru_cache(maxsize=1)
def _gbif_cache():
    p = os.path.join(BUILD, "gbif_cache.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def class_for(name, *candidates):
    """Best available class for a species, trying each candidate then GBIF.

    Species recovered by the audits often arrive with no class and no order --
    GBIF returns a class for them but not an order, and the audit output only
    carried order.  Falling back to the cached GBIF record fills those in
    (15 squamates, without this).
    """
    for c in candidates:
        got = normalise_class(c)
        if got:
            return got
    m = _gbif_cache().get(name, {})
    return normalise_class(m.get("class") or m.get("order") or "")
