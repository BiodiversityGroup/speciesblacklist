"""
Recover a locality from a species' own evidence sentence.

WHY THIS EXISTS
03_extract_and_score.py only assigns a locality when a species sits inside one of
Richardson's locality-headed paragraphs. When the place is named inline in the
species' own sentence instead, nothing was recorded -- which left 1,958 of 2,408
species (81%) with no locality, and made the Sites page a view of nineteen percent
of the register.

The place is almost always right there in the sentence already held:

    "... known only from a single specimen collected from South Cinque Island"
    "... known only from a single specimen collected off Mauritius"
    "... known only from a single specimen collected from the upper Pungwe River"

This is extraction from the source, not inference. Nothing here geocodes or guesses;
if the sentence does not name a place, the species keeps no locality.

PRECEDENCE
A named physical feature ("Salween River", "Gulf of Panama") is far more reliable
than a bare capitalised word after a preposition, so FEATURE patterns run first and
the looser BARE patterns only get a turn when they fail.
"""
import re

# Feature nouns Richardson uses for places, longest-first so "Seamount Chain" wins
# over "Seamount".
FEATURE = (r"Seamount Chain|Seamount|Archipelago|Peninsula|Mountains|Mountain|"
           r"Highlands|Escarpment|Depression|Plateau|Massif|Cordillera|Sierra|"
           r"Range|River|Stream|Creek|Lagoon|Lake|Swamp|Marsh|Spring|Springs|"
           r"Falls|Rapids|Cave|Caves|Sinkhole|Cenote|Island|Islands|Islet|Atoll|"
           r"Cay|Reef|Bank|Ridge|Rise|Trench|Basin|Valley|Gorge|Canyon|Delta|"
           r"Estuary|Bay|Gulf|Sound|Strait|Channel|Sea|Ocean|Desert|Forest|"
           r"National Park|Reserve|Volcano|Crater|Hills|Hill|Ranges|Drainage")

WORD = r"[A-Z][A-Za-zéíóáúñãõçöü'\-]*"
CONN = r"(?:de|del|do|da|dos|das|of|el|la|le|los|las|du|van|von|the|and|y)"

PATTERNS = [
    # "Gulf of Panama", "Sea of Japan", "Bay of Bengal"
    ("feature", rf"\b((?:Gulf|Sea|Bay|Lake|Strait|Isthmus|Bight|Firth|Loch)\s+of\s+{WORD}(?:\s+{WORD})?)\b"),
    # "Salween River", "South Cinque Island", "Sierra Madre del Sur"
    ("feature", rf"\b({WORD}(?:\s+(?:{WORD}|{CONN})){{0,3}}\s+(?:{FEATURE}))\b"),
    # "the upper Pungwe River" handled above; this catches "Lake Tanganyika"
    ("feature", rf"\b((?:Lake|Mount|Cape|Rio|Río|Isla|Islas)\s+{WORD}(?:\s+{WORD})?)\b"),
    # bare place after a collecting preposition: "collected off Mauritius"
    ("bare", rf"collected\s+(?:from|off|in|at|near|along|around)\s+(?:the\s+)?({WORD}(?:\s+(?:{WORD}|{CONN})){{0,2}})"),
    ("bare", rf"(?:known only from|confined to|endemic to|restricted to)\s+(?:the\s+)?({WORD}(?:\s+(?:{WORD}|{CONN})){{0,2}})"),
]

# Words that are never a locality even when capitalised in the right position.
STOP = {
    "the", "a", "an", "its", "his", "her", "their", "this", "that", "these",
    "type", "holotype", "original", "single", "only", "one", "two", "three",
    "several", "few", "some", "north", "south", "east", "west", "northern",
    "southern", "eastern", "western", "central", "upper", "lower", "middle",
    "coastal", "inland", "offshore", "deep", "shallow", "unnamed", "unknown",
    "specimen", "specimens", "collection", "collections", "series", "locality",
    "localities", "site", "sites", "record", "records", "population",
    "populations", "museum", "expedition", "century", "nineteenth", "twentieth",
    "eighteenth", "described", "reported", "recorded", "collected", "found",
    "probably", "possibly", "apparently", "recently", "formerly", "it", "he",
    "she", "they", "there", "where", "which", "who", "and", "or", "but",
}
# A capture must not be, or start with, one of these.
BAD_START = re.compile(r"^(?:" + "|".join(sorted(STOP, key=len, reverse=True)) + r")\b",
                       re.I)


def clean(s):
    """Collapse the runs of whitespace the .doc conversion left behind."""
    return " ".join((s or "").split()).strip(" ,.;:")


def locality_from_evidence(evidence, vernacular="", binomial=""):
    """(name, kind) or (None, None). kind is 'feature' or 'bare'."""
    e = clean(evidence)
    if not e:
        return None, None
    # Drop the parenthetical binomial so the species' own name cannot be captured.
    e = re.sub(r"\([^)]*\)", " ", e)
    vern = (vernacular or "").lower()
    genus = (binomial or " ").split()[0].lower()

    for kind, pat in PATTERNS:
        for m in re.finditer(pat, e):
            cand = clean(m.group(1))
            if len(cand) < 3 or BAD_START.match(cand):
                continue
            low = cand.lower()
            # reject the species' own vernacular or genus bleeding through
            if low in vern or vern.startswith(low) or low == genus:
                continue
            if any(w.lower() in STOP for w in cand.split()[:1]):
                continue
            # a single bare word that is also a normal English word is too risky
            if kind == "bare" and " " not in cand and low in STOP:
                continue
            return cand, kind
    return None, None
