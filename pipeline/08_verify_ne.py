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

CHECK 3 -- a genus rename is not an absence
GBIF's linkage is queried by name, so it can miss a species IUCN holds under a renamed
genus.  Aphanius iberus reached the published list as "never assessed" while IUCN carries
the same fish as *Apricaphanius iberus*, Near Threatened -- same epithet, same family
(Aphaniidae), different genus.  The v4 API 404s on the old name too, so a 404 means only
"this name string is not indexed", never "this animal was never assessed".

Matching the epithet alone is far too loose: across the whole list it produced ten hits of
which nine were coincidences between unrelated animals -- a chameleon against a skink, a
parakeet against a pigeon, a goral against a dolphin.  Two tighter tests were tried and both
failed.  FAMILY agreement fails because the two bodies disagree about the family: GBIF files
this fish in Cyprinodontidae, IUCN in Aphaniidae.  GBIF TAXON KEY identity fails because GBIF
treats both names as accepted species with different keys, not as synonyms.

What works is the AUTHORITY.  Aphanius iberus and Apricaphanius iberus are both
"(Valenciennes, 1846)" -- one nominal taxon under two generic placements -- while the
coincidences differ (Bradypodion caffer is Boettger 1889, Scelotes caffer is Peters 1861).
Author and year travel with the name through every generic revision, which is exactly the
property needed here.  So: same epithet, same class, same authority, different genus.

CHECK 4 -- domesticated forms are out of scope by policy, not neglected
IUCN does not assess domesticated animals.  Three reached the list -- the domestic water
buffalo, the llama and the alpaca -- and all three were matched from passages about humans
*introducing livestock* rather than from species accounts: "the Spanish introduced pigs,
dogs, chickens ... and water buffalo".  Calling them never assessed is the same category
error as listing a Pleistocene bear, so they are split off the same way, with the reason
recorded rather than the row silently dropped.

Outputs: build_2026/SPECIES_BLACK_LIST_ne.csv        (rewritten, verified)
         build_2026/ne_verify_removed.csv            (assessed after all)
         build_2026/prehistoric_extinctions.csv      (out of IUCN scope)
         build_2026/ne_domesticated.csv              (out of IUCN scope by policy)
"""
import csv, json, os, re, queue, threading, urllib.parse, urllib.request, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")
CACHE = os.path.join(BUILD, "gbif_iucn_cache.json")
UA = {"User-Agent": "TBG-SpeciesBlackList/1.0 (business@biodiversitygroup.org)"}

# Language Richardson uses for animals known only from pre-1500 remains.
#
# The first version keyed on preservation words (bones, subfossil, midden) and on the
# epoch names, and it let Arctodus simus -- the Pleistocene giant short-faced bear --
# through to the published register as a "never assessed" species. Its sentence names
# no bones and no epoch:
#
#   "Many large animals, including horses, camels, tapirs, mammoths, mastodonts,
#    ground sloths, sabre-tooth cats (Smilodon), the giant short-faced bear (Arctodus
#    simus) ... became extinct in North America at the end of the ice ages."
#
# Two signals were missing: the glacial time marker, and the company the species keeps.
# A sentence listing mammoths and ground sloths is describing a Quaternary extinction
# event whether or not it uses the word Pleistocene, so the co-occurring megafauna are
# treated as a date. Deep-time expressions ("11,000 years ago", "BP") are added too.
SUBFOSSIL = re.compile(
    r"subfossil|fossil|\bbones?\b|skeletal remains|described from .{0,30}remains|"
    r"prehistoric|archaeolog|midden|Holocene|Pleistocene|Pliocene|Quaternary|"
    r"cave deposits?|known only from .{0,40}(remains|deposits)|"
    r"\bice ages?\b|last glacial|glacial period|late glacial|"
    r"\b\d{1,3},\d{3} years? (?:ago|BP)\b|\bmillion years\b|"
    r"\b(mammoths?|mastodonts?|ground sloths?|sabre-?tooth|sabertooth|glyptodon|"
    r"megafauna|American cheetah|Smilodon|Miracinonyx)\b", re.I)


# Domesticated forms.  IUCN assesses wild taxa; the domesticated animal is out of scope by
# policy, and its wild ancestor is assessed separately (Bubalus arnee is Endangered, with
# nine assessments, while Bubalus bubalis has none).  Listed explicitly rather than detected
# from prose, because this is a question about IUCN's remit and not about wording.
DOMESTICATED = {
    "Bubalus bubalis", "Lama glama", "Vicugna pacos", "Bos taurus", "Bos indicus",
    "Capra hircus", "Ovis aries", "Sus domesticus", "Canis familiaris", "Felis catus",
    "Equus caballus", "Equus asinus", "Camelus dromedarius", "Camelus bactrianus",
    "Gallus domesticus", "Anas domesticus", "Cavia porcellus", "Oryctolagus domesticus",
    "Mustela furo", "Bombyx mori", "Carassius auratus", "Cyprinus rubrofuscus",
}


def iucn_by_epithet():
    """epithet -> [IUCN names] from the v2026-1 index."""
    p = os.path.join(BUILD, "iucn_2026_index.csv")
    if not os.path.exists(p):
        return {}
    out = collections.defaultdict(list)
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cn = (r["canonical_name"] or "").split()
            if len(cn) >= 2:
                out[cn[1].lower()].append(
                    {"name": r["canonical_name"], "cat": r["category"],
                     "family": r["family"], "cls": (r["class"] or "").upper()})
    return out


def gbif_authority(name, cache):
    """The author-and-year that trails a name in the GBIF backbone."""
    k = "auth::" + name
    if k in cache:
        return cache[k]
    auth = ""
    try:
        m = get("https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(name))
        sci, canon = m.get("scientificName") or "", m.get("canonicalName") or ""
        auth = sci.replace(canon, "").strip() if canon else ""
    except Exception:
        pass
    cache[k] = auth
    return auth


def same_authority(a, b):
    """Author and year agree, ignoring parentheses, spacing and punctuation."""
    n = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
    return bool(n(a)) and n(a) == n(b)


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
    ne = list(csv.DictReader(open(os.path.join(BUILD, "ne_candidates.csv"),
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

    epi = iucn_by_epithet()
    print(f"  IUCN index keyed by epithet: {len(epi):,} epithets")

    def renamed_genus(name, cls):
        """IUCN holds this same nominal taxon under a different genus."""
        parts = name.split()
        if len(parts) < 2 or not epi:
            return None
        mine = None
        for x in epi.get(parts[1].lower(), []):
            if x["name"].split()[0] == parts[0]:
                continue
            if cls and x["cls"] and x["cls"] != cls.upper():
                continue                      # cheap pre-filter before spending a call
            if mine is None:
                mine = gbif_authority(name, cache)
                if not mine:
                    return None
            if same_authority(mine, gbif_authority(x["name"], cache)):
                return x
        return None

    keep, removed, prehistoric, domestic = [], [], [], []
    for r in ne:
        res = cache.get(r["book_name"], {"code": "NE"})
        if r["book_name"] in DOMESTICATED:
            domestic.append({**r, "excluded_because":
                             "domesticated form; IUCN assesses wild taxa only"})
            continue
        if res["code"] not in ("NE", "ERROR"):
            removed.append({**r, "actual_iucn_category": res["code"],
                            "iucn_name": res["iucn_name"],
                            "found_by": "GBIF curated linkage"})
            continue
        alt = renamed_genus(r["book_name"], r.get("class"))
        if alt:
            removed.append({**r, "actual_iucn_category": alt["cat"],
                            "iucn_name": alt["name"],
                            "found_by": f"genus rename within {alt['family']}"})
            continue
        if SUBFOSSIL.search(r["evidence"]):
            prehistoric.append(r)
        else:
            keep.append(r)

    for fn, rows in (("SPECIES_BLACK_LIST_ne.csv", keep),
                     ("ne_verify_removed.csv", removed),
                     ("prehistoric_extinctions.csv", prehistoric),
                     ("ne_domesticated.csv", domestic)):
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
    print(f"  split off - domesticated     : {len(domestic)}")
    for r in domestic:
        print(f"      {r['book_name']:<28} {r['class']}")
    for r in removed:
        if str(r.get("found_by", "")).startswith("genus rename"):
            print(f"  caught by genus rename       : {r['book_name']} -> "
                  f"{r['iucn_name']} ({r['actual_iucn_category']})")
    for r in prehistoric[:5]:
        print(f"      {r['book_name']:<30} {r['class']}")
    print(f"\n  >>> VERIFIED NOT EVALUATED   : {len(keep)}")
    for k, v in collections.Counter(r["class"] for r in keep).most_common(8):
        print(f"      {v:4d}  {k}")


if __name__ == "__main__":
    main()
