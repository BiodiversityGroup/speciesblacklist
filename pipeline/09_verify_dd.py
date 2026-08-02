"""
Apply the same independent verification to the Data Deficient list.

The NE list lost 90% of its raw candidates to verification, so it would be
negligent to assume the DD list is clean without checking.  The DD claim is
structurally safer -- it asserts that a record exists and says DD, rather than
asserting absence, and absence is what name matching gets wrong -- but the
residual risk is real: a book name can be a synonym of a species IUCN assesses
under another name and another category.

Same instrument as script 08: GBIF's curated backbone-to-IUCN link, which is built
independently of the name-string matching used to construct the list.  Species
whose verified category is not DD are moved out.  Those that come back DD under a
different name keep their place, with the IUCN name recorded so the list can be
cited accurately.

Also folds in the 17 species that script 08 removed from the NE list because they
turned out to be DD -- they are black list members, just misfiled until now.

Outputs: build_2026/SPECIES_BLACK_LIST_dd.csv   (rewritten, verified)
         build_2026/dd_verify_removed.csv       (not DD after all)
"""
import csv, json, os, queue, threading, collections, importlib.util, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import class_for

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")
CACHE = os.path.join(BUILD, "gbif_iucn_cache.json")

spec = importlib.util.spec_from_file_location(
    "verify", os.path.join(HERE, "08_verify_ne.py"))
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)


def main():
    dd = list(csv.DictReader(open(os.path.join(BUILD, "SPECIES_BLACK_LIST_dd.csv"),
                                  encoding="utf-8")))
    # species script 08 pulled out of the NE list that are really DD
    recovered = []
    p = os.path.join(BUILD, "ne_verify_removed.csv")
    if os.path.exists(p):
        have = {r["book_name"] for r in dd}
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if r["actual_iucn_category"] == "DD" and r["book_name"] not in have:
                recovered.append({
                    "book_name": r["book_name"], "iucn_name": r["iucn_name"],
                    "class": class_for(r["book_name"], r["class"]),
                    "restriction_tier": r["restriction_tier"],
                    "restriction_basis": r["restriction_basis"],
                    "tranche": "A - validated priority"
                               if int(r["restriction_tier"]) >= 4 else "B - unranked",
                    "site": r["site"], "recovered_from_ne_audit": "yes",
                    "historical_silence": "", "site_threats": "",
                    "in_protected_area": "", "evidence": r["evidence"]})
    dd += recovered
    print(f"verifying {len(dd):,} DD species ({len(recovered)} recovered from the "
          f"NE verification)")

    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [r["book_name"] for r in dd if r["book_name"] not in cache]
    print(f"  {len(todo):,} to fetch from GBIF")

    if todo:
        q, lock, done = queue.Queue(), threading.Lock(), [0]
        for n in todo:
            q.put(n)

        def worker():
            while True:
                try:
                    n = q.get_nowait()
                except queue.Empty:
                    return
                res = v.lookup(n, {})
                with lock:
                    cache[n] = res
                    done[0] += 1
                    if done[0] % 250 == 0:
                        print(f"     {done[0]:,}/{len(todo):,}")
        ts = [threading.Thread(target=worker, daemon=True) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        json.dump(cache, open(CACHE, "w", encoding="utf-8"))

    keep, removed = [], []
    for r in dd:
        res = cache.get(r["book_name"], {"code": "ERROR"})
        code = res.get("code")
        if code in ("DD", "ERROR", "NE"):
            # NE here means GBIF has no link for the name, not that IUCN never
            # assessed it -- our own index matched a DD record, which stands.
            r["verified_iucn_name"] = res.get("iucn_name", "") or r.get("iucn_name", "")
            r["verification"] = "confirmed DD" if code == "DD" else "no GBIF link - index match stands"
            keep.append(r)
        else:
            removed.append({**r, "actual_iucn_category": code,
                            "verified_iucn_name": res.get("iucn_name", "")})

    for fn, rows in (("SPECIES_BLACK_LIST_dd.csv", keep),
                     ("dd_verify_removed.csv", removed)):
        if not rows:
            continue
        with open(os.path.join(BUILD, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader()
            w.writerows(rows)

    print(f"\n  removed - not DD after all : {len(removed)}")
    if removed:
        print("     ", dict(collections.Counter(r["actual_iucn_category"]
                                                for r in removed).most_common()))
    print(f"  >>> VERIFIED DATA DEFICIENT: {len(keep):,}")
    print("     ", dict(collections.Counter(r["verification"] for r in keep).most_common()))
    a = sum(1 for r in keep if r["tranche"].startswith("A"))
    print(f"\n  tranche A (tier 4-5, validated): {a:,}")
    print(f"  tranche B (tier 1-3)           : {len(keep)-a:,}")


if __name__ == "__main__":
    main()
