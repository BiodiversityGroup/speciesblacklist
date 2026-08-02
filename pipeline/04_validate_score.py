"""
Validate the restriction score against ground truth.

Between the Sept 2024 export and IUCN v2026-1, IUCN independently reassessed 108
of the book's Data Deficient species and gave each a real category.  Those 108 are
a held-out labelled set that the scoring rules never saw.  If the rules capture
genuine extinction risk, the high-restriction species should have gone threatened
at a materially higher rate than the low-restriction ones.

This is the test that decides whether the black list ships as a ranked list or
not at all.  Reported alongside is the base rate, so the score has to beat it.

Output: build_2026/validation_report.txt
"""
import csv, os, re, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.path.join(PROJ, "build_2026")

spec = importlib.util.spec_from_file_location(
    "extract", os.path.join(HERE, "03_extract_and_score.py"))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)

THREATENED = {"CR", "EN", "VU", "EX", "EW"}


def fisher(a, b, c, d):
    """Two-sided Fisher exact p for the 2x2 [[a,b],[c,d]]."""
    from math import comb
    n, r1, c1 = a + b + c + d, a + b, a + c
    pk = lambda k: comb(r1, k) * comb(n - r1, c1 - k) / comb(n, c1)
    obs = pk(a)
    return sum(pk(k) for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1)
               if pk(k) <= obs + 1e-12)


def wilson(k, n):
    """95% CI on a proportion; small-n honest, unlike a bare percentage."""
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - m), min(1.0, c + m))


def main():
    moved = {}
    with open(os.path.join(BUILD, "dd_movement_2024_to_2026.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            moved[r["book_name"]] = r["cat_2026"]
    print(f"labelled set: {len(moved)} species reassessed by IUCN since Sept 2024")

    found = collections.defaultdict(list)
    for site, text in ex.blocks():
        for sent in re.split(r"(?<=[.;])\s+", text):
            for g, e in ex.BINOMIAL.findall(sent):
                n = f"{g} {e}"
                if n in moved:
                    found[n].append((site, sent, text))

    scored = []
    for n, hits in found.items():
        site, sent, text = max(hits, key=lambda h: (
            bool(re.search(r"known only|confined to", h[1], re.I)), len(h[1])))
        tier, label, silence, threats, prot = ex.score(sent, text)
        scored.append({"species": n, "outcome": moved[n],
                       "threatened": moved[n] in THREATENED, "tier": tier,
                       "silence": silence, "threats": bool(threats),
                       "sentence": sent})
    print(f"located in book text: {len(scored)}\n")

    out = []
    def say(s=""):
        print(s); out.append(s)

    base_k = sum(1 for r in scored if r["threatened"])
    lo, hi = wilson(base_k, len(scored))
    say("=" * 72)
    say("VALIDATION: does restriction severity predict IUCN's own reassessment?")
    say("=" * 72)
    say(f"\nBase rate: {base_k}/{len(scored)} = {100*base_k/len(scored):.1f}% "
        f"came out threatened/extinct  (95% CI {100*lo:.0f}-{100*hi:.0f}%)")
    say("Reference points: ~28% of all assessed species are threatened;")
    say("                  Borgelt et al. 2022 predicted 56% for DD species.")

    say("\n--- by restriction tier (5 = type locality only) ---")
    say(f"{'tier':<6}{'n':>5}{'threatened':>12}{'rate':>9}   95% CI")
    for t in (5, 4, 3, 2, 1):
        g = [r for r in scored if r["tier"] == t]
        if not g:
            continue
        k = sum(1 for r in g if r["threatened"])
        lo, hi = wilson(k, len(g))
        say(f"{t:<6}{len(g):>5}{k:>12}{100*k/len(g):>8.0f}%   "
            f"{100*lo:.0f}-{100*hi:.0f}%")

    say("\n--- collapsed: high restriction (tier 4-5) vs rest ---")
    hi_g = [r for r in scored if r["tier"] >= 4]
    lo_g = [r for r in scored if r["tier"] < 4]
    for lbl, g in (("tier 4-5", hi_g), ("tier 1-3", lo_g)):
        if g:
            k = sum(1 for r in g if r["threatened"])
            a, b = wilson(k, len(g))
            say(f"  {lbl:<10} {k:>3}/{len(g):<4} = {100*k/len(g):>5.1f}%   "
                f"95% CI {100*a:.0f}-{100*b:.0f}%")

    # Fisher exact on the collapsed 2x2 -- small n, so report it explicitly.
    a, b = sum(1 for r in hi_g if r["threatened"]), sum(1 for r in hi_g if not r["threatened"])
    c, d = sum(1 for r in lo_g if r["threatened"]), sum(1 for r in lo_g if not r["threatened"])
    say(f"\n  odds ratio {(a*d)/(b*c):.2f}, Fisher exact two-sided "
        f"p = {fisher(a, b, c, d):.4f}")

    say("\n--- modifiers in isolation (these are why the composite was dropped) ---")
    for lbl, key in (("historical silence", "silence"), ("site threat named", "threats")):
        for val in (True, False):
            g = [r for r in scored if r[key] is val]
            if g:
                k = sum(1 for r in g if r["threatened"])
                say(f"  {lbl} = {str(val):<5} {k:>3}/{len(g):<4} = {100*k/len(g):>5.1f}%")

    say("\n--- where the tier 4-5 species actually landed ---")
    for c, n in collections.Counter(r["outcome"] for r in hi_g).most_common():
        say(f"  {n:>3}  {c}")

    with open(os.path.join(BUILD, "validation_report.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    with open(os.path.join(BUILD, "validation_set.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(scored[0])); w.writeheader(); w.writerows(scored)


if __name__ == "__main__":
    main()
