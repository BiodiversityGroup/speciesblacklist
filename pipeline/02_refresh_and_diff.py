"""
Refresh the Species Black List cross-reference against IUCN Red List v2026-1 and
diff it against the September 2024 baseline that the original analysis used.

Two questions this answers:
  1. Which of the 2,434 book species that were Data Deficient in 2024 have since
     been reassessed, and where did they land?  (Any still published as DD in our
     material after they have moved would be a factual error.)
  2. Of those reassessed, what share came out threatened?  That is a direct
     empirical test of the project's premise -- if the book's "known only from a
     single river" species are genuinely at risk, IUCN's own reassessments should
     agree at a rate well above the ~28% all-species baseline.

Inputs : build_2026/iucn_2026_index.csv  (from 01_build_iucn_index.py)
         latin_species_names.csv          (9,162 unique names from Richardson 2023)
         IUCN DD list/, IUCN threatened extinct list/, LC and others/  (2024 baseline)
Outputs: build_2026/crossref_2026.csv     (every book name x 2024 cat x 2026 cat)
         build_2026/dd_movement_2024_to_2026.csv  (only the ones that moved)
"""
import csv, collections, os

csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")

SHORT = {"Data Deficient": "DD", "Least Concern": "LC", "Near Threatened": "NT",
         "Vulnerable": "VU", "Endangered": "EN", "Critically Endangered": "CR",
         "Extinct": "EX", "Extinct in the Wild": "EW",
         "Lower Risk/near threatened": "NT", "Lower Risk/least concern": "LC"}
THREATENED = {"VU", "EN", "CR"}
GONE = {"EX", "EW"}
# Rank the categories so that when one binomial carries several IUCN rows
# (species plus subspecies plus subpopulations) we report the species-level one.
RANK_PREF = {"species": 0, "subspecies": 1, "variety": 2, "form": 3,
             "subpopulation": 4, "": 5}


def load_2026():
    """canonical binomial -> (category, kingdom, class); species rank wins."""
    best = {}
    with open(os.path.join(BUILD, "iucn_2026_index.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            name = r["canonical_name"]
            # accepted names beat synonyms; species rank beats infraspecific
            key = (0 if r["taxonomic_status"] == "accepted" else 1,
                   RANK_PREF.get(r["rank"], 9))
            if name not in best or key < best[name][0]:
                best[name] = (key, (r["category"], r["kingdom"], r["class"]))
    return {k: v[1] for k, v in best.items()}


def load_2024():
    """canonical binomial -> category, from the three Sept-2024 exports."""
    out = {}
    for d in ("LC and others", "IUCN threatened extinct list", "IUCN DD list"):
        tax = {}
        with open(os.path.join(PROJ, d, "taxonomy.csv"), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                tax[r["internalTaxonId"]] = r
        with open(os.path.join(PROJ, d, "assessments.csv"), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                t = tax.get(r["internalTaxonId"], {})
                # normalise to a bare binomial to match the 2026 index
                canon = " ".join(
                    x for x in (t.get("genusName", ""), t.get("speciesName", "")) if x
                ) or r["scientificName"]
                out[canon.strip()] = SHORT.get(r["redlistCategory"], r["redlistCategory"])
    return out


def book_names():
    with open(os.path.join(PROJ, "latin_species_names.csv"),
              encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))[1:]
    return sorted({r[0].strip() for r in rows if r and r[0].strip()})


def main():
    cat26, cat24, names = load_2026(), load_2024(), book_names()
    print(f"2026-1 index: {len(cat26):,} binomials | "
          f"2024 baseline: {len(cat24):,} | book names: {len(names):,}\n")

    rows = []
    for n in names:
        c24 = cat24.get(n, "not-in-2024-export")
        m = cat26.get(n)
        c26, kingdom, klass = m if m else ("not-in-2026-index", "", "")
        rows.append({"book_name": n, "cat_2024": c24, "cat_2026": c26,
                     "kingdom": kingdom, "class": klass,
                     "moved": "yes" if c24 != c26 else "no"})

    with open(os.path.join(BUILD, "crossref_2026.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    print("=== Book names by IUCN v2026-1 category ===")
    for k, v in collections.Counter(r["cat_2026"] for r in rows).most_common():
        print(f"  {v:6d}  {k}")

    # --- the premise test: what happened to the 2024 DD cohort? ---
    dd = [r for r in rows if r["cat_2024"] == "DD"]
    moved = [r for r in dd if r["cat_2026"] not in ("DD", "not-in-2026-index")]
    still = [r for r in dd if r["cat_2026"] == "DD"]
    lost = [r for r in dd if r["cat_2026"] == "not-in-2026-index"]

    print(f"\n=== 2024 Data Deficient cohort (n={len(dd)}) ===")
    print(f"  still DD in 2026-1        : {len(still)}")
    print(f"  reassessed to a new cat   : {len(moved)}")
    print(f"  no longer matchable       : {len(lost)}  (taxonomy changed / merged)")

    if moved:
        dist = collections.Counter(r["cat_2026"] for r in moved)
        print("\n  where the reassessed ones landed:")
        for k in ("CR", "EN", "VU", "NT", "LC", "EX", "EW"):
            if dist.get(k):
                print(f"    {dist[k]:4d}  {k}")
        thr = sum(dist.get(k, 0) for k in THREATENED | GONE)
        print(f"\n  >>> {thr}/{len(moved)} = {100*thr/len(moved):.1f}% came out "
              f"threatened or extinct")
        print(f"      (all-species Red List baseline is ~28%)")

        with open(os.path.join(BUILD, "dd_movement_2024_to_2026.csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(moved[0]))
            w.writeheader(); w.writerows(moved)

    # the live black list: still DD, so still excluded from GBF Target 4
    print(f"\n=== Live black list (still DD in v2026-1): {len(still)} ===")
    for k, v in collections.Counter(r["class"] for r in still).most_common():
        print(f"  {v:6d}  {k}")


if __name__ == "__main__":
    main()
