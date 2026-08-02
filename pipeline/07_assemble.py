"""
Assemble the final Species Black List from the audited components.

Two lists come out of this pipeline, and they make different claims:

  LIST 1 -- Data Deficient.  IUCN has assessed these and returned "we don't know".
            Ranked by restriction tier; tranche A (tier 4-5) is the validated
            stratum where 52.6% of reassessed species came out threatened.
            Includes species recovered from the NE audit that turned out to be
            DD under a genus IUCN has since renamed -- they were invisible to the
            original name-match but are black list members like any other.

  LIST 2 -- Not Evaluated.  IUCN has never assessed these at all, yet a Cambridge
            University Press reference treats them as threatened or recently
            extinct.  Smaller, and the harder claim to make, so it is the more
            heavily audited of the two (58% of raw candidates were removed).

Outputs: build_2026/SPECIES_BLACK_LIST_dd.csv
         build_2026/SPECIES_BLACK_LIST_ne.csv
"""
import csv, collections, importlib.util, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import class_for, normalise_class

csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")

spec = importlib.util.spec_from_file_location(
    "extract", os.path.join(HERE, "03_extract_and_score.py"))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)


def main():
    roster = {}
    with open(os.path.join(BUILD, "crossref_2026.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["cat_2026"] == "DD":
                roster[r["book_name"]] = {"class": r["class"], "iucn_name": r["book_name"],
                                          "recovered": "no"}
    direct = len(roster)

    # species the NE audit found are DD under a name IUCN has since changed
    with open(os.path.join(BUILD, "ne_audit_flagged.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["iucn_category"] == "DD" and r["book_name"] not in roster:
                roster[r["book_name"]] = {"class": r["book_order"],
                                          "iucn_name": r["iucn_name"], "recovered": "yes"}
    print(f"DD roster: {direct:,} direct + {len(roster)-direct} recovered from the "
          f"NE audit = {len(roster):,}")

    found = collections.defaultdict(list)
    for site, text in ex.blocks():
        for sent in re.split(r"(?<=[.;])\s+", text):
            for g, e in ex.BINOMIAL.findall(sent):
                n = f"{g} {e}"
                if n in roster:
                    found[n].append((site, sent, text))

    rows = []
    for n, hits in found.items():
        site, sent, text = max(hits, key=lambda h: (
            bool(re.search(r"known only|confined to", h[1], re.I)), len(h[1])))
        tier, label, silence, threats, prot = ex.score(sent, text)
        meta = roster[n]
        rows.append({
            "book_name": n, "iucn_name": meta["iucn_name"],
            "class": class_for(n, meta["class"]),
            "restriction_tier": tier, "restriction_basis": label,
            "tranche": "A - validated priority" if tier >= 4 else "B - unranked",
            "site": site, "recovered_from_ne_audit": meta["recovered"],
            "historical_silence": "yes" if silence else "no",
            "site_threats": "|".join(threats),
            "in_protected_area": "yes" if prot else "no",
            "evidence": sent})
    rows.sort(key=lambda r: (-r["restriction_tier"], r["class"], r["book_name"]))

    with open(os.path.join(BUILD, "SPECIES_BLACK_LIST_dd.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    ne = list(csv.DictReader(open(os.path.join(BUILD, "black_list_not_evaluated.csv"),
                                  encoding="utf-8")))
    ne_found = {}
    for site, text in ex.blocks():
        for sent in re.split(r"(?<=[.;])\s+", text):
            for g, e in ex.BINOMIAL.findall(sent):
                n = f"{g} {e}"
                if any(r["book_name"] == n for r in ne):
                    prev = ne_found.get(n)
                    if not prev or (re.search(r"known only|confined to", sent, re.I)
                                    and not re.search(r"known only|confined to", prev[1], re.I)):
                        ne_found[n] = (site, sent)

    ne_rows = []
    for r in ne:
        site, sent = ne_found.get(r["book_name"], ("", ""))
        tier, label, *_ = ex.score(sent, sent) if sent else (1, "no evidence located",
                                                             False, [], False)
        ne_rows.append({"book_name": r["book_name"], "accepted_name": r["accepted_name"],
                        "class": class_for(r["book_name"], r["class"], r["order"]),
                        "restriction_tier": tier, "restriction_basis": label,
                        "site": site, "evidence": sent})
    ne_rows.sort(key=lambda r: (-r["restriction_tier"], r["class"], r["book_name"]))
    with open(os.path.join(BUILD, "SPECIES_BLACK_LIST_ne.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ne_rows[0])); w.writeheader()
        w.writerows(ne_rows)

    a = sum(1 for r in rows if r["tranche"].startswith("A"))
    print(f"\n=== LIST 1: Data Deficient  ({len(rows):,} species) ===")
    print(f"  tranche A (tier 4-5, validated): {a:,}")
    print(f"  tranche B (tier 1-3)           : {len(rows)-a:,}")
    for k, v in collections.Counter(r["class"] for r in rows).most_common(6):
        print(f"    {v:5d}  {k}")
    print(f"\n=== LIST 2: Not Evaluated  ({len(ne_rows)} species) ===")
    for k, v in collections.Counter(r["class"] for r in ne_rows).most_common(6):
        print(f"    {v:5d}  {k}")
    print(f"  with a located evidence sentence: "
          f"{sum(1 for r in ne_rows if r['evidence']):,}/{len(ne_rows)}")


if __name__ == "__main__":
    main()
