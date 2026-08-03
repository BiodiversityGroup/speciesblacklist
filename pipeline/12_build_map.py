"""
Build the map layer: real georeferenced occurrence points for each species.

WHY NOT GEOCODE THE SITE NAMES
The register stores localities as text pulled from Richardson's prose -- "The Mano
River", "Arrowsmith Bank", "Espiritu Santo". Running those through a gazetteer
would invent coordinates: place-name geocoding is ambiguous exactly where this
corpus is ambiguous, and a map that confidently puts a species in the wrong ocean
is worse than no map. So the points here are actual georeferenced specimen and
observation records from GBIF, which are citable.

THE TRAP THAT GOVERNS THIS SCRIPT
GBIF's free-text `scientificName=` search must NOT be used. Many of these names are
synonyms, and the free-text search silently returns records of the *accepted*
species instead:

    Anampses viridis   free-text scientificName= : 3071 records, centroid inland NSW
    Anampses viridis   precise taxonKey=         :    3 records, all at Reunion

The book describes A. viridis as known from a single specimen; the 3,071 belong to
Anampses caeruleopunctatus, its widespread senior synonym. A map built on free-text
matching would smear narrow endemics across the ranges of common species -- a
systematic error in the same family as the name-matching trap that wrecked the
first Not-Evaluated list. Always resolve to a usageKey with strict matching, then
query by taxonKey.

Also passes hasGeospatialIssue=false, which drops records GBIF itself flags as
having bad coordinates. Even then bad points survive (a Brazilian sea bass with a
record off Malaysia), so the page presents density, never a single authoritative
dot, and says so.

Each point carries the INDEX of the species it belongs to, not just its tier, so a
click on the map can name the species in a cell and hand them to the register. The
index costs less than repeating the tier and list flags per point, which are looked
up from the register payload instead.

Outputs: site/map.json  { land: [[lon,lat],...], names: [...], points: [[lon,lat,i]] }
"""
import json, math, os, queue, statistics, threading, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SITE = os.path.join(PROJ, "site")
CACHE = os.path.join(PROJ, "build_2026", "gbif_occurrence_cache.json")
UA = {"User-Agent": "TBG-SpeciesBlackList/1.0 (business@biodiversitygroup.org)"}

MAX_PTS = 30          # plenty for a density surface; keeps the payload small
LAND_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
            "master/geojson/ne_110m_land.geojson")


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception:
            if i == tries - 1:
                raise
    return None


def occurrences(name):
    """Strict-match the name to a usageKey, then pull points by taxonKey."""
    m = get("https://api.gbif.org/v1/species/match?strict=true&name="
            + urllib.parse.quote(name))
    key = m.get("usageKey")
    if not key:
        return {"key": None, "count": 0, "pts": []}
    r = get("https://api.gbif.org/v1/occurrence/search"
            f"?taxonKey={key}&hasCoordinate=true&hasGeospatialIssue=false"
            f"&limit={MAX_PTS}")
    pts = []
    for o in r.get("results", []):
        la, lo = o.get("decimalLatitude"), o.get("decimalLongitude")
        if la is None or lo is None:
            continue
        if abs(la) > 90 or abs(lo) > 180:
            continue
        # 0,0 is the classic null-island artefact, never a real record
        if abs(la) < 0.001 and abs(lo) < 0.001:
            continue
        pts.append([round(lo, 3), round(la, 3)])
    return {"key": key, "count": r.get("count", 0), "pts": pts}


def perp(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def simplify(pts, tol):
    """Douglas-Peucker, iterative so a long coastline cannot blow the stack."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        worst, idx = 0.0, -1
        for k in range(i + 1, j):
            d = perp(pts[k], pts[i], pts[j])
            if d > worst:
                worst, idx = d, k
        if worst > tol and idx > 0:
            keep[idx] = True
            stack.append((i, idx)); stack.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def land_rings(tol=0.18, min_pts=5):
    # tol=0.55 gave 1,330 vertices for the whole world, which is visibly blobby at
    # ~1100px wide. 0.18 lands near 4k vertices and about 90 KB -- still trivial.
    """Natural Earth 110m land, simplified. Public domain."""
    gj = get(LAND_URL)
    rings = []
    for feat in gj["features"]:
        g = feat["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            outer = poly[0]                      # outer ring only; holes are
            s = simplify([[c[0], c[1]] for c in outer], tol)   # invisible at this scale
            if len(s) >= min_pts:
                rings.append([[round(x, 2), round(y, 2)] for x, y in s])
    return rings


def main():
    data = json.load(open(os.path.join(SITE, "data.json"), encoding="utf-8"))
    species = data["species"]

    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [s["n"] for s in species if s["n"] not in cache]
    print(f"occurrences: {len(species)-len(todo):,} cached, {len(todo):,} to fetch")

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
                try:
                    res = occurrences(n)
                except Exception as e:
                    res = {"key": None, "count": 0, "pts": [], "err": str(e)}
                with lock:
                    cache[n] = res
                    done[0] += 1
                    if done[0] % 200 == 0:
                        print(f"   {done[0]:,}/{len(todo):,}")
        ts = [threading.Thread(target=worker, daemon=True) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        json.dump(cache, open(CACHE, "w", encoding="utf-8"))

    # Points reference their species by index into `names`. Tier and list flags are
    # not repeated per point -- the page already holds them in data.json and can
    # look them up, and carrying identity is what makes a cell clickable.
    names, points, mapped, unmapped = [], [], 0, []
    for s in species:
        c = cache.get(s["n"]) or {}
        pts = c.get("pts") or []
        if not pts:
            unmapped.append(s["n"])
            continue
        idx = len(names)
        names.append(s["n"])
        mapped += 1
        for lo, la in pts:
            points.append([lo, la, idx])

    print(f"\nmappable species : {mapped:,} / {len(species):,}")
    print(f"unmappable       : {len(unmapped):,} (no georeferenced GBIF record)")
    print(f"points           : {len(points):,}")
    by_tier = {}
    for s in species:
        if (cache.get(s['n']) or {}).get('pts'):
            by_tier[s['t']] = by_tier.get(s['t'], 0) + 1
    print("mapped species by tier:", dict(sorted(by_tier.items(), reverse=True)))

    print("\nfetching Natural Earth 110m land ...")
    rings = land_rings()
    print(f"  {len(rings)} rings, {sum(len(r) for r in rings):,} vertices")

    out = {
        "land": rings,
        "names": names,
        "points": points,
        "stats": {
            "species_total": len(species),
            "species_mapped": mapped,
            "species_unmapped": len(unmapped),
            "points": len(points),
            "mapped_by_tier": by_tier,
            "max_points_per_species": MAX_PTS,
        },
    }
    p = os.path.join(SITE, "map.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"\nwrote {p}  ({os.path.getsize(p)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
