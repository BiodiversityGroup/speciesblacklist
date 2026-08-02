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

    restriction tier 4-5   10/19 = 52.6% came out threatened   (95% CI 32-73%)
    restriction tier 1-3   18/89 = 20.2%                       (95% CI 13-30%)
    Fisher exact two-sided p = 0.0075,  odds ratio 4.38

So restriction severity does predict IUCN's own verdict, and the tier 4-5 rate
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

BINOMIAL = re.compile(r"\b([A-Z][a-z]{2,})\s+([a-z]{3,})\b")

# --- restriction tiers, strongest first; first match wins -------------------
# R5/R4 are the tiers that plausibly sit inside Criterion B2 thresholds.
TIERS = [
    (5, "type locality / single collection", re.compile(
        r"known only from (its |the )?(original |type )(collection|locality|series|"
        r"specimens?)|only (known )?from a single specimen|known only from the "
        r"holotype|from a single collection|only ever (been )?(collected|recorded) once",
        re.I)),
    (4, "single named site", re.compile(
        r"known only from (a|an|the)?\s*[a-z]*\s*(unnamed )?(single )?"
        r"(river|stream|creek|spring|cave|lake|lagoon|pool|swamp|marsh|waterfall|"
        r"rapids|island|islet|cay|mountain|peak|volcano|massif|valley|forest|"
        r"locality|site|reef)\b|confined to (a|an|the)?\s*[a-z]*\s*"
        r"(river|stream|creek|spring|cave|lake|lagoon|pool|island|islet|mountain|"
        r"peak|volcano|massif|valley|forest)\b", re.I)),
    (3, "single drainage / massif / small island", re.compile(
        r"known only from .{0,40}(drainage|basin|catchment|watershed|system|"
        r"archipelago|range)\b|confined to .{0,40}(drainage|basin|catchment|"
        r"watershed|system|archipelago|range)\b", re.I)),
    (2, "restricted, extent unclear", re.compile(
        r"known only from|confined to|restricted to|endemic to", re.I)),
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
    raw = open(BOOK, encoding="cp1252", errors="replace").read()
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
        for sent in re.split(r"(?<=[.;])\s+", text):
            for g, e in BINOMIAL.findall(sent):
                name = f"{g} {e}"
                if name in live:
                    found[name].append((site, sent, text))

    ev_rows, sc_rows = [], []
    for name, hits in found.items():
        # prefer the mention that carries an explicit restriction statement
        site, sent, text = max(
            hits, key=lambda h: (bool(re.search(r"known only|confined to", h[1], re.I)),
                                 len(h[1])))
        tier, label, silence, threats, protected = score(sent, text)
        meta = live[name]
        ev_rows.append({"species": name, "site": site, "species_sentence": sent,
                        "block_text": text})
        sc_rows.append({
            "species": name, "class": meta["class"], "site": site,
            "restriction_tier": tier, "restriction_basis": label,
            # Tier 4-5 is the validated stratum: 52.6% of reassessed tier 4-5
            # species came out threatened, vs 20.2% for tier 1-3.
            "tranche": "A - validated priority" if tier >= 4 else "B - unranked",
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
    print(f"\n=== tranche A (tier 4-5, validated priority): {a:,} species ===")
    print(f"    tranche B (tier 1-3, needs range work) : {len(sc_rows)-a:,} species")
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
