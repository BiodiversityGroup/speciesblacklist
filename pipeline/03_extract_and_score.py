"""
Re-extract evidence from Richardson (2023) with the book's own structure, then
score each Data Deficient species for geographic-restriction severity.

WHY RE-EXTRACT
The 2024 pipeline kept one sentence per species (median 131 chars).  Mining those
sentences shows 73% say "known only from" and under 1% mention any threat driver
(dams, logging, pollution).  That is not a gap in the book -- it is the book's
structure.  It is organised biogeographically:

      The Luhoho River is located in central-eastern Democratic Republic of Congo.
      The Luhoho yellowfish (Labeobarbus longifilis) ... known only from the Luhoho.
      The Luhoho shellear (Parakneria kissi) is confined to the Luhoho River.

The locality paragraph carries the place and its threats; the species line carries
the restriction.  Keeping only the species line throws away half the evidence, so
here we keep the whole block and record which site each species belongs to.

WHY SCORE ON RESTRICTION RATHER THAN THREAT KEYWORDS
IUCN Criterion B lets a species qualify as threatened on a small range plus
decline/fragmentation: AOO under 2,000 km2 for VU, 500 for EN, 10 for CR.  A
species "known only from its type locality" is prima facie inside the CR envelope
for B2.  That is the strongest defensible claim this corpus can make, so the
primary axis is restriction severity, with site-level threats as a modifier.

VALIDATION RESULT (see 04_validate_score.py; run it before trusting this file)
Tested against the 108 species IUCN independently reassessed between the Sept 2024
export and v2026-1 -- a labelled set these rules never saw:

    restriction tier 3-5   15/28 = 53.6% came out threatened   (95% CI 36-70%)
    restriction tier 1-2   24/111 = 21.6%                      (95% CI 15-30%)
    Fisher exact two-sided p = 0.0017,  odds ratio 4.18

    The tiers are NOT monotonic at the top -- tier 5 (40%) scores below tier 4
    (70%) and tier 3 (67%).  "Known only from a single specimen" measures survey
    effort as much as range size, which is why the boundary sits at 2|3 where the
    real discontinuity is (19.8% -> 66.7%) rather than at the top of the scale.

So restriction severity does agree with IUCN's own verdict, and the tier 3-5 rate
lands on Borgelt et al.'s 56% DD prediction.  The read-across is that the 56%
belongs to the narrowly restricted subset, not to DD species indiscriminately --
a flat DD list dilutes a real signal with vague-range species.

The composite score originally tried here has been REMOVED because validation
killed it: it was non-monotonic (score 4 -> 78% threatened, score 5 -> 17%), and
its modifiers do not carry signal in the direction assumed.  Naming a site-level
threat is *inversely* associated with being threatened (odds ratio 0.56): broad
well-documented regions attract threat prose but hold wide-ranging species, while
a genuine type-locality endemic gets one terse line.  Historical silence was
positive but on n=6 (OR 1.46), far too thin to rank on.  Both are retained below
as descriptive context only.  Ranking is on restriction tier alone.

Outputs: build_2026/evidence_blocks.csv   (species x site x full block text)
         build_2026/scored_dd.csv         (the ranked live black list)
"""
import csv, os, re, collections

csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")
BOOK = os.path.join(PROJ, "Threatened and Recently-Extinct Vertebrates.txt")
# 02a rewrites the corpus with abbreviated genera resolved ("A. leurolepis" ->
# "Abronia leurolepis"). Without it, a species named only in abbreviated form can be in
# the name list yet never match a sentence, so it would score tier 1 by default.
EXPANDED = os.path.join(BUILD, "corpus_expanded.txt")

BINOMIAL = re.compile(r"\b([A-Z][a-z]{2,})\s+([a-z]{3,})\b")

# --- restriction tiers, strongest first; first match wins -------------------
# R5/R4 are the tiers that plausibly sit inside Criterion B2 thresholds.
# Richardson phrases a restriction several ways, and the first version of these
# patterns only covered "known only from" / "confined to". An audit found 37 tier-1
# species that do state a restriction in wording the patterns missed -- 26 of them
# "known for certain only from". KNOWN is that alternation, shared by every tier so
# the phrasings cannot drift apart again.
#
# A second audit pass found 6 more, where the book varies the PREPOSITION or omits it:
# "known only BY a single specimen", "known only IN a small area", "known only two
# localities", "known only its original collection". Rather than keep adding literal
# phrases, KNOWN is now built compositionally: certainty adverbs, then "known", then a
# mandatory "only" (or an explicit certainty phrase), then an optional preposition.
#
# "only" or a certainty phrase is REQUIRED. A bare "is known from the Amazon basin" is
# not a restriction statement, and matching it would collapse tier 2 into a catch-all.
# The prepositionless branch is safe here because only 3 sentences in the corpus use it
# and all 3 are genuine restrictions; "in|at|by|from" excludes "known only TO occur",
# which is why "is only known to occur seasonally" does not match.
CERT = r"(?:for certain|with certainty|definitely|reliably|long)"
PREP = r"(?:from|by|in|at)"
KNOWN = (r"(?:"
         r"only\s+(?:" + CERT + r"\s+)*known\s+" + PREP +
         r"|(?:" + CERT + r"\s+)*known(?:\s+" + CERT + r")*\s+only(?:\s+" + PREP + r")?"
         r"|known\s+(?:for certain|with certainty)(?:\s+" + PREP + r")?"
         r")")

# ORDER MATTERS: first match wins, and the order is 5, 3, 4, 2 -- not 5, 4, 3, 2.
#
# Tier 4's alternation contains "river", and it used to be tested before tier 3, so
# "confined to the Kapuas River drainage" -- a basin the size of a country -- scored as
# "a single named site". 73 species were classified against the published tier table that
# way. Testing the drainage qualifier first fixes it.
#
# But a drainage can also be mere CONTEXT for a genuine single site: "known only from a
# single locality within the Ganges River drainage" is tier 4, and 29 species read like
# that. So tier 3's pattern is tempered -- it refuses to match across the words "single"
# or "localit" -- which keeps the scale noun as the head of the restriction rather than
# something merely mentioned later in the sentence.
TIERS = [
    (5, "type locality / single collection", re.compile(
        KNOWN + r" (its |the )?(original |type )(collection|locality|series|"
        r"specimens?)|only (known )?from a single specimen|" + KNOWN +
        r" the holotype|from a single collection|"
        r"only ever (been )?(collected|recorded) once|"
        r"from (?:a|the) single (?:specimen|collection|individual)|"
        # a single collection EVENT, however the preposition falls ("known only by a
        # single specimen"). A single *locality* is tier 4 -- one named site, not one
        # collection -- so it is deliberately absent from this list.
        + KNOWN + r"\s+(?:a|the)?\s*single (?:specimen|individual|collection|series)",
        re.I)),
    (3, "single drainage / massif / small island", re.compile(
        r"(?:" + KNOWN + r"|confined to|restricted to)"
        # tempered: may not run across a single-site phrase, so "a single locality
        # within the Ganges River drainage" stays tier 4 rather than becoming tier 3
        r"(?:(?!\bsingle\b|\blocalit)[^.]){0,40}?"
        r"\b(?:drainage|basin|catchment|watershed|system|archipelago|ranges?)\b", re.I)),
    # The slot before the feature noun holds exactly ONE word, and that is deliberate.
    #
    # It looks like a bug: a multi-word place name ("the Suoi Rut stream", "La Quebradona
    # creek") does not match, so four genuine single-site endemics sit in tier 2. Widening
    # the slot to three words was tried, and the held-out set rejected it. It moved 94
    # species from tier 2 into tier 4, of which 7 were in the labelled set and only 1 came
    # out threatened -- so the priority stratum fell from 15/28 = 53.6% to 16/35 = 45.7%,
    # OR 4.23 -> 3.00, p 0.0016 -> 0.0091.
    #
    # The single token is therefore doing real work rather than accidentally restricting
    # the match: a bare "the <Name> River" is a tighter claim than a qualified phrase, and
    # loosening it admits species that behave statistically like tier 2. The four misses
    # are recorded as a known limitation instead of being fixed at that cost.
    (4, "single named site", re.compile(
        KNOWN + r" (a|an|the)?\s*[a-z]*\s*(unnamed )?(single )?"
        r"(river|stream|creek|spring|cave|lake|lagoon|pool|swamp|marsh|waterfall|"
        r"rapids|island|islet|cay|mountain|peak|volcano|massif|valley|forest|"
        r"locality|site|reef)\b|confined to (a|an|the)?\s*[a-z]*\s*"
        r"(river|stream|creek|spring|cave|lake|lagoon|pool|island|islet|mountain|"
        r"peak|volcano|massif|valley|forest)\b", re.I)),
    (2, "restricted, extent unclear", re.compile(
        KNOWN + r"|confined to|restricted to|endemic to|"
        r"known from (?:a )?few localities", re.I)),
]

# --- modifiers --------------------------------------------------------------
SILENCE = re.compile(
    r"not (been )?(recorded|seen|collected|found|reported) (since|for|in)|"
    r"last (recorded|seen|collected|reported)|no (recent |further )?(records|"
    r"sightings|specimens)|(may|might|possibly|could|feared|presumed) be extinct|"
    r"in the (18|19)\d0s\b|original collection in", re.I)

THREATS = {
    "dam/hydro":      re.compile(r"\bdam(s|med|ming)?\b|hydroelectric|impound|reservoir|diverted", re.I),
    "deforestation":  re.compile(r"deforest|logging|logged|timber|clear.?cut|clearance of", re.I),
    "agriculture":    re.compile(r"agricultur|cultivat|plantation|grazing|pasture|oil palm|converted to", re.I),
    "pollution":      re.compile(r"pollut|siltation|sediment|effluent|contaminat|sewage|runoff|acidif", re.I),
    "mining":         re.compile(r"\bmining\b|\bmines?\b|quarr|dredg|gold.?panning", re.I),
    "invasive":       re.compile(r"invasive|introduced (species|fish|predator|trout|tilapia)|non-native|feral", re.I),
    "harvest":        re.compile(r"\bhunt|poach|bushmeat|overfish|fished|collected for|pet trade|aquarium trade", re.I),
    "development":    re.compile(r"urban|settlement|road construction|tourism|drained|drainage of|reclaim", re.I),
    "climate/drought":re.compile(r"drought|climate change|desiccat|dried up|water table", re.I),
}

PROTECTED = re.compile(
    r"national park|nature reserve|wildlife (reserve|sanctuary|refuge)|"
    r"protected area|world heritage|conservation area", re.I)


def blocks():
    """Yield (site_header, block_text) for every paragraph block in the book."""
    src = EXPANDED if os.path.exists(EXPANDED) else BOOK
    raw = open(src, encoding="cp1252", errors="replace").read()
    raw = raw.replace("’", "'").replace("�", "'")
    for blk in re.split(r"\n\s*\n", raw):
        lines = [ln.strip() for ln in blk.split("\n") if ln.strip()]
        if not lines:
            continue
        text = " ".join(lines)
        # A locality header introduces a place rather than a species: it has no
        # parenthetical binomial and reads "X is located in / X is a ...".
        head = lines[0]
        is_header = ("(" not in head) and re.search(
            r"\bis (located|a|an|the|situated|found)\b|\blies\b|\brefers to\b", head)
        yield (site_name(head) if is_header else ""), text


def site_name(header):
    """Reduce a locality paragraph's opening line to just the place name."""
    m = re.match(r"^(.{3,80}?)\s+(?:is|are|lies|comprises|covers|extends|refers|"
                 r"literally|occupy|occupies|still)\b", header)
    return (m.group(1) if m else header[:80]).strip().rstrip(",")


def score(species_line, block_text):
    tier, tier_label = 1, "no restriction statement"
    for t, label, pat in TIERS:
        if pat.search(species_line):
            tier, tier_label = t, label
            break
    silence = bool(SILENCE.search(species_line))
    threats = sorted(k for k, p in THREATS.items() if p.search(block_text))
    protected = bool(PROTECTED.search(block_text))
    # Descriptive only -- validation showed these do not rank (see module docstring).
    return tier, tier_label, silence, threats, protected


import sys; sys.path.insert(0, HERE)
from _common import sentences, best_evidence  # shared so 04's held-out test segments
                               # the corpus exactly as this scorer does


def main():
    live = {}
    with open(os.path.join(BUILD, "crossref_2026.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["cat_2026"] == "DD":
                live[r["book_name"]] = r
    print(f"live DD species to score: {len(live):,}")

    # Walk the book once, attaching each species mention to its site and block.
    found = collections.defaultdict(list)
    for site, text in blocks():
        for sent in sentences(text):
            for g, e in BINOMIAL.findall(sent):
                name = f"{g} {e}"
                if name in live:
                    found[name].append((site, sent, text))

    ev_rows, sc_rows = [], []
    for name, hits in found.items():
        # Rank candidate sentences by the tier they actually produce, then by length.
        #
        # This used to test for "known only|confined to" and otherwise take the longest
        # sentence. That test was the scorer's ORIGINAL vocabulary, frozen while the scorer
        # itself was widened three times, so selector and scorer could disagree about what
        # counts as a restriction. An audit found the consequence: Phrynomedusa bokermanni
        # was scored tier 2 from a long sentence shared with another frog, while its own
        # account -- "known only from a single locality in coastal southeast Brazil", tier 4
        # -- sat unread in the same block.
        #
        # Scoring every candidate and taking the best makes the two consistent by
        # construction rather than by coincidence, and it cannot drift again: there is no
        # second vocabulary left to fall behind.
        site, sent, text = best_evidence(hits, score)
        tier, label, silence, threats, protected = score(sent, text)
        meta = live[name]
        ev_rows.append({"species": name, "site": site, "species_sentence": sent,
                        "block_text": text})
        sc_rows.append({
            "species": name, "class": meta["class"], "site": site,
            "restriction_tier": tier, "restriction_basis": label,
            # Tier 3-5 is the validated stratum: on the held-out set it scores 15/28 = 53.6%
            # threatened (OR 4.18, p 0.0017), beating tier 4-5 (OR 3.67, p 0.0060) on
            # every measure. The per-tier break is at 2|3 (19.8% -> 66.7%), not 3|4.
            "tranche": "A - validated priority" if tier >= 3 else "B - unranked",
            "historical_silence": "yes" if silence else "no",
            "site_threats": "|".join(threats),
            "in_protected_area": "yes" if protected else "no",
            "species_sentence": sent})

    missing = sorted(set(live) - set(found))
    print(f"matched in book text: {len(found):,} | unmatched: {len(missing):,}")

    sc_rows.sort(key=lambda r: (-r["restriction_tier"], r["class"], r["species"]))
    for fn, rows in (("evidence_blocks.csv", ev_rows), ("scored_dd.csv", sc_rows)):
        with open(os.path.join(BUILD, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("\n=== restriction tier distribution ===")
    for t, n in sorted(collections.Counter(r["restriction_tier"] for r in sc_rows).items(),
                       reverse=True):
        lab = next(x[1] for x in TIERS if x[0] == t) if t > 1 else "no restriction statement"
        print(f"  tier {t}: {n:5d}   {lab}")
    a = sum(1 for r in sc_rows if r["tranche"].startswith("A"))
    print(f"\n=== tranche A (tier 3-5, validated priority): {a:,} species ===")
    print(f"    tranche B (tier 1-2, needs range work) : {len(sc_rows)-a:,} species")
    print(f"\nhistorical silence flagged: "
          f"{sum(1 for r in sc_rows if r['historical_silence']=='yes'):,}")
    print(f"site threat named        : {sum(1 for r in sc_rows if r['site_threats']):,}")
    print(f"inside a protected area  : "
          f"{sum(1 for r in sc_rows if r['in_protected_area']=='yes'):,}")

    sites = collections.Counter(r["site"] for r in sc_rows if r["site"])
    print("\n=== sites carrying the most live-DD species ===")
    for s, n in sites.most_common(12):
        print(f"  {n:3d}  {s[:95]}")


if __name__ == "__main__":
    main()
