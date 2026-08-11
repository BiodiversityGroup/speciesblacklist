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


# Place names that genuinely contain "and" and must not be split.
COMPOUND_OK = re.compile(
    r"^(?:Wallis and Futuna|Antigua and Barbuda|Trinidad and Tobago|"
    r"Turks and Caicos|Sao Tome and Principe|S[aã]o Tom[eé] and Pr[ií]ncipe|"
    r"Saint Vincent and the Grenadines|Bosnia and Herzegovina|"
    r"Heard and McDonald)", re.I)


def squash(s):
    """Whitespace only. Safe to run on a whole sentence."""
    return " ".join((s or "").split()).strip(" ,.;:")


def clean(s):
    """Normalise a captured PLACE NAME. Never call this on a sentence.

    squash() is the sentence-safe version; this one is place-name-specific.
    """
    n = squash(s)
    # Never end on a dangling connector: 'Madagascar and the' -> 'Madagascar'.
    # The connector list let a capture stop mid-conjunction; audit found 10 of these.
    n = re.sub(r"\s+(?:and|or|y|and the|or the)$", "", n, flags=re.I).strip(" ,")
    return n.strip(" ,.;:")


def is_compound(name):
    """True when the string names two places rather than one.

    Audit found 55: 'Athi and Tana River', 'Caroline and Marshall Islands'. They are
    LEFT INTACT rather than split, and merely withheld from geocoding, because every
    way of reducing them invents something:

        take the first component      'Caroline and Marshall Islands' -> 'Caroline'
                                      loses the noun that identified it
        carry the shared feature noun 'Oman and Masirah Island' -> 'Oman Island'
                                      'Turkana and the Omo River' -> 'Turkana River'
                                      fabricates places that do not exist

    A true-but-coarse locality beats a precise-sounding fiction, and the evidence
    sentence is shown in full anyway, so the reader sees both places.
    """
    # clean() first, so a capture merely ENDING on a connector ('Madagascar and the')
    # is repaired to one place rather than misread as two.
    n = clean(name)
    return bool(re.search(r"\s+and\s+", n, re.I)) and not COMPOUND_OK.match(n)


def locality_from_evidence(evidence, vernacular="", binomial=""):
    """(name, kind) or (None, None). kind is 'feature' or 'bare'."""
    e = squash(evidence)          # sentence-safe; clean() would truncate at "and"
    if not e:
        return None, None
    # Drop the parenthetical binomial so the species' own name cannot be captured.
    e = re.sub(r"\([^)]*\)", " ", e)
    vern = (vernacular or "").lower()
    # " ".split() is [], not [""], so indexing a blank binomial raises IndexError.
    genus = next(iter((binomial or "").split()), "\0").lower()

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
