"""
Triage the book names that match nothing in IUCN v2026-1.

680 of the 9,162 extracted names find no IUCN record.  That set is a mix of four
very different things and the original pipeline could not tell them apart:

  * genuine NOT EVALUATED vertebrates -- a Cambridge University Press reference
    treats them as threatened and IUCN has never assessed them.  These are the
    most valuable rows in the whole project and they are currently invisible.
  * synonyms of species IUCN *has* assessed (Agrionemys horsfieldii = Testudo
    horsfieldii).  Reporting these as unassessed would be a straight error.
  * common names swept up by the binomial regex ("Aceh orangutan", "African
    manatee") -- extraction noise.
  * out-of-scope taxa: plants (Acacia aneura), invertebrates.

Resolution uses the GBIF backbone taxonomy (no API key needed), which gives
accepted-name resolution, kingdom and class in one call.  Synonyms are then
re-checked against the IUCN index under their accepted name.

Responses are cached to build_2026/gbif_cache.json so reruns cost nothing.

Output: build_2026/unmatched_triage.csv
        build_2026/black_list_not_evaluated.csv   (the NE vertebrates)
"""
import csv, json, os, queue, threading, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")
CACHE = os.path.join(BUILD, "gbif_cache.json")
UA = {"User-Agent": "TBG-SpeciesBlackList/1.0 (business@biodiversitygroup.org)"}

# GBIF's backbone leaves `class` null for a large share of ray-finned fishes
# (172 of the 680 here), so phylum is the reliable vertebrate test.  Chordata
# also covers tunicates and lancelets, but Richardson (2023) is a vertebrate
# reference, so nothing in this corpus can be a non-vertebrate chordate.
VERTEBRATE_PHYLUM = "Chordata"


def gbif_match(name):
    u = ("https://api.gbif.org/v1/species/match?strict=false&name="
         + urllib.parse.quote(name))
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_all(names):
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))
    todo = [n for n in names if n not in cache]
    print(f"GBIF: {len(names)-len(todo)} cached, {len(todo)} to fetch")
    if todo:
        q, lock = queue.Queue(), threading.Lock()
        for n in todo:
            q.put(n)

        def worker():
            while True:
                try:
                    n = q.get_nowait()
                except queue.Empty:
                    return
                try:
                    m = gbif_match(n)
                except Exception as e:
                    m = {"matchType": "ERROR", "error": str(e)}
                with lock:
                    cache[n] = m
                    if len(cache) % 100 == 0:
                        print(f"   {len(cache)}/{len(names)}")
                q.task_done()

        ts = [threading.Thread(target=worker, daemon=True) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        json.dump(cache, open(CACHE, "w", encoding="utf-8"))
    return cache


def main():
    names, iucn = [], {}
    with open(os.path.join(BUILD, "crossref_2026.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["cat_2026"] == "not-in-2026-index":
                names.append(r["book_name"])
    with open(os.path.join(BUILD, "iucn_2026_index.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            iucn.setdefault(r["canonical_name"], r["category"])
    print(f"unmatched names to triage: {len(names)}")

    cache = fetch_all(names)

    rows = []
    for n in names:
        m = cache.get(n, {})
        mt = m.get("matchType", "NONE")
        status = m.get("status", "")
        kingdom = m.get("kingdom") or ""
        phylum = m.get("phylum") or ""
        klass = m.get("class") or ""
        order = m.get("order") or ""
        accepted = m.get("species") or m.get("scientificName") or ""
        # a synonym may still be assessed under its accepted binomial
        acc_bino = " ".join(accepted.split()[:2]) if accepted else ""
        acc_cat = iucn.get(acc_bino, "")

        if mt in ("NONE", "ERROR") or m.get("rank") not in ("SPECIES", "SUBSPECIES"):
            verdict = "extraction noise - not a resolvable species name"
        elif kingdom != "Animalia" or phylum != VERTEBRATE_PHYLUM:
            verdict = f"out of scope - {phylum or kingdom or 'unresolved'}"
        elif acc_cat:
            # covers both true synonyms and orthographic variants: either way the
            # species IS assessed, under a different name, so it is not a gap
            kind = "synonym" if status == "SYNONYM" else "name variant"
            verdict = f"already assessed - {kind}, {acc_cat} as {acc_bino}"
        else:
            # accepted-but-unassessed, or a synonym whose accepted name is also
            # unassessed -- both are genuine coverage gaps
            verdict = "NOT EVALUATED vertebrate"

        rows.append({"book_name": n, "verdict": verdict, "gbif_match": mt,
                     "gbif_status": status, "phylum": phylum, "class": klass,
                     "order": order, "accepted_name": acc_bino,
                     "iucn_cat_of_accepted": acc_cat})

    rows.sort(key=lambda r: (r["verdict"], r["book_name"]))
    with open(os.path.join(BUILD, "unmatched_triage.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    import collections
    print("\n=== triage outcome ===")
    buckets = collections.Counter(r["verdict"].split(" - ")[0] for r in rows)
    for k, v in buckets.most_common():
        print(f"  {v:5d}  {k}")

    # dedupe on accepted name: two book spellings can resolve to one species
    ne, seen = [], set()
    for r in sorted(rows, key=lambda r: r["book_name"]):
        if r["verdict"] != "NOT EVALUATED vertebrate":
            continue
        key = r["accepted_name"] or r["book_name"]
        if key in seen:
            continue
        seen.add(key)
        ne.append(r)

    cols = ["book_name", "accepted_name", "class", "order", "gbif_status"]
    with open(os.path.join(BUILD, "black_list_not_evaluated.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        w.writerows({k: r[k] for k in cols} for r in ne)

    print(f"\n=== NOT EVALUATED vertebrates: {len(ne)} unique species ===")
    for k, v in collections.Counter(r["class"] or f"(fish: {r['order']})"
                                    for r in ne).most_common(12):
        print(f"  {v:5d}  {k}")
    print("\n  examples:", ", ".join(r["book_name"] for r in ne[:6]))


if __name__ == "__main__":
    main()
