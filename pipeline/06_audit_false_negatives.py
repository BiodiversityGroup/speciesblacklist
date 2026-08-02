"""
Audit the "NOT EVALUATED" list for false positives before anything is published.

THE FAILURE MODE
The NE list is built by failing to find a book name in the IUCN index.  That is
only sound if the two sources agree on genus placement, and they frequently do
not.  Worked example: Richardson and GBIF both use Amblyopsis rosae for the Ozark
cavefish, while IUCN assesses the same animal as Troglichthys rosae and rates it
Near Threatened.  A plain binomial lookup misses it and the species lands in the
NE bucket -- i.e. we would publicly claim IUCN has never looked at a species it
has actually assessed.  That single class of error would discredit the list.

THE TEST
For every NE candidate, look for IUCN records sharing the specific epithet in the
same corner of the tree.  Epithet alone is far too noisy -- "grahami" spans 20
IUCN records across fish, lizards, crabs and snails -- so it is paired with rank:

  tier 1  epithet + same FAMILY  -> genus was reassigned.  Near-certain match;
          demoted.  Example: Amblyopsis rosae = IUCN Troglichthys rosae (NT).
  tier 2  epithet + same ORDER   -> genus AND family both moved.  Order is the
          stable rank across taxonomies, so this catches the harder cases.
          Example: Aphanius iberus (Cyprinodontidae) = IUCN Apricaphanius iberus
          (Aphaniidae, NT) -- both ranks changed.

Tier 2 on its own produces homonyms: Sinosuthora przewalskii (an Asian parrotbill)
matches Grallaria przewalskii (a South American antpitta) because both are
Passeriformes.  So every tier-2 hit is confirmed against GBIF -- both names are
resolved to their accepted taxon and the demotion only stands if they land on the
same species.  Unconfirmed hits are reinstated as NE rather than dropped.

Nothing is deleted: every demotion is written out with the IUCN name it matched.

Family and order for the book names come from the GBIF cache built by script 05.

Outputs: build_2026/ne_audit_flagged.csv          (demoted - needs eyeball)
         build_2026/black_list_not_evaluated.csv  (rewritten, audited)
"""
import csv, json, os, collections, urllib.parse, urllib.request

UA = {"User-Agent": "TBG-SpeciesBlackList/1.0 (business@biodiversitygroup.org)"}


def gbif_accepted(name, cache):
    """Accepted-species name GBIF resolves `name` to, or '' if unresolvable."""
    if name not in cache:
        u = ("https://api.gbif.org/v1/species/match?strict=false&name="
             + urllib.parse.quote(name))
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                        timeout=30) as r:
                cache[name] = json.loads(r.read().decode())
        except Exception as e:
            cache[name] = {"matchType": "ERROR", "error": str(e)}
    m = cache[name]
    acc = m.get("species") or ""
    return " ".join(acc.split()[:2])

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")


def main():
    idx = list(csv.DictReader(open(os.path.join(BUILD, "iucn_2026_index.csv"),
                                   encoding="utf-8")))
    by_ep_fam, by_ep_ord = collections.defaultdict(list), collections.defaultdict(list)
    for r in idx:
        ep = r["canonical_name"].split()[-1].lower()
        by_ep_fam[(ep, r["family"].upper())].append(r)
        by_ep_ord[(ep, r["order"].upper())].append(r)

    gbif = json.load(open(os.path.join(BUILD, "gbif_cache.json"), encoding="utf-8"))
    # Read from the triage output, NOT from black_list_not_evaluated.csv -- this
    # script rewrites that file, so reading it would make a second run audit its
    # own output and silently report zero findings.
    ne, seen = [], set()
    with open(os.path.join(BUILD, "unmatched_triage.csv"), encoding="utf-8") as fh:
        for r in sorted(csv.DictReader(fh), key=lambda r: r["book_name"]):
            if r["verdict"] != "NOT EVALUATED vertebrate":
                continue
            key = r["accepted_name"] or r["book_name"]
            if key in seen:
                continue
            seen.add(key)
            ne.append({"book_name": r["book_name"], "accepted_name": r["accepted_name"],
                       "class": r["class"], "order": r["order"],
                       "gbif_status": r["gbif_status"]})
    print(f"auditing {len(ne)} NE candidates against {len(idx):,} IUCN records")

    clean, flagged = [], []
    for r in ne:
        name = r["book_name"]
        m = gbif.get(name, {})
        fam = (m.get("family") or "").upper()
        order = (m.get("order") or "").upper()
        ep = (r["accepted_name"] or name).split()[-1].lower()

        hits = by_ep_fam.get((ep, fam), []) if fam else []
        tier = "1 - genus reassigned (same family)"
        if not hits and order:
            hits = by_ep_ord.get((ep, order), [])
            tier = "2 - genus + family reassigned (same order) - verify"
        if hits and tier.startswith("2"):
            # confirm via GBIF: both names must resolve to the same accepted taxon
            mine = gbif_accepted(name, gbif)
            hits = [h for h in hits
                    if gbif_accepted(h["canonical_name"], gbif) == mine and mine]
            if not hits:
                r["audit_note"] = "tier-2 candidate reinstated: GBIF says homonym"
                clean.append(r)
                continue
        if hits:
            h = hits[0]
            flagged.append({
                "book_name": name, "tier": tier, "book_family": fam,
                "book_order": order, "iucn_name": h["canonical_name"],
                "iucn_category": h["category"], "iucn_family": h["family"]})
        else:
            clean.append(r)

    json.dump(gbif, open(os.path.join(BUILD, "gbif_cache.json"), "w",
                         encoding="utf-8"))

    flagged.sort(key=lambda f: (f["tier"], f["book_name"]))
    for fn, rows, cols in (
        ("ne_audit_flagged.csv", flagged,
         ["book_name", "tier", "book_family", "book_order", "iucn_name",
          "iucn_category", "iucn_family"]),
        ("black_list_not_evaluated.csv", clean, list(ne[0].keys()))):
        with open(os.path.join(BUILD, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
            w.writerows({k: r.get(k, "") for k in cols} for r in rows)

    print(f"\n  demoted (assessed under another name): {len(flagged)}")
    for t, n in collections.Counter(f["tier"] for f in flagged).most_common():
        print(f"      {n:4d}  tier {t}")
    print(f"  surviving as genuinely NOT EVALUATED  : {len(clean)}")
    if flagged:
        print("\n  examples of what the audit caught:")
        for f in flagged[:6] + flagged[-4:]:
            print(f"    [{f['tier'][0]}] {f['book_name']:<30} -> IUCN "
                  f"{f['iucn_name']} ({f['iucn_category']})")
        print("\n  categories they were hiding in:",
              dict(collections.Counter(f["iucn_category"] for f in flagged).most_common()))
    print("\n  surviving NE by class:")
    for k, v in collections.Counter(r["class"] or f"(fish: {r['order']})"
                                    for r in clean).most_common(10):
        print(f"    {v:4d}  {k}")


if __name__ == "__main__":
    main()
