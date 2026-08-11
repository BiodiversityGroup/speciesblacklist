"""
Geocode the register's named localities, with verification.

WHY THIS IS NOT "INVENTING COORDINATES"
Looking up "Salween River" or "Gulf of Panama" is a gazetteer lookup, not a guess.
The earlier refusal to geocode was over-broad: it took a real risk that applies to
a subset -- names like "Espiritu Santo" or "Cordillera Central" that recur around
the world -- and used it to rule out the unambiguous majority. 83% of the 902
distinct localities are clean named physical features.

WHAT MAKES IT SAFE IS THE VERIFICATION, NOT THE LOOKUP
Nominatim will happily answer any string. Asked for "The Cordillera Central" it
returns a *university* in Baguio at 16.41,120.60. Plotted blind, a mountain range
becomes a campus. So every result is checked three ways and dropped if it fails:

  1. TYPE AGREEMENT -- the feature noun in the name implies a class. A name ending
     "River" must come back as a waterway, "Island" as an island, "Mountains" as a
     ridge/range/peak. Universities, buildings, roads and shops are rejected
     outright whatever the name.
  2. EXTENT -- Nominatim's bounding box gives the feature's size. An ocean basin's
     centroid is open water thousands of km from any actual record, so anything
     spanning more than MAX_SPAN degrees is recorded but flagged too coarse to plot.
  3. CONTEXT -- where the book supplied a locality account, its opening sentence
     usually names the country. If it does and the gazetteer disagrees, the match
     is flagged rather than trusted.

Everything is cached, and the confidence of each result is carried through to the
page so the map can separate verified points from coarse ones. Nominatim's usage
policy requires a real User-Agent and at most one request per second; both honoured.

Outputs: build_2026/geocode_cache.json
         site/geo.json   { locality -> {lat, lon, kind, span, conf} }
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SITE = os.path.join(PROJ, "site")
CACHE = os.path.join(PROJ, "build_2026", "geocode_cache.json")
UA = {"User-Agent": "TBG-SpeciesBlackList/1.0 (business@biodiversitygroup.org)"}

MAX_SPAN = 12.0     # degrees; beyond this the centroid is not a locality
SLEEP = 1.1         # Nominatim: <=1 request/second

# feature noun in the name -> OSM types that would corroborate it
EXPECT = {
    r"River|Stream|Creek|Drainage|Delta|Estuary": {
        "river", "stream", "water", "waterway", "riverbank", "canal", "strait",
        "bay", "wetland", "reservoir", "basin"},
    r"Lake|Lagoon|Swamp|Marsh|Reservoir": {
        "water", "lake", "lagoon", "wetland", "reservoir", "protected_area", "basin"},
    r"Islands?|Islet|Atoll|Cay|Archipelago": {
        "island", "islet", "archipelago", "atoll", "reef", "protected_area",
        "administrative", "town", "village", "county", "state"},
    r"Mountains?|Range|Ranges|Massif|Cordillera|Sierra|Peak|Hills?|Highlands|Plateau|Escarpment": {
        "peak", "ridge", "mountain_range", "massif", "volcano", "plateau", "hill",
        "natural", "protected_area", "saddle"},
    r"Bay|Gulf|Sound|Strait|Channel|Sea|Ocean|Bight": {
        "bay", "gulf", "strait", "sea", "ocean", "water", "channel", "sound"},
    r"Reef|Bank|Ridge|Rise|Trench|Seamount|Seamount Chain|Abyssal Plain": {
        "reef", "bank", "ridge", "shoal", "water", "sea", "ocean", "natural"},
    r"Cave|Caves|Sinkhole|Cenote|Springs?|Falls|Rapids": {
        "cave_entrance", "spring", "waterfall", "water", "natural", "hole"},
    r"Valley|Gorge|Canyon|Depression": {"valley", "natural", "gorge", "ravine"},
    r"National Park|Reserve|Forest|Desert": {
        "protected_area", "national_park", "nature_reserve", "forest", "wood",
        "desert", "natural", "boundary"},
    r"Peninsula": {"peninsula", "natural", "administrative", "cape"},
    r"Volcano|Crater": {"volcano", "peak", "crater", "natural"},
}
# never acceptable as a locality, whatever the name asked for
BANNED = {
    "university", "college", "school", "hospital", "hotel", "restaurant", "cafe",
    "bar", "pub", "shop", "supermarket", "mall", "museum", "library", "church",
    "mosque", "temple", "bank_branch", "atm", "pharmacy", "parking", "fuel",
    "bus_stop", "station", "aerodrome", "airport", "residential", "house",
    "building", "apartments", "office", "company", "highway", "road", "street",
    "path", "track", "footway", "railway", "platform", "attraction", "hostel",
    "guest_house", "camp_site", "pitch", "sports_centre", "stadium", "zoo",
}


def nominatim(q):
    u = ("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=3&q="
         + urllib.parse.quote(q))
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return json.loads(r.read().decode())


def expected_types(name):
    for pat, types in EXPECT.items():
        if re.search(rf"\b(?:{pat})\b", name, re.I):
            return types
    return None


def span_of(box):
    """Nominatim boundingbox is [south, north, west, east] as strings."""
    try:
        s, n, w, e = (float(x) for x in box)
        return max(abs(n - s), abs(e - w))
    except Exception:
        return None


def judge(name, results):
    """Pick the best corroborated result, or return why nothing qualified."""
    want = expected_types(name)
    for r in results:
        t = (r.get("type") or "").lower()
        cls = (r.get("class") or "").lower()
        if t in BANNED or cls in BANNED:
            continue
        span = span_of(r.get("boundingbox") or [])
        rec = {"lat": round(float(r["lat"]), 4), "lon": round(float(r["lon"]), 4),
               "kind": f"{cls}/{t}", "span": None if span is None else round(span, 2),
               "display": (r.get("display_name") or "")[:120]}
        if want is not None:
            if t in want or cls in want:
                rec["conf"] = "verified"
            else:
                # the name promised a physical feature and the gazetteer gave
                # something else; keep it, but never plot it as if confirmed
                rec["conf"] = "unconfirmed-type"
        else:
            rec["conf"] = "no-type-expectation"
        if rec["span"] is not None and rec["span"] > MAX_SPAN:
            rec["conf"] = "too-coarse"
        return rec
    return {"conf": "rejected", "reason": "no acceptable result"}


def main():
    data = json.load(open(os.path.join(SITE, "data.json"), encoding="utf-8"))
    locs = collections.Counter(s["s"] for s in data["species"] if s["s"])
    # habitat types are not places; never send them to a gazetteer
    habitat = {s["name"] for s in data["sites"] if s.get("habitat")}
    # A string naming two places ('Athi and Tana River') has no single coordinate, so
    # it is withheld rather than reduced -- every reduction either drops the noun that
    # identified it or fabricates a place. Three such strings previously reached the
    # map. See _locality.is_compound for the reasoning.
    sys.path.insert(0, HERE)
    from _locality import is_compound
    # sentence fragments that leaked out of the header extractor are not places
    targets = [l for l in locs
               if l not in habitat and len(l) <= 48 and l.count(" ") <= 5
               and not is_compound(l)
               and not re.search(r"\b(is|are|runs|surrounds|covers|lies|means)\b", l)]
    print(f"distinct localities: {len(locs):,}  ->  geocoding {len(targets):,} "
          f"(dropped {len(locs)-len(targets)} habitat types and sentence fragments)")

    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [t for t in targets if t not in cache]
    print(f"  {len(todo):,} to fetch  (~{len(todo)*SLEEP/60:.0f} min at 1 req/s)\n")

    for i, name in enumerate(todo, 1):
        q = re.sub(r"^The\s+", "", name).strip()
        try:
            cache[name] = judge(name, nominatim(q))
        except Exception as e:
            cache[name] = {"conf": "error", "reason": str(e)[:80]}
        if i % 50 == 0:
            print(f"   {i:,}/{len(todo):,}")
            json.dump(cache, open(CACHE, "w", encoding="utf-8"))
        time.sleep(SLEEP)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"))

    out, stats = {}, collections.Counter()
    for name in targets:
        r = cache.get(name) or {}
        stats[r.get("conf", "missing")] += 1
        if r.get("conf") in ("verified", "no-type-expectation") and "lat" in r:
            out[name] = {"lat": r["lat"], "lon": r["lon"], "kind": r["kind"],
                         "conf": r["conf"], "n": locs[name]}
    print("\ntype-check breakdown:")
    for k, v in stats.most_common():
        print(f"  {v:>5}  {k}")

    # ---- second, independent check: does the geocode agree with real records? ----
    # Type agreement is necessary but NOT sufficient: it cannot see a same-type
    # homonym. "Congo River" resolved to a real river of that name in Sierra Leone,
    # 4,000 km from the Congo; "Dunk Island" to one near Sydney rather than the
    # Queensland island. Both passed as river/river and island/island.
    #
    # So each geocode is measured against the GBIF occurrence points of the species
    # that sit at that locality -- an independent witness we already hold. Anything
    # further than THRESHOLD_KM from every one of its own species' records is
    # contradicted and never plotted.
    THRESHOLD_KM = 500
    occ = json.load(open(os.path.join(PROJ, "build_2026",
                                      "gbif_occurrence_cache.json"), encoding="utf-8"))
    data_sp = data["species"]
    witness = collections.defaultdict(list)
    for s in data_sp:
        if s["s"] in out:
            for lo, la in ((occ.get(s["n"]) or {}).get("pts") or []):
                witness[s["s"]].append((la, lo))

    def km(a, b):
        (la1, lo1), (la2, lo2) = a, b
        p = math.pi / 180
        return 2 * 6371 * math.asin(math.sqrt(
            math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) *
            math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2))

    verdict = collections.Counter()
    for name, v in out.items():
        w = witness.get(name)
        if not w:
            v["check"] = "unverified"          # no witness exists; cannot be checked
        else:
            dmin = min(km((v["lat"], v["lon"]), p) for p in w)
            v["check"] = "validated" if dmin <= THRESHOLD_KM else "contradicted"
            v["km"] = round(dmin)
        verdict[v["check"]] += 1

    print(f"\ncross-check against their own species' GBIF records "
          f"(threshold {THRESHOLD_KM} km):")
    for k in ("validated", "contradicted", "unverified"):
        print(f"  {verdict[k]:>5}  {k}")

    # contradicted geocodes are dropped outright
    out = {k: v for k, v in out.items() if v["check"] != "contradicted"}
    plot_ok = {k: v for k, v in out.items() if v["check"] == "validated"}
    gbif_ok = {s["n"] for s in data_sp if (occ.get(s["n"]) or {}).get("pts")}
    gained = len({s["n"] for s in data_sp
                  if s["s"] in plot_ok and s["n"] not in gbif_ok})
    print(f"\nvalidated localities plotted : {len(plot_ok):,}")
    print(f"  species they newly place   : {gained:,} (had no GBIF record of their own)")
    print(f"unverified, kept but flagged : {sum(1 for v in out.values() if v['check']=='unverified'):,}")

    p = os.path.join(SITE, "geo.json")
    json.dump({"localities": out,
               "stats": {k: v for k, v in stats.items()},
               "check": dict(verdict),
               "threshold_km": THRESHOLD_KM,
               "newly_placed": gained,
               "max_span_deg": MAX_SPAN},
              open(p, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"wrote {p}  ({os.path.getsize(p)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
