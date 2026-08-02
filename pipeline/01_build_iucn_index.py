"""
Build a compact name -> IUCN category index from the GBIF-hosted IUCN Red List
Darwin Core Archive (IUCN Red List v2026-1).

Source archive: https://hosted-datasets.gbif.org/datasets/iucn/iucn-latest.zip
Citation: IUCN (2026). The IUCN Red List of Threatened Species. Version 2026-1.
          https://www.iucnredlist.org  doi:10.15468/0qnb58 (accessed via GBIF.org)

The archive has no header rows; column positions come from meta.xml:
  taxon.txt        0 taxonID, 1 scientificName, 2 kingdom, 4 class, 7 genus,
                   8 specificEpithet, 10 taxonRank, 12 taxonomicStatus
  distribution.txt 0 taxonID(coreid), 5 threatStatus

Family and order are carried through because matching on the bare binomial is not
safe on its own: IUCN and GBIF disagree about genus placement often enough to
generate false "never assessed" claims.  The Ozark cavefish is the worked example
-- GBIF calls Amblyopsis rosae an accepted name, IUCN assesses the same animal as
Troglichthys rosae (NT).  06_audit_false_negatives.py uses epithet+family to catch
those; it cannot run without these columns.

Output: build_2026/iucn_2026_index.csv
  canonical_name, category, kingdom, class, order, family, rank,
  taxonomic_status, taxon_id
"""
import csv, io, os, sys, zipfile, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
OUT = os.path.join(PROJ, "build_2026", "iucn_2026_index.csv")

# The 21 MB archive is a cache artifact, not a deliverable; keep it out of Dropbox.
ARCHIVE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.environ.get("TEMP", "."), "iucn-latest.zip")

# threatStatus arrives as human-readable text with inconsistent case
# ("Near Threatened" and "near threatened" both occur), so match on lowercase.
CODE = {
    "extinct": "EX", "extinct in the wild": "EW", "critically endangered": "CR",
    "endangered": "EN", "vulnerable": "VU", "near threatened": "NT",
    "least concern": "LC", "data deficient": "DD", "not evaluated": "NE",
    "lower risk/near threatened": "NT", "lower risk/least concern": "LC",
    "lower risk/conservation dependent": "LC", "conservation dependent": "LC",
}


def main():
    zf = zipfile.ZipFile(ARCHIVE)

    # threatStatus is repeated once per country row; the global category is the
    # value that dominates, so take the most common non-empty value per taxon.
    status = collections.defaultdict(collections.Counter)
    with zf.open("distribution.txt") as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) > 5 and p[5]:
                status[p[0]][p[5]] += 1
    print(f"distribution.txt: threat status for {len(status):,} taxa")

    rows, seen = [], set()
    with zf.open("taxon.txt") as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) < 13:
                continue
            tid, kingdom, klass, order, family = p[0], p[2], p[4], p[5], p[6]
            genus, epithet, rank, tstat = p[7], p[8], p[10], p[12]
            if not (genus and epithet):
                continue
            canonical = f"{genus} {epithet}"           # binomial, no authority
            raw = status[tid].most_common(1)
            if raw:
                cat = CODE.get(raw[0][0].strip().lower())
                if cat is None:
                    raise SystemExit(f"unmapped threatStatus {raw[0][0]!r} (taxon {tid})")
            else:
                cat = "NE"
            key = (canonical, tid)
            if key in seen:
                continue
            seen.add(key)
            rows.append((canonical, cat, kingdom, klass, order, family,
                         rank, tstat, tid))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["canonical_name", "category", "kingdom", "class", "order",
                    "family", "rank", "taxonomic_status", "taxon_id"])
        w.writerows(sorted(rows))

    print(f"wrote {len(rows):,} rows -> {OUT}")
    print("  by category:", dict(collections.Counter(r[1] for r in rows).most_common()))
    print("  by kingdom :", dict(collections.Counter(r[2] for r in rows).most_common()))


if __name__ == "__main__":
    main()
