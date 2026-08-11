# Reptile pilot — accepted species IUCN has never assessed

**Run 2026-08-08.** A test of whether the register can be extended beyond the Richardson
corpus by a stated, reproducible rule rather than by ad-hoc additions. Reptiles were
chosen because splitting has been most active in this class.

This is **not** part of the register. See "Why this cannot join List 2" below.

## The question that started it

*Crotalus polisi* and *C. thalassoporus* — two rattlesnakes with single-island ranges in
the Gulf of California — are unassessed. Should they go on the Black List, and are there
others like them?

## Sources

| | |
|---|---|
| Taxonomy | Reptile Database checklist **2026_06** (Uetz, Freed, Reyes, Kudera & Hošek), 12,650 accepted species |
| Assessed set | IUCN v2026-1, the three local exports, filtered to REPTILIA — **10,305** unique binomials |
| Verification | IUCN Red List API v4, per species |
| Cross-reference | GBIF backbone, for synonym resolution |

reptile-database.org serves no robots.txt (404), so nothing is disallowed. One bulk
checklist download was used rather than crawling species pages.

## Matching, and why not a plain name diff

METHODS §5 established that a failed name match cannot support an absence claim — the
book-derived NE list carried a **~90% false-positive rate** before verification. A
species is therefore counted as MATCHED here if *either* the binomial agrees, *or* the
specific epithet and the taxonomic authority (first author surname + year, ±1) agree.
That second test is the one that caught *Aphanius* / *Apricaphanius*: author and year
travel with a name through every generic revision.

It earned its place. The authority test matched **169 species** that a binomial-only
diff would have reported as gaps.

```
12,650  Reptile Database accepted species
 9,816  matched on binomial
   169  matched on epithet + authority   <- would have been false gaps
 2,665  unmatched CANDIDATES
 1,780  of those described 2015 or later
```

## Verification — a stratified sample of 100

Candidates are not findings. Each sampled species was resolved against the IUCN API,
which gives three outcomes: **CONFIRMED_GAP** (IUCN knows the taxon, holds zero
assessments — airtight), **NOT_IN_INDEX** (IUCN returns no taxon), and **FALSE_POSITIVE**
(IUCN holds an assessment; our diff was wrong).

NOT_IN_INDEX is not proof of a gap — IUCN may hold the animal under another genus — so
every one was re-checked against GBIF synonyms and re-queried under each alternative
name. That second pass converted **3 more** to false positives.

| stratum | n | airtight | standing | false | real-gap rate |
|---|---|---|---|---|---|
| described 2015+ | 45 | 26 | 15 | 4 | **91%** |
| 2000–2014 | 25 | 20 | 2 | 3 | 88% |
| pre-2000 | 30 | 15 | 6 | 9 | 70% |
| **all** | 100 | 61 | 23 | 16 | **84%** |

The rate is far better than the book-derived list's because the Reptile Database is a
curated taxonomic authority carrying authority strings, not species names extracted from
prose. Older candidates are dirtier, as expected from synonymy drift — which is why the
target population is the recent one.

**A limit on the "standing" column, stated because it is easy to miss.** Of the 26
NOT_IN_INDEX names, GBIF has never heard of **10**. For those the synonym check is
vacuous — it found no alternatives because no cross-reference exists, not because the gap
was confirmed. Those rest on the Reptile Database alone. The instrument itself was
validated before this was believed: `alt_names()` correctly returns *Cyprinodon/Lebias*
for *Aphanius iberus* and *Troglichthys rosae* for *Amblyopsis rosae*.

## Full verification — all 1,780 candidates described 2015 or later

The sample estimate was replaced with a per-species result. Every candidate was resolved
against the IUCN API, and every "not in index" verdict then went through the GBIF synonym
second pass.

| Evidence | n | % | what it means |
|---|---|---|---|
| **Airtight** | **1,179** | 66.2% | IUCN indexes the taxon and holds **zero** assessments |
| **Corroborated** | 249 | 14.0% | IUCN does not index the name; GBIF does; no assessed synonym found |
| **Uncorroborated** | 301 | 16.9% | neither IUCN nor GBIF indexes the name — rests on the Reptile Database alone |
| False positive | 51 | 2.9% | IUCN holds an assessment; the diff was wrong |

**1,729 of 1,780 (97.1%) are genuine gaps.** The false-positive rate of **2.9%** should be
read against the book-derived NE list's ~90% before verification — the difference is
entirely the source. A curated taxonomic authority carrying authority strings supports an
absence claim in a way that names extracted from prose never did.

The 301 uncorroborated are almost certainly gaps — a name IUCN's index does not contain
cannot have been assessed under that name — but the synonym check cannot run on them,
because GBIF has not caught up with the description either. They are single-source and
labelled as such rather than counted with the rest.

Of the 552 that IUCN did not index, the second pass found only **2** assessed under a
synonym. That is a far cleaner result than the equivalent check on the book corpus, and
for the same reason.

## Where the gap concentrates (described 2015+)

| family | n | | genus | n |
|---|---|---|---|---|
| Gekkonidae | 548 | | *Cyrtodactylus* | 163 |
| Colubridae | 250 | | *Cnemaspis* | 93 |
| Scincidae | 158 | | *Hemiphyllodactylus* | 57 |
| Agamidae | 93 | | *Liolaemus* | 55 |
| Viperidae | 68 | | *Hemidactylus* | 46 |

By order: Sauria 1,279, Serpentes 479, Testudines 21, Crocodylia 1.

## The mechanism — better than "newly described"

Being unassessed shortly after description is partly ordinary pipeline latency. The
sharper failure is **taxonomic splitting**, where a wide-ranging parent keeps its
assessment and the narrow-range daughters inherit nothing.

**The king cobra.** IUCN holds exactly one assessment in *Ophiophagus*: *O. hannah*,
**Vulnerable, 2012**. In 2024 the king cobra was split into four species. Three —
*O. bungarus*, *O. kaalinga*, *O. salvatana* — have **no Red List status at all**, and the
2012 assessment, made when this was one wide-ranging animal, is still doing duty for all
of them. Each daughter holds a fraction of the original range, so an assessment built on
the combined range almost certainly understates the risk to each part.

**The rattlesnakes that prompted this.** The Baja speckled rattlesnake complex was
assessed once, in **2007**: *C. mitchellii* LC, *C. angelensis* LC, *C. enyo* LC,
*C. catalinensis* CR. In 2018 Meik et al. split two single-island endemics out of it —
*C. polisi* (Cabeza de Caballo Island) and *C. thalassoporus* (Piojo Island). Both
unassessed. So is *C. pyrrhus*. A 19-year-old Least Concern assessment of a wide-ranging
parent now stands in front of island endemics nobody has evaluated, and its LC status is
why nobody looks.

That is a blind spot with a mechanism, not a backlog.

## Why this cannot join List 2

List 2 is defined as *species Richardson's corpus treats as threatened that IUCN has
never assessed*. Its defensibility rests on every member being there because **he** judged
it at risk, with IUCN's later verdicts held out as an independent test of that screen.
Species selected by us have no such test.

The corpus was checked rather than assumed: it contains **zero** mentions of *polisi*,
*thalassoporus*, either island, or the speckled rattlesnake complex. Richardson does cover
*Crotalus catalinensis*, a Gulf island endemic, so this is not him ignoring the category —
the 2018 split simply post-dates his reach.

METHODS §1 already anticipates this: *"Extending coverage now requires a second corpus,
not better extraction."* This pilot is that second corpus. It must publish as a separate
list with its own rule, never folded into the register — the register's argument is about
the **back** of the pipeline (repeated non-conclusion, median 16 years), and this one is
about the **front**. Blending them would dilute the stronger claim.

## Restriction — how narrow are they?

Two inputs, deliberately kept separate. **Distribution text** comes from the Reptile
Database species page, which transcribes it from the original description and cites the
describing paper (*C. polisi*'s entry reads "Figure 5 in Meik et al. 2018"). One light
page per species, rate-limited to 1.2 s, rather than chasing 1,600 mostly-paywalled PDFs.
**Occurrence geography** comes from GBIF: distinct sites rounded to ~1 km, and the
greatest distance between them.

Scoring restriction from the text alone put **74% of species into a single bucket** —
"Country (OneState)" — because the source string does not say whether an animal occupies
one ridge or a 53,000 km² state. That is a property of the text, not of the species, so
occurrence geography was added to break the lump apart.

| Class | n | what the evidence supports |
|---|---|---|
| **A** island endemic | 73 | confined to one island; independent of collecting effort |
| **B** tight cluster | 27 | ≥3 georeferenced sites within ≤10 km — narrow *on* evidence |
| **C** one site only | 213 | consistent with a narrow range, but undersampling of a recent description cannot be excluded |
| **D** wider than 10 km | 301 | not narrowly restricted on current evidence |
| **E** not restricted | 288 | more than one country, or >200 km across |
| **F** unknown | 827 | GBIF holds no usable coordinates |

**The A/B versus C split is the important one.** For a species described in 2023, "one
known site" may mean a narrow range or may only mean nobody has looked twice, so those
are held separately rather than counted as restricted. Class A does not depend on
sampling at all. Class B is sampling-robust: three or more records inside 10 km is
evidence of a tight range, not an absence of evidence.

**There is no priority stratum, because the validation refused it.** An earlier draft of
this section called the 70 airtight class-A/B species a priority list. See the validation
section below: the classes at the top of the scale do not predict threat, so that label
was withdrawn before publication.

**Class F is 48% of the list and must not be read as "widespread".** It means GBIF has no
coordinates, which for very recent descriptions is the normal state. Restriction there is
unknown, and the site labels it that way.

## Validation of the restriction classes — a negative result

The list cannot validate itself: its species have no Red List outcome by definition. So
the same scorer was run over reptiles that **do** carry a category, and asked directly
whether narrower species come back threatened more often. This mirrors METHODS §4.

**Design.** A seeded *random* sample of 600 from the 8,750 assessed reptiles with a
determinate category — not a chosen set. The scorer read Reptile Database text and never
saw the IUCN category. Data Deficient was **excluded from the denominator**: it is an
absent outcome, not a "not threatened" one. Base rate among the pool: 21.1% threatened.
571 of the 600 scored to a usable tier. Stated in advance: *if threatened rates are flat
across tiers, the ranking carries no information and must not be published as a priority
ranking.*

The statistics were themselves checked first. The Fisher implementation reproduces the
register's published figures exactly — OR 4.23, p 0.0016 on the n=140 table. That check
caught a mis-specified comparison group in my first attempt (6/28 instead of 24/112),
which had given p = 0.0261; without testing against a known answer the wrong table would
have been carried into this validation.

| tier | n | threatened | rate | 95% CI |
|---|---|---|---|---|
| 5 island endemic | 41 | 8 | 19.5% | 10.2–34.0% |
| 4 named landform | 12 | 7 | 58.3% | 32.0–80.7% |
| 3 one country, one unit | 172 | 52 | 30.2% | 23.9–37.5% |
| 2 one country, several units | 88 | 18 | 20.5% | 13.3–30.0% |
| 1 multi-country | 258 | 34 | 13.2% | 9.6–17.9% |

| comparison | rates | OR | p |
|---|---|---|---|
| single-country vs multi-country | 27.2% vs 13.2% | 2.46 | **0.000048** |
| tier 3 vs rest | 30.2% vs 16.8% | 2.15 | **0.00046** |
| tier 4–5 ("priority") vs rest | 28.3% vs 20.1% | 1.57 | 0.16 |
| tier 5 (island) vs rest | 19.5% vs 20.9% | 0.92 | **1.0** |

**What holds.** Endemism to a single country predicts threat, roughly doubling the odds,
and it is the only ordering this list can defend. It is not nothing: it separates 1,441
species from 288.

**What fails, and why.** The claimed priority stratum is not significant, and the top
class carries **literally no information** — an odds ratio of 0.92 at p = 1. The cause is
diagnosable rather than mysterious. "Island endemic", detected from distribution text,
conflates a 1 km² islet with Hainan (34,000 km²), takes in whole archipelagos (Ryukyus,
Andamans, Socotra plus three neighbours), and admits at least one outright false
positive: *Psomophis joberti*, a mainland Brazilian snake whose distribution merely
*mentions* Marajó Island. A class spanning four orders of magnitude of area is not
measuring restriction.

**What was NOT done about it.** The tempting move is to tighten the island rule and
re-test until it clears p < 0.05. That is p-hacking on the same sample, and the register's
credibility rests on not doing it. The negative is recorded, the priority label is
withdrawn, and the classes are published as *descriptive*. A tightened island definition
— single named island, area bounded, incidental mentions excluded — would need testing on
a **fresh** sample before any priority claim is made again.

This is the same discipline METHODS §1 already applied when the duration analysis showed
the priority tiers had *not* waited longer than the rest: a tested claim that fails is
recorded, not quietly dropped.

## The website

Published as a separate page at `/new-species/`, not merged into the register. The page
opens with a box headed "This is not the register" explaining that the two answer
different questions and must never be summed. Data lives in `site/reptiles.json`;
`14_build_pages.py` gained the route and `MUST_BE_ABSOLUTE` gained `/reptiles.json`.

## Localities are withheld from the public data — and why the coordinates were suspect anyway

Scott (2026-08-08): **it is common practice in new reptile and amphibian descriptions to
obscure or falsify the type locality to deter poaching.** That has two consequences and
both matter.

**Publication risk.** `site/reptiles.json` was about to ship with **1,307 coordinate
pairs and 1,725 exact type localities** for narrowly restricted reptiles that the Red
List has never assessed — so no listing triggers any legal protection for them — with
island-endemic geckos and vipers prominent among them. Scattered across separate
descriptions those localities are hard to exploit; gathered into one downloadable file
they are a collecting list. **The aggregation is the harm, not any single record.**

The public payload now carries the distribution statement only (country, state, island —
what the Reptile Database already publishes and what is inseparable from calling a species
restricted) and drops every coordinate and exact type locality. The full data lives in
`build_2026/reptiles_full.json`, which is not served. The build asserts that no
coordinate-shaped string survives into the public file, so a future edit cannot quietly
reintroduce them.

**Measurement consequence.** The geocoder accuracy figure below used published
coordinates as ground truth. If an unknown share of those are deliberately wrong, the
measured error is an **upper bound**: some of that 167 km is the describer's obfuscation
rather than the geocoder's failure. Neither source can be trusted to the kilometre, which
is a further reason not to publish points from either.

## Geocoding the remaining type localities — measured, and not yet usable

97 of the 186 unresolved species geocoded to something that passed a country check and an
extent check. That sounded like progress until it was measured against the 1,307 species
whose descriptions print coordinates:

| | |
|---|---|
| median error | **166.6 km** |
| 75th percentile | 653 km |
| 90th percentile | 1,596 km |
| worst | 2,758 km |
| within 10 km | 4 of 27 (15%) |

The fault was the verification, not the gazetteer. Country agreement admits an error as
wide as the country, and the fallback chain manufactured exactly that: when a precise
query failed it retried with *place + country* and found homonyms elsewhere —
*Erythrolamprus rochai*'s locality in Amapá matched a same-named place in Mato Grosso do
Sul, *Gekko mizoramensis* in Mizoram matched Gujarat, mainland Azuay matched the
Galápagos. All three passed as "verified".

Every candidate query now carries the state named in the distribution field, and results
must match that state. Re-measurement on a **different** 45 species is outstanding. Until
that number exists, **the geocoded points are not used and not published**, and the 186
remain "restriction unknown".

## The island re-test — inconclusive, not a refutation

Run once on a fresh sample of 600 assessed reptiles with **zero overlap** with the first
600, against a rule frozen before the sample finished downloading.

| | |
|---|---|
| small-island endemics found | **3** of 579 |
| island threatened | 2/3 = 66.7% |
| rest threatened | 121/576 = 21.0% |
| odds ratio | 7.52 |
| p | **0.116 — not significant** |

The direction is strong and the sample is far too small to lean on. This is materially
different from the first result: the **unbounded** rule was genuinely refuted (n=41,
OR 0.92, p=1), while the bounded rule is **untested** — it qualifies roughly 0.5% of
species, so powering it would need most of the assessed reptile fauna rather than a
600-species sample. *No evidence of an effect*, not *evidence of no effect*.

**A first run of this test was void and is not reported as a null.** It returned zero
qualifiers because the island-name extractor looked up the wrong token: "Solomon Islands
(Rennell)" queried *Solomon Islands*, and "Socotra Island (Yemen)" queried *"Socotra
Island, Socotra Island"*. All 15 species that reached the gazetteer failed for that
reason. Re-running on the same sample was legitimate precisely because a void run leaks
no outcome information — no threatened rate was computed for any island group, so nothing
about the answer could bias the repair.

**One case was left failing rather than fixed.** Rarotonga (~67 km², ~11 km across) ought
to qualify, but OSM carries it as an administrative district whose bounding box spans
0.54° because island districts include territorial sea. `MAX_ISLAND_SPAN` was **not**
raised to 0.6° to admit it: the threshold was fixed in advance and moving it to capture a
case already inspected is tuning. The rule therefore under-counts small islands that are
their own administrative unit, biasing toward false negatives.

## Known limitations

- Restriction rests on two sources of differing quality; see the section above. Nearly
  half the list has no usable geography at all.
- "Never assessed" is measured against v2026-1. Species assessed after that ship as false
  positives until the export is refreshed.
- The 10 GBIF-unknown names have no independent corroboration.
- Splits are inferred case-by-case. The checklist's `changes` column covers only the
  current release (119 rows), so split history is not machine-readable from this source.

## Artifacts

In the session scratchpad:
`reptile_checklist_2026_06.xlsx`, `reptile_pilot_diff.py`, `reptile_candidates.json`,
`reptile_verify.py`, `reptile_verify_results.json`, `reptile_resolve_notinindex.py`,
`reptile_notinindex_resolved.json`, `reptile_verify_all.py`, `reptile_verified_all.json`.
