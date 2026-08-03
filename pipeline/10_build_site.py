"""
Build the public site payload from the verified lists.

Emits site/data.json -- everything the page needs in one request.  A static site is
the right architecture here: the data changes twice a year when IUCN publishes, it
is under 2,400 records, and a static file needs no database, no application server
and no authentication surface.  It also survives a traffic spike, which matters if
the list ever gets press.

Common names are recovered from the evidence sentences.  Richardson writes them in
a fixed form -- "The Luhoho shellear (Parakneria kissi) is confined to..." -- so the
vernacular is sitting in the text we already extracted, and a register that shows
only binomials is needlessly hostile to non-taxonomists.

Outputs: site/data.json
         site/index.html is hand-authored, not generated
"""
import csv, json, os, re, sys, collections, importlib.util

csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")
SITE = os.path.join(PROJ, "site")
BOOK = os.path.join(PROJ, "Threatened and Recently-Extinct Vertebrates.txt")

# "The Marsa el At combtooth blenny (Adelotremus leptus) is known only from ..."
VERNACULAR = re.compile(r"([A-Z][^()]{2,70}?)\s*\(([A-Z][a-z]+ [a-z]+)\)")

# --- site metadata ----------------------------------------------------------
# The bare site strings were unusable on their own. Three separate faults:
#
#   * '“Miombo”' kept the book's curly quotes, because Richardson is
#     *defining* the word, not naming a place.
#   * 'Terra firma', 'The cerrado', 'Lowland rainforests' are habitat TYPES that
#     the extractor treated as localities. They are still useful groupings but
#     must not be presented as places you could go and survey.
#   * 'Espiritu Santo', 'Luzon', 'Palawan', 'Manus' are real places whose names
#     are ambiguous worldwide.
#
# The fix for the last one is deliberately NOT to attach country names myself --
# inferring geography is how you end up confidently placing Espiritu Santo in the
# wrong ocean. Richardson's own opening sentence almost always says where it is
# ("Espiritu Santo is the largest of the Vanuatu Islands"), so that sentence is
# carried through as the site's context line and the reader gets the source's
# words rather than my inference.

# A block that defines a term is describing a habitat, not naming a locality.
HABITAT_DEF = re.compile(
    r"literally means|is the vernacular word|refers to (a |the )?(type|kind|forest|"
    r"woodland|habitat|vegetation)|is a (type|kind|term|word|name for a)|"
    r"are characterized by|is the term|denotes", re.I)
# Names that are plainly a habitat rather than a place, even without a definition.
HABITAT_NAME = re.compile(
    r"^(the )?(terra firma|cerrado|caatinga|miombo|campo|chaco|p[aá]ramo|"
    r"lowland rainforests?|scattered patches|montane forests?|mangroves?|"
    r"cloud forests?|dry forests?|coastal forests?|savanna)", re.I)


def clean_site(name):
    """Strip the book's quotation marks and stray leading clauses off a site name."""
    n = (name or "").strip()
    n = n.strip("“”‘’\"'")
    # 'Located in the southeastern Philippines, Mindanao' -> 'Mindanao'
    m = re.match(r"^(?:Located|Situated|Lying|Found)\b[^,]*,\s*(.+)$", n, re.I)
    if m:
        n = m.group(1).strip()
    return n.strip().rstrip(",")


def first_sentence(block_text, site):
    """Richardson's opening sentence for a locality: the geographic context."""
    for sent in re.split(r"(?<=[.;])\s+", block_text):
        s = " ".join(sent.split())
        # skip the sentence if it is really a species record
        if "(" in s and re.search(r"\([A-Z][a-z]+ [a-z]+\)", s):
            continue
        if len(s) > 20:
            return s
    return ""


def build_site_meta():
    """raw site string -> {name, context, habitat} using the book's own prose."""
    spec = importlib.util.spec_from_file_location(
        "extract", os.path.join(HERE, "03_extract_and_score.py"))
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)
    meta = {}
    for site, text in ex.blocks():
        if not site or site in meta:
            continue
        ctx = first_sentence(text, site)
        name = clean_site(site)
        habitat = bool(HABITAT_DEF.search(ctx)) or bool(HABITAT_NAME.match(name))
        meta[site] = {"name": name, "context": ctx, "habitat": habitat}
    return meta


def vernacular_for(binomial, sentence):
    for m in VERNACULAR.finditer(sentence or ""):
        if m.group(2) == binomial:
            name = m.group(1).strip().rstrip(",")
            # strip a leading article so names sort and read cleanly
            name = re.sub(r"^(The|A|An)\s+", "", name)
            # a run-on clause is not a common name
            if len(name) < 60 and " is " not in name and " and " not in name:
                return name
    return ""


def rows(fn):
    p = os.path.join(BUILD, fn)
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def main():
    os.makedirs(SITE, exist_ok=True)

    species = []
    for r in rows("SPECIES_BLACK_LIST_dd.csv"):
        species.append({
            "n": r["book_name"],
            "v": vernacular_for(r["book_name"], r["evidence"]),
            "c": r["class"],
            "t": int(r["restriction_tier"]),
            "b": r["restriction_basis"],
            "s": r["site"],
            "e": r["evidence"],
            "l": "dd",
            "iucn": r.get("verified_iucn_name") or r.get("iucn_name") or r["book_name"],
            # descriptive only -- these did NOT validate as predictors
            "sil": r.get("historical_silence") == "yes",
            "thr": [x for x in (r.get("site_threats") or "").split("|") if x],
            "pa": r.get("in_protected_area") == "yes",
        })
    for r in rows("SPECIES_BLACK_LIST_ne.csv"):
        species.append({
            "n": r["book_name"], "v": vernacular_for(r["book_name"], r["evidence"]),
            "c": r["class"], "t": int(r["restriction_tier"]),
            "b": r["restriction_basis"], "s": r["site"], "e": r["evidence"],
            "l": "ne", "iucn": r.get("accepted_name") or r["book_name"],
            "sil": False, "thr": [], "pa": False,
        })

    named = sum(1 for s in species if s["v"])
    print(f"species: {len(species):,}  (common name recovered for {named:,})")

    # Rewrite each species' site to its cleaned display name so the register and
    # the sites page agree, and so a filter on one matches the other.
    smeta = build_site_meta()
    for s in species:
        m = smeta.get(s["s"])
        s["s"] = m["name"] if m else clean_site(s["s"])
        s["sk"] = "block" if s["s"] else ""

    # Script 03 only records a locality when the species sits inside one of
    # Richardson's locality-headed paragraphs. That left 81% of the register with no
    # locality even though the place is named in the species' own sentence. Recover
    # those from the evidence text -- extraction from the source, never geocoding.
    sys.path.insert(0, HERE)
    from _locality import locality_from_evidence
    recovered = 0
    for s in species:
        if s["s"]:
            continue
        name, kind = locality_from_evidence(s["e"], s.get("v", ""), s["n"])
        if name:
            s["s"], s["sk"] = name, "inline"
            recovered += 1
    have = sum(1 for s in species if s["s"])
    print(f"localities: {have-recovered:,} from locality paragraphs "
          f"+ {recovered:,} recovered from evidence sentences = {have:,} "
          f"({100*have/len(species):.0f}% of the register)")

    sites = collections.Counter(s["s"] for s in species if s["s"])
    inline_share = collections.Counter(s["s"] for s in species
                                       if s["s"] and s["sk"] == "inline")
    # collapse the metadata onto cleaned names
    by_name = {}
    for raw, m in smeta.items():
        by_name.setdefault(m["name"], m)
    payload = {
        "meta": {
            "redlist_version": "2026-1",
            "redlist_accessed": "2026-07-28",
            "corpus": "Richardson, M. (2023) Threatened and Recently Extinct "
                      "Vertebrates of the World: A Biogeographic Approach. "
                      "Cambridge University Press.",
            "built": "2026-08-02",
            "counts": {
                "dd": sum(1 for s in species if s["l"] == "dd"),
                "ne": sum(1 for s in species if s["l"] == "ne"),
                # DD-only priority is the figure to quote beside the validation
                # rate, because the held-out test was run on DD species alone.
                "priority_dd": sum(1 for s in species
                                   if s["t"] >= 4 and s["l"] == "dd"),
                "priority_all": sum(1 for s in species if s["t"] >= 4),
                "prehistoric": len(rows("prehistoric_extinctions.csv")),
            },
            # the held-out test from script 04 -- the site must show this honestly
            "validation": {
                "n_labelled": 108,
                "high": {"n": 19, "threatened": 10, "rate": 52.6, "lo": 32, "hi": 73},
                "low": {"n": 89, "threatened": 18, "rate": 20.2, "lo": 13, "hi": 30},
                "all": {"n": 108, "rate": 25.9, "lo": 19, "hi": 35},
                "p": 0.0075, "odds_ratio": 4.38,
                "baseline_all_species": 28,
                "borgelt_prediction": 56,
            },
        },
        "tiers": {
            5: "Type locality, original collection, or a single specimen",
            4: "A single named site — one river, cave, spring, island, massif",
            3: "A single drainage, archipelago, or mountain range",
            2: "Restricted, extent unclear",
            1: "No restriction statement",
        },
        "classes": dict(collections.Counter(s["c"] for s in species).most_common()),
        "tier_counts": dict(sorted(collections.Counter(
            s["t"] for s in species).items(), reverse=True)),
        # Each site carries the book's own opening sentence as context, so an
        # ambiguous name like "Espiritu Santo" is disambiguated by the source
        # rather than by inference, and habitat types are labelled as such.
        "sites": [{"name": n, "count": c,
                   "context": (by_name.get(n) or {}).get("context", ""),
                   "habitat": bool((by_name.get(n) or {}).get("habitat")),
                   # how many of this site's species were recovered from their own
                   # evidence sentence rather than a locality paragraph
                   "inline": inline_share.get(n, 0)}
                  for n, c in sites.most_common() if c >= 3],
        "species": sorted(species, key=lambda s: (-s["t"], s["c"], s["n"])),
    }

    out = os.path.join(SITE, "data.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {out}  ({os.path.getsize(out)/1024:.0f} KB)")
    print(f"  classes    : {payload['classes']}")
    print(f"  tier counts: {payload['tier_counts']}")
    print(f"  sites >=3  : {len(payload['sites'])}")


if __name__ == "__main__":
    main()
