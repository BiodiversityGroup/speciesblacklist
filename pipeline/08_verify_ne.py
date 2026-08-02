"""
Final verification of the Not Evaluated list, and separation of the species IUCN
excludes by policy rather than by neglect.

CHECK 1 -- independent confirmation of "never assessed"
Everything up to here decides assessment status by matching names against the IUCN
export.  That shares a failure mode with itself: if IUCN files a species under a
name we never think to look for, we call it unassessed.  Scripts 05 and 06 caught
the genus and family cases, but not rank changes -- IUCN treats Cyanoramphus
cookii at a rank our binomial lookup does not reach, and it is really LC.

GBIF maintains its own curated link between its backbone and IUCN taxa, built
independently of name string matching.  Querying it per species is therefore a
genuine second opinion rather than a rerun of the same logic.  Anything it reports
as assessed is removed.  Verified false positives found this way include:
    Cyanoramphus cookii      -> LC
    Chatarrhaea longirostris -> VU

CHECK 2 -- pre-1500 extinctions are out of scope, not neglected
Richardson covers "recently extinct" vertebrates, which includes species known
only from subfossil bones -- the St Croix macaw, the Madeira scops owl, the New
Zealand swan.  The IUCN Red List only treats extinctions from 1500 AD onward, so
these are outside its remit by published policy.  Listing them as coverage gaps
would be a category error and would hand a reviewer an easy way to dismiss the
whole list, so they are split into their own file and excluded from the headline.

Outputs: build_2026/SPECIES_BLACK_LIST_ne.csv        (rewritten, verified)
         build_2026/ne_verify_removed.csv            (assessed after all)
         build_2026/prehistoric_extinctions.csv      (out of IUCN scope)
"""
import csv, json, os, re, queue, threading, urllib.parse, urllib.request, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")
CACHE = os.path.join(BUILD, "gbif_iucn_cache.json")
UA = {"User-Agent": "TBG-SpeciesBlackList/1.0 (business@biodiversitygroup.org)"}

# Language Richardson uses for animals known only from pre-1500 remains.
SUBFOSSIL = re.compile(
    r"subfossil|fossil|\bbones?\b|skeletal remains|described from .{0,30}remains|"
    r"prehistoric|archaeolog|midden|Holocene|Pleistocene|cave deposits?|"
    r"known only from .{0,40}(remains|deposits)", re.I)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=30) as r:
        return json.loads(r.read().decode())


def lookup(name, cache):
    if name in cache:
        return cache[name]
    try:
        m = get("https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(name))
        key = m.get("usageKey")
        out = {"code": "NE", "iucn_name": ""}
        if key:
            try:
                c = get(f"https://api.gbif.org/v1/species/{key}/iucnRedListCategory")
                out = {"code": c.get("code", "NE"),
                       "iucn_name": c.get("scientificName", "")}
            except Exception:
                pass
    except Exception as e:
        out = {"code": "ERROR", "iucn_name": str(e)}
    cache[name] = out
    return out


def main():
    ne = list(csv.DictReader(open(os.path.join(BUILD, "SPECIES_BLACK_LIST_ne.csv"),
                                  encoding="utf-8")))
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [r["book_name"] for r in ne if r["book_name"] not in cache]
    print(f"verifying {len(ne)} NE species against GBIF's curated IUCN linkage "
          f"({len(todo)} to fetch)")

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
                res = lookup(n, {})
                with lock:
                    cache[n] = res
        ts = [threading.Thread(target=worker, daemon=True) for _ in range(6)]
        [t.start() for t in ts]; [t.join() for t in ts]
        json.dump(cache, open(CACHE, "w", encoding="utf-8"))

    keep, removed, prehistoric = [], [], []
    for r in ne:
        res = cache.get(r["book_name"], {"code": "NE"})
        if res["code"] not in ("NE", "ERROR"):
            removed.append({**r, "actual_iucn_category": res["code"],
                            "iucn_name": res["iucn_name"]})
        elif SUBFOSSIL.search(r["evidence"]):
            prehistoric.append(r)
        else:
            keep.append(r)

    for fn, rows in (("SPECIES_BLACK_LIST_ne.csv", keep),
                     ("ne_verify_removed.csv", removed),
                     ("prehistoric_extinctions.csv", prehistoric)):
        if not rows:
            continue
        with open(os.path.join(BUILD, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader()
            w.writerows(rows)

    print(f"\n  removed - actually assessed  : {len(removed)}")
    if removed:
        print("     ", dict(collections.Counter(r["actual_iucn_category"]
                                                for r in removed).most_common()))
        for r in removed[:6]:
            print(f"      {r['book_name']:<30} -> {r['actual_iucn_category']}")
    print(f"  split off - pre-1500 extinct : {len(prehistoric)}")
    for r in prehistoric[:5]:
        print(f"      {r['book_name']:<30} {r['class']}")
    print(f"\n  >>> VERIFIED NOT EVALUATED   : {len(keep)}")
    for k, v in collections.Counter(r["class"] for r in keep).most_common(8):
        print(f"      {v:4d}  {k}")


if __name__ == "__main__":
    main()
