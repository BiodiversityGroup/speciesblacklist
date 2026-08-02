"""Shared helpers for the Species Black List pipeline."""
import csv, functools, json, os

BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "build_2026")

# Taxonomy arrives from three places with three conventions: IUCN shouts its
# class (ACTINOPTERYGII), GBIF sometimes returns a class that is really an order
# (Squamata) or nothing at all for fish, and the recovery paths fall back to
# order.  Left alone, the deliverable's class column mixes all three.  Everything
# is normalised to the eight vertebrate classes below.
CANON = {
    "ACTINOPTERYGII": "Actinopterygii", "ACTINOPTERI": "Actinopterygii",
    "CHONDRICHTHYES": "Chondrichthyes", "ELASMOBRANCHII": "Chondrichthyes",
    "HOLOCEPHALI": "Chondrichthyes", "AMPHIBIA": "Amphibia",
    "REPTILIA": "Reptilia", "SQUAMATA": "Reptilia", "TESTUDINES": "Reptilia",
    "CROCODYLIA": "Reptilia", "RHYNCHOCEPHALIA": "Reptilia",
    "AVES": "Aves", "MAMMALIA": "Mammalia", "MYXINI": "Myxini",
    "PETROMYZONTI": "Petromyzonti", "CEPHALASPIDOMORPHI": "Petromyzonti",
    "SARCOPTERYGII": "Sarcopterygii", "DIPNOI": "Sarcopterygii",
}


@functools.lru_cache(maxsize=1)
def order_to_class():
    """ORDER -> canonical class, learned from the IUCN index rather than hardcoded."""
    out = {}
    with open(os.path.join(BUILD, "iucn_2026_index.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cls = CANON.get(r["class"].upper())
            if cls and r["order"]:
                out.setdefault(r["order"].upper(), cls)
    return out


def normalise_class(value):
    """Map any class-ish or order-ish string onto one vertebrate class."""
    if not value:
        return ""
    # tolerate the "fish (Cypriniformes)" shape used by the NE paths
    v = value.strip().strip(")").split("(")[-1].strip().upper()
    return CANON.get(v) or order_to_class().get(v) or value.strip().title()


@functools.lru_cache(maxsize=1)
def _gbif_cache():
    p = os.path.join(BUILD, "gbif_cache.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def class_for(name, *candidates):
    """Best available class for a species, trying each candidate then GBIF.

    Species recovered by the audits often arrive with no class and no order --
    GBIF returns a class for them but not an order, and the audit output only
    carried order.  Falling back to the cached GBIF record fills those in
    (15 squamates, without this).
    """
    for c in candidates:
        got = normalise_class(c)
        if got:
            return got
    m = _gbif_cache().get(name, {})
    return normalise_class(m.get("class") or m.get("order") or "")
