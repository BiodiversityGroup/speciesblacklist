# The Species Black List — Methods

**The Biodiversity Group** · pipeline rebuilt August 2026 against IUCN Red List v2026-1

---

## 1. What this project claims

Two claims, deliberately kept separate because they are not equally strong.

**List 1 — Data Deficient: 3,031 species**, of which **1,123 are tranche A**, the
validated priority stratum. IUCN has assessed these and returned *we don't know*. A
Cambridge University Press reference documents most of them as narrowly restricted,
often to a single river or a single collecting event. Ranked by how severe that
restriction is.

**List 2 — Not Evaluated: 35 species.** IUCN has never assessed these at all, yet the
same reference treats them as threatened or recently extinct. Small because the claim
is hard to make safely — see §5.

### What the register is a sample OF

This belongs before any figure above is quoted. **IUCN v2026-1 holds 8,659 Data Deficient
species in vertebrate classes. This register covers 3,031 of them — 35%.**

The remainder is accounted for exactly, because an earlier version of this section got it
wrong. The claim was that the missing species lay outside the corpus. Checking it rather
than asserting it — pull every binomial out of the book and intersect with IUCN's DD list —
showed that 521 of them were named in the book and lost by the pipeline, because the name
list it worked from held full binomials only and Richardson names hundreds of species
solely as an abbreviated congener (*"A. leurolepis"*). Those are now recovered (§6), and
the accounting closes:

| | |
|---|---|
| IUCN DD vertebrates, v2026-1 | 8,659 |
| named anywhere in the corpus | 2,964 |
| of those, in the register | **2,964 — all of them** |
| never named in the corpus | 5,695 (66%) |
| register total, incl. synonym and rank recoveries | 3,031 |

So the honest statement is narrow and checkable: **every Data Deficient vertebrate this
corpus names is in the register, and two thirds of IUCN's DD vertebrates are not in the
corpus at all.** This is **a ranked subset, not a census of the problem.** Nothing here
licenses "these are the DD vertebrates that matter most" — only "of the DD vertebrates with
a usable published range statement, these are the most narrowly restricted." The 5,695
outside are not judged lower priority; they are unexamined, and extending the corpus is the
largest single improvement available to this project.

Both lists exist because Data Deficient and Not Evaluated species are excluded from
conservation in practice and, in one case, by treaty language. Target 4 of the
Kunming-Montreal Global Biodiversity Framework commits to halting the extinction of
*known threatened species* — a phrase that excludes both categories by definition.
Under 3.5% of Mohamed bin Zayed Species Conservation Fund awards have gone to Data
Deficient taxa; under 1% at the People's Trust for Endangered Species. IUCN's own
guidance says DD species should receive the same attention as threatened ones, and
it is not followed.

**What this project is not.** These are not Red List assessments and must never be
presented as such. They are a prioritised research agenda: a defensible ranking of
where assessment effort would most likely convert a blank into a threatened listing.

---

## 2. Sources

| Source | Detail |
|---|---|
| Species corpus | Matthew Richardson, *Threatened and Recently Extinct Vertebrates of the World: A Biogeographic Approach*, Cambridge University Press, 2023. Working copy is the January 2022 final manuscript. Vertebrates only — the scope of this project follows the scope of the book. |
| Extinction risk | IUCN Red List **v2026-1**, obtained as a Darwin Core Archive from GBIF's mirror (`hosted-datasets.gbif.org/datasets/iucn/iucn-latest.zip`, published 2026-07-28). 178,011 taxa. No API key required. |
| Taxonomic backbone | GBIF Backbone Taxonomy via the public `species/match` API, for synonym resolution and higher classification. |
| Independent verification | GBIF's curated backbone-to-IUCN linkage (`species/{key}/iucnRedListCategory`), which is built independently of name-string matching. |

**Required citation** when any of this is published:
> IUCN (2026). *The IUCN Red List of Threatened Species.* Version 2026-1.
> https://www.iucnredlist.org — doi:10.15468/0qnb58, accessed via GBIF.org.

IUCN Red List Terms of Use apply and a copy sits in each of the legacy export folders.

---

## 3. Pipeline

Scripts in `scripts/`, outputs in `build_2026/`. Run in order; all are idempotent and
GBIF responses are cached, so reruns are free.

Idempotence was not free. 08 and 09 originally read the same published list they
rewrote, so a second run read a list from which its own exclusions had already been
removed, found nothing left to exclude, and overwrote `prehistoric_extinctions.csv` with
just that run's single finding — deleting the record of the other seven. The exclusion
logs *are* the audit trail, so a rerun quietly truncating them is a correctness bug, not
untidiness. 07 now writes candidate files and 08/09 own the published ones; verified
stable over four consecutive runs.

| Script | Does |
|---|---|
| `01_build_iucn_index.py` | Parses the DwC-A into a flat name → category index. Carries family and order, without which the audit in 06 cannot run. |
| `02a_expand_corpus.py` | Resolves the corpus's abbreviated genus names and recovers the species reachable only that way. **Run before 02** — it supplies 3,430 names the 2024 list lacks. |
| `02_refresh_and_diff.py` | Cross-references the 12,592 book names against v2026-1 and diffs against the September 2024 baseline. |
| `03_extract_and_score.py` | Re-extracts evidence using the book's biogeographic structure and scores geographic restriction. |
| `04_validate_score.py` | Tests the score against species IUCN reassessed independently. **Run this before trusting anything downstream.** |
| `05_triage_unmatched.py` | Resolves names absent from IUCN against the GBIF backbone. |
| `06_audit_false_negatives.py` | Catches species IUCN files under a different genus or family. |
| `07_assemble.py` | Builds both lists, as `dd_candidates.csv` / `ne_candidates.csv`. |
| `08_verify_ne.py` | Independent confirmation of the NE list; splits off pre-1500 extinctions. Reads 07's candidates and **owns** the published `SPECIES_BLACK_LIST_ne.csv`. |
| `09_verify_dd.py` | Same verification applied to the DD list, and owns `SPECIES_BLACK_LIST_dd.csv`. |
| `10_build_site.py` | Builds `site/data.json`: register payload, recovered common names, cleaned localities, site metadata. |
| `11_make_og.py` | Draws the shared-link preview card. **Needs Pillow** — the only script with a third-party dependency. |
| `12_build_map.py` | Fetches georeferenced GBIF occurrence points per species plus the Natural Earth basemap → `site/map.json`. |
| `13_geocode_localities.py` | Geocodes the locality names and cross-checks each against real records → `site/geo.json`. |
| `14_build_pages.py` | Writes the four sub-pages from `site/index.html` and regenerates the sitemap. **Run after any edit to index.html.** |
| `15_check_figures.py` | Anchored check that every figure in the prose still matches the data. Non-zero exit gates the deploy. |
| `_locality.py` | Shared: recovers a locality from a species' own evidence sentence, and flags the compound names that must never be geocoded. |
| `_common.py` | Shared: class normalisation, and the sentence splitter. Segmentation lives here because 03, 04, 07 and 10 all divide the same corpus — and 04 is the held-out test, so if they disagree the test scores a classifier that is not the published one. |

The 21 MB source archive is treated as a cache artifact and kept out of Dropbox. Pass
its path to script 01, or drop it in `%TEMP%`.

---

## 4. Scoring, and the validation that shaped it

### Why restriction rather than threat keywords

The 2024 pipeline kept one sentence per species. Mining those sentences shows 73%
say *known only from* and under 1% mention any threat driver. That is not a gap in
the book — it is the book's structure. Richardson organises biogeographically:

```
The Luhoho River is located in central-eastern Democratic Republic of Congo.
The Luhoho yellowfish (Labeobarbus longifilis) ... known only from the Luhoho.
The Luhoho shellear (Parakneria kissi) is confined to the Luhoho River.
```

The locality paragraph carries the place and its threats; the species line carries
the restriction. Keeping only the species line discards half the evidence, so the
rebuilt extraction keeps the whole block and records which site each species belongs
to. All 3,031 DD species were located in the text.

Restriction is the primary axis because IUCN **Criterion B** lets a species qualify
as threatened on a small range plus decline or fragmentation: area of occupancy under
2,000 km² for Vulnerable, 500 for Endangered, 10 for Critically Endangered. A species
*known only from its type locality* sits prima facie inside the CR envelope for B2.
That is the strongest defensible claim this corpus can make.

The tiers describe **what kind of range statement the record contains**, from narrowest
to broadest. They are numbered, but see the validation below: the numbering is *not* a
validated severity order at the top of the scale.

| Tier | Basis | Priority |
|---|---|---|
| 5 | Type locality, original collection, or a single specimen | yes |
| 4 | A single named site — one river, cave, spring, island, massif | yes |
| 3 | A single drainage, archipelago, or mountain range | yes |
| 2 | Restricted, extent unclear | no |
| 1 | No restriction statement | no |

Tier order is decided by testing tier 3 **before** tier 4, because tier 4's wording list
contains *river* and would otherwise claim *"confined to the Kapuas River drainage"* — a
basin the size of a country — as "a single named site". A drainage named only as context
for a real point (*"a single locality within the Ganges River drainage"*) still scores 4.

### The validation

Between the 2024 export and v2026-1, IUCN independently reassessed **140** of the book's
DD species. Those 140 are a held-out labelled set the scoring rules never saw.

| | n | threatened or extinct | 95% CI |
|---|---|---|---|
| **Tier 3–5** (priority) | 28 | **53.6%** | 36–70% |
| Tier 1–2 | 112 | 21.4% | 15–30% |
| *All 140* | *140* | *27.9%* | *21–36%* |

**Fisher exact two-sided p = 0.0016, odds ratio 4.23.**

Two things follow. First, restriction severity does agree with IUCN's own verdict.
Second, the tier 3–5 rate lands on the 56% that Borgelt et al. (2022, *Communications
Biology*) predicted for DD species generally — which suggests that figure belongs to the
narrowly restricted subset, and that a flat DD list dilutes a real signal with vague-range
species.

Read the base rate honestly: taken flat, the 140 came out threatened at 27.9%, which is
the ordinary all-species rate of roughly 28%. **The unranked premise does not hold.** The
ranking is what makes the list defensible, not the DD status by itself.

### Where the boundary sits, and why it is not at the top of the scale

The priority stratum is tiers 3–5. That is an empirical choice, and the reason is visible
only when the tiers are read individually rather than collapsed:

| Tier | n | threatened | 95% CI |
|---|---|---|---|
| 5 — type locality / single specimen | 15 | **40%** | 20–64% |
| 4 — single named site | 10 | **70%** | 40–89% |
| 3 — single drainage / archipelago | 3 | **67%** | 21–94% |
| 2 — restricted, extent unclear | 97 | **20%** | 13–29% |
| 1 — no restriction statement | 15 | **33%** | 15–58% |

**The discontinuity is between tier 2 and tier 3 — 20% to 67% — not between 3 and 4.**
There is no evidence that a single named site carries more risk than a single drainage
(70% vs 67%). Testing all four available cut points says the same thing:

| Cut | priority | rest | OR | p |
|---|---|---|---|---|
| tier ≥5 | 6/15 = 40.0% | 33/125 | 1.86 | 0.3594 |
| tier ≥4 | 13/25 = 52.0% | 26/115 | 3.71 | 0.0057 |
| **tier ≥3** | **15/28 = 53.6%** | **24/112** | **4.23** | **0.0016** |
| tier ≥2 | 34/125 = 27.2% | 5/15 | 0.75 | 0.7609 |

Tier ≥3 wins on every measure — higher rate, higher odds ratio, smaller p, larger tested
n — and it survives Bonferroni across all four cuts (0.0016 × 4 = 0.0064).

It has one further property that decided the matter. A species moved between tier 3 and
tier 4 stays inside tier 3–5, so **the priority list no longer depends on the tier 3/4
regex boundary at all** — a distinction the data cannot support and which was, until this
audit, being drawn incorrectly for 73 species.

**Tier 5 is the awkward result and it is not dismissed here.** At 40% it sits below both
tier 4 and tier 3, so the scale is not monotonic where it is supposed to be strongest. The
difference is not significant on this n (tier 5 vs tier 4, p = 0.23), but the direction has
a mechanism: *"known only from a single specimen"* measures **survey effort as much as
range size**. For a cave fish the two coincide; for a deep-sea snailfish trawled once, one
specimen is evidence of a barely-sampled ocean, not a small range. The corpus wording lets
this be probed only weakly — tier-5 species whose sentence carries deep-sea or offshore
language came out 0/2 against 6/13 for the rest, which is far too thin to claim, and only
5% of register tier-5 species use such wording. So the mechanism is plausible, untested,
and stated as a caution: **tier 5 should not be read as "worse than tier 4"**, and the tier
numbering is a description of evidence type, not a validated risk ordering.

### What validation killed

A composite score was built first, adding points for historical silence and named
site-level threats. Validation destroyed it: the composite was non-monotonic (score 4
→ 78% threatened, score 5 → 17%), and naming a site-level threat turned out
*inversely* associated with being threatened (OR 0.56). The reason is legible in
hindsight — broad, well-documented regions attract threat prose but hold
wide-ranging species, while a genuine type-locality endemic gets one terse line.
Historical silence pointed the right way but on n=6 (OR 1.46), far too thin to rank
on. Both survive in the output as descriptive columns. **Ranking is on restriction
tier alone.**

### The tier patterns were widened after the validation was run — disclosed

This matters enough to state plainly rather than bury. The held-out test above was run
first. A later audit then found the tier patterns were **under-matching**: the book
phrases a restriction many ways, and the patterns covered only *"known only from"* and
*"confined to"*. Two rounds of widening followed:

| Round | What was being missed | Tier 1 before → after |
|---|---|---|
| 1 | *"known for certain only from"* (26 cases), *"only definitely known from"*, *"known from a few localities"* | 279 → 245 |
| 2 | a varied or absent preposition: *"known only **by** a single specimen"*, *"known only **in** a small area"*, *"known only two localities"*, *"known only its original collection"* | 245 → 227 |
| 3 | not a pattern at all — the **sentence splitter** cut at an abbreviated genus, so *"the Assam perch (B. | assamensis) are both known only from…"* lost its restriction to the discarded half | 226 → 147 |

Changing a classifier after seeing its test result is how test sets get quietly tuned,
so the guard is this: **the published validation figures did not move, in any of the
three rounds.**
Tier 4–5 stayed at 10/19 = 52.6%, tier 1–3 at 20.2%, p = 0.0075, OR 4.38 every time.
Each round moved species *within* the collapsed tier 1–3 group and none across the 4–5
boundary the headline rests on. Round 3 is the strongest form of that check, because it
changed the segmentation of the validation set itself (its tier 2 went 69 → 75) and the
collapsed result still did not budge. The result cannot be an artefact of the fixes — had
it been, it would have changed when they landed.

The widenings are corrections to the *code*, not the *definitions*. Tier 4 was defined in
advance as "a single named site"; *"known for certain only from the Mahananda River"*
plainly satisfies that as written, and failing to match it was a bug. The tier definitions
are unchanged from before the test was run. What did change is the register: tranche A
grew from 795 to **843** across the three rounds, as restrictions the code had been
missing were recognised.

A residual false-positive risk was checked rather than assumed. Requiring *"only"* or an
explicit certainty word is what keeps the widened pattern from matching a bare *"is known
from the Amazon basin"*, which would collapse tier 2 into a catch-all; and restricting the
optional preposition to *from / by / in / at* is what keeps *"is only known **to** occur
seasonally"* out. Only 3 sentences in the whole corpus use the prepositionless form, and
all 3 were inspected individually.

### What the validation does NOT establish

Four qualifications, each measured rather than asserted. None of them overturns the
result; together they set how hard it can be leaned on.

**1. The tested sample is not a random draw from the register.** IUCN does not choose
which DD species to resolve at random — a reassessment follows funding, a specialist
group, or somebody's fieldwork. The 140 are **20.0% tier 3–5 against 37.1% in the
register** (Fisher p = 0.00003). Reassessment effort is going disproportionately to the
vague-range species and leaving the narrowly restricted ones unresolved. That is itself a
finding in the project's favour, and it means the tier 4–5 rate is estimated on a stratum
IUCN sampled non-randomly. Whether the 19 they happened to pick were already suspected of
being threatened cannot be tested from here.

**2. It rests on 28 species.** One species is worth 3.6 percentage points. **The honest
statement of the result is the interval 36–70%, not the point estimate**, and "53.6%"
should never be quoted to one decimal without it.

**3. Predictor and outcome are not independent sources.** Richardson compiled from the
primary literature and specialist-group material; an assessor writing the same species'
account draws on the same papers and may well have read Richardson. So this is agreement
between two readings of one literature, not a blind prediction against ground truth. The
time order is sound — every outcome postdates the January 2022 manuscript, so no answer
leaked into the predictor — which is what makes the test worth running. But
*"predicts IUCN's own verdict"* overstates it; *"agrees with"* is accurate.

**4. The chosen cut is not the strongest one.** Of the four monotone cut points, two are
significant, and tier ≥3 tests **better** than the published tier ≥4 (OR 5.25, p = 0.0018
vs OR 4.38, p = 0.0075). Tranche A is 4–5 because Criterion B's area-of-occupancy
thresholds motivate it a priori, not because it maximised the statistic — had the cut been
chosen to fit the test, tier ≥3 would have been picked. Bonferroni across all four cuts
leaves the result significant (0.0018 → 0.0072). The corollary is that **tier 3 is a
defensible candidate for inclusion in the priority stratum** and is currently excluded on
theoretical rather than empirical grounds.

---

## 5. Corrections to the 2024 analysis

**The baseline was two years stale.** Of the 2,434 species DD in the 2024 export:
2,298 still DD, 108 reassessed, 28 no longer matchable. Publishing the original list
unchanged would have asserted DD status for 108 species IUCN had already moved.

**Name matching cannot prove absence.** This is the single most important finding of
the rebuild, and the reason the NE list is small. Deciding "IUCN has never assessed
this" by failing to find a name is unsound, because the two sources disagree about
placement constantly. Four distinct failure modes, each found by a different check:

| Failure | Example | Caught by |
|---|---|---|
| Genus reassigned | *Amblyopsis rosae* = IUCN *Troglichthys rosae* (NT) | epithet + family (06) |
| Genus **and** family reassigned | *Aphanius iberus* = IUCN *Apricaphanius iberus* (NT) | epithet + order (06) |
| Homonym within an order | *Sinosuthora przewalskii*, an Asian parrotbill, matching *Grallaria przewalskii*, a South American antpitta | GBIF confirmation of tier-2 hits (06) |
| Rank change | *Cyanoramphus cookii*, really LC | GBIF curated linkage (08) |

Attrition on the NE list, stage by stage:

```
680  book names absent from the IUCN index
373  classified as vertebrates, not noise or plants        (05)
368  unique after deduplication on accepted name           (05)
153  survive the genus/family/homonym audit                (06)
 43  survive independent GBIF verification                 (08)  -110
 35  after removing pre-1500 extinctions                   (08)   -8
```

**A cumulative false-positive rate near 90%.** Any future work asserting that a
species is unassessed must clear script 08 before the claim leaves the building.

**The Data Deficient list, put through the identical check, came back clean.** All
2,372 were verified: 2,364 confirmed DD by GBIF's independent linkage, 8 with no link
where our own index match stands, **none removed**. The contrast is the most useful
methodological result here and it is structural, not luck:

> A **positive** claim — *a record exists and it says DD* — is checkable against the
> record itself and survives verification. A claim of **absence** — *no record
> exists* — cannot be established by failing to find a name, because the two
> taxonomies disagree about placement constantly. Absence needs a curated
> cross-reference, and name matching is not one.

Practical consequence: List 1 can be quoted with confidence. List 2 is 35 species,
each individually verified, and should never be regenerated by name matching alone.

**Pre-1500 extinctions are out of scope, not neglected.** Richardson covers species
known only from subfossil remains — the St Croix macaw, the Madeira scops owl, the
New Zealand swan. The Red List only treats extinctions from 1500 AD onward, so these
fall outside its remit by published policy. They are split into
`prehistoric_extinctions.csv` and excluded from the headline. Presenting them as
coverage gaps would be a category error and would give a reviewer an easy way to
dismiss the whole list.

**Species were recovered, not just removed.** The audits found 67 species that are DD
under a name the original match never reached — 50 from the taxonomic audit, 17 from
the NE verification. All were folded into List 1 rather than discarded, which is why
it grew from 2,305 to 2,372 while the NE list shrank.

---

## 6. Localities

Recorded two ways, and the site distinguishes them.

**From a locality account (519 species).** Richardson organises geographically, so most
species sit inside a paragraph introduced by a place. That place, and its opening
sentence, attach to every species in the paragraph. The stronger provenance.

**From the species entry itself (1,213 species).** Where a species is not inside a
locality account, the place is usually named in its own sentence anyway — *"collected
from the upper Pungwe River"*, *"collected off Mauritius"*. `_locality.py` extracts
those. Named physical features are preferred over a bare capitalised word after a
preposition, and a capture is rejected when it collides with the species' own common
name or genus.

Coverage went from **19% to 60%** of the register (1,732 of 3,066) and the site list from
42 to 102. Clusters that were entirely invisible appeared — the Gulf of California holds
19 species, none of which had a locality before. **1,334 still have none**, because their
sentence names no place specific enough to record. Nothing is invented to fill that gap.

A later audit of the recovered localities found two more classes of defect in the captured strings, both
now handled. **Ten captures ended on a conjunction** — *"Madagascar and the"*, *"Panama
and"* — because the pattern's connector list let a capture stop mid-phrase; three of them
had reached the map. Those are repaired to the first place. **Fifty-three name two places**
and are handled differently: they are left exactly as they are and simply never geocoded,
for the reason given in limitation 10.

Three faults in the original site strings were fixed at the same time:

- `"Miombo"` kept the book's quotation marks, because Richardson was *defining* the word
  rather than naming a place.
- *Terra firma*, *the cerrado*, *lowland rainforests* and two others are habitat
  **types** the extractor had treated as localities. Now a separate section, labelled as
  things no protected area can be drawn around.
- `Located in the southeastern Philippines, Mindanao` captured the wrong clause.

Ambiguous names (*Espiritu Santo*, *Luzon*, *Cordillera Central*) carry Richardson's own
opening sentence as context rather than a country name inferred by me. That restraint
earned its keep: this *Cordillera Central* is in Luzon, and a **different** range of the
same name appears elsewhere in the book.

---

## 7. The map

Points are real georeferenced GBIF occurrence records, not geocoded place names.

### The trap that governs the fetch

GBIF's free-text `scientificName=` search must not be used: many of these names are
synonyms and it silently returns records of the *accepted* species.

| Query for *Anampses viridis* | Records | Centroid |
|---|---|---|
| free-text `scientificName=` | 3,071 | inland New South Wales |
| strict `taxonKey=` | 3 | all at Réunion |

The book describes that species as known from a single specimen; the 3,071 belong to
*Anampses caeruleopunctatus*, its widespread senior synonym. A map built on free-text
matching would smear narrow endemics across the ranges of common species — the same
family of error as the name-matching trap in §5. Every name is strict-matched to a usage
key then queried by `taxonKey`, with `hasGeospatialIssue=false` and at most 30 points
per species.

### A rate-limit bug that corrupted the figures

The first run used eight concurrent threads and retried three times with no delay. GBIF
answered **399 of the 2,408 requests made at the time with HTTP 429**, and the script cached those failures as
though they were results — so re-running never retried them, and 16.6% of the register
was silently recorded as having no records.

Because the register is sorted by tier descending, the failures landed on the tail:
**tier 1 appeared to be 3.6% mappable when it is actually 80%.** That impossible-looking
number is what exposed the bug. The fetcher now backs off exponentially, uses four
threads, and **never caches a failure** — a cached failure is indistinguishable from a
genuine absence and makes the miss permanent.

Corrected: **2,261 of 3,066** species mappable from **21,906** points; **805** have no
georeferenced record anywhere in GBIF.

### Geocoding the locality names, with two independent checks

Refusing to look up *Salween River* while printing it was inconsistent, so the names are
geocoded — but one check is not enough.

*Type agreement* catches the obvious failures: asked for "The Cordillera Central",
Nominatim returns a **university** in Baguio. Names ending *River* must resolve as
waterways, *Island* as islands; buildings, roads and campuses are rejected outright.
That removed 354 of 929 candidates.

*But type agreement cannot see a same-type homonym*, and those are common. "Congo River"
resolved to a real river of that name in **Sierra Leone**, 4,000 km from the Congo,
passing cleanly as river/river; "Dunk Island" resolved near Sydney rather than
Queensland. So each geocode is measured against the GBIF records of the species sitting
at that locality — an independent witness already held:

| | |
|---|---|
| Agree within 500 km — plotted | **339** |
| Disagree by more — discarded | **110** |
| No records to check against — off by default | **126** |

About one in five checkable geocodes was wrong by more than 500 km, and none of those
errors was detectable from the name or the feature type. That rate is why the unverified
126 are not shown by default. The validated rings add **78** species that have no
georeferenced record of their own.

**Total placeable: 2,339 of 3,066 (76%). 727 cannot be placed at all.**

The map shows density, never authoritative dots, and states plainly that it maps
collecting effort at least as much as biology.

---

## 8. The website

Live at **https://speciesblacklist.org** — static, on GitHub Pages from the public repo
`BiodiversityGroup/speciesblacklist`.

Five real pages, each a genuine `index.html` returning 200 with its own title,
description and canonical: `/`, `/register/`, `/map/`, `/sites/`, `/methods/`. Real
directories rather than a `404.html` fallback, because GitHub Pages serves that with an
HTTP 404 status, which would keep every view but the homepage out of the index while
indexing is deliberately enabled. The app reads `location.pathname` and opens the
matching view, so Back moves between views instead of leaving the site.

`site/index.html` is the source. **Run `14_build_pages.py` after every edit to it**, or
the four sub-pages keep serving the previous version while the homepage looks correct.
Asset paths must stay root-absolute or they resolve into the subdirectory and 404 — the
build script asserts that rather than trusting it.

---

## 9. Known limitations

1. **Vertebrates only.** The corpus is a vertebrate reference. Invertebrates, plants
   and fungi are where the assessment gap is worst — invertebrates are 97% of animals
   and 32% of animal assessments — and this project says nothing about them.
2. **Single source.** Everything rests on one author's synthesis. Richardson is
   credible and peer-reviewed, but no second corpus corroborates the restriction
   statements.
3. **n=28 in the validated stratum.** The tier 3–5 result is significant but thin.
   The next Red List release adds labels and should be used to re-run script 04.
4. **Restriction is inferred from prose, not from range data.** No area of occupancy
   has been computed. Tier 3–5 is an argument that Criterion B *should be evaluated*,
   not a finding that it is met.
5. **Sites are inconsistent in grain.** Extracted localities run from a single named
   river to the entire Tropical Atlantic. Site-level clustering in the output needs a
   granularity filter before it can drive site-based prioritisation.
6. **Tier 2 of the audit will have residual homonyms.** GBIF confirmation removes most
   but the rank is coarse; every tier-2 demotion is written out for inspection.
7. **Tier 1 is a weak-evidence bucket, not a severity one.** It means the extractor found
   no restriction statement — not that the species is widespread. Three rounds of fixes
   (§4) have taken it from 279 species to **147**: two of pattern widening, then one that
   was not about patterns at all but about sentence segmentation, which alone accounted for
   79 species. Each round was found by auditing the tier, and each time the residue looked
   clean before the next mechanism was noticed — so the honest statement is that tier 1 has
   been wrong three times and may still hide a fourth mechanism. What remains is a genuine
   mix of wide-ranging species and sentences that discuss a species without describing its
   range. A tier-1 species is *unranked*, not *safe*, and must never be read as the latter.
8. **The map maps collecting effort.** Density clusters where institutions and
   expeditions have worked, so it is a picture of where the evidence sits rather than
   where risk is concentrated.
9. **1,334 species have no locality and 727 cannot be placed at all.** Both numbers are
   published rather than rounded away, because the least documented species are the ones
   the register exists to surface.
10. **67 localities name two places and are deliberately never mapped.** *"Athi and Tana
    River"*, *"Caroline and Marshall Islands"*. They are kept whole in the register and
    withheld from the gazetteer, because every reduction to one place either discards the
    noun that identified it (*"Caroline"*) or invents a location outright — *"Oman and
    Masirah Island"* reduces to *"Oman Island"*, and *"Turkana and the Omo River"* to
    *"Turkana River"*, neither of which exists. A true but coarse locality is preferable
    to a precise-sounding fiction, and the evidence sentence names both places anyway.
11. **"Validated" means within 500 km, which is coarse for a single-site endemic.** About half
    the plotted localities agree with a real record to within 50 km and 17% to within
    10 km, but **60 of 339 agree only to more than 200 km** — for a species whose whole
    claim is one river, that can be the wrong watershed. Worse, for **72 of the 339 the
    witness records are themselves spread over more than 1,000 km** (large marine
    features, mostly: the Gulf of Guinea, the Bay of Biscay), so a 500 km test could not
    have failed however wrong the coordinate was. Those points are corroborated only in
    the weak sense that nothing contradicted them. A further **74 carry no feature noun
    the type-check recognises** (*Espiritu Santo*, *Luzon*) and passed on distance alone.
12. **The tier 3/4 boundary is not cleanly separable by pattern — now fixed, but it was
    wrong.** Tier 4 used to be tested before tier 3, and its alternation contains *river*,
    so *"confined to the Kapuas River drainage"* — a basin the size of a country — scored as
    "a single named site". 73 species were misclassified against the published table. Tier 3
    is now tested first, with a tempered pattern so a basin named as context for a real
    point (*"a single locality within the Ganges River drainage"*, 29 species) still scores
    4. The change no longer moves anything in or out of the priority stratum, because the
    boundary is at 2|3 — which is part of why it was put there.
13. **Four single-site endemics sit in tier 2, and widening the pattern to reach them
    made things worse.** Tier 4's slot before the feature noun holds one word, so a
    multi-word place name — *"the Suoi Rut stream"*, *"La Quebradona creek"* — does not
    match. Widening it to three words was tried and the held-out set rejected it: it moved
    94 species from tier 2 into tier 4, of which 7 were in the labelled set and only 1 came
    out threatened, dropping the priority stratum from 53.6% to 45.7% (OR 4.23 → 3.00,
    p 0.0016 → 0.0091). The narrow slot is doing real work — a bare *"the X River"* is a
    tighter claim than a qualified phrase — so the four misses stay, recorded rather than
    fixed at that price.
14. **One taxon in the register may not be a real species.** *Pseudonovibos spiralis*, the
    khting-vor, is known only from twisted horns that Richardson himself notes "may perhaps
    be nothing more than artificially-crafted cattle horns". It is genuinely unassessed, so
    it satisfies the NE list's criterion literally, but IUCN's silence here reflects
    doubtful validity rather than neglect. Its evidence sentence is displayed in full, so a
    reader sees the caveat; it is nonetheless ranked alongside species that certainly
    exist. Two further entries (*Apus sladeniae*, *Varanus telenesetes*) are described as
    "mysterious" but are valid taxa that IUCN lists as DD.

### What is still open

**Tier 5's underperformance is unexplained.** At 40% it sits below tier 4 (70%) and tier 3
(67%), and the survey-effort mechanism proposed in §4 is plausible but untested — the corpus
wording supports only a 0/2 versus 6/13 split, which is nothing. Either a larger
reassessment cohort or an external habitat/depth join would settle it. Until then the tier
numbers should be read as evidence types, not as a risk ordering.

**Two species share a sentence the corpus never terminated.** *Micrurus camilae* and
*Emmochliophis fugleri* sit in one run-on sentence with no period between their accounts, so
one takes the other's tier-5 phrase. No sentence splitter can recover a boundary that is not
in the source; this needs a manual correction to the input text.

**A probable non-taxon is ranked** — see limitation 14.

**Two thirds of IUCN's Data Deficient vertebrates are outside the corpus entirely** (§1).
Every one the corpus names is now included, so further coverage has to come from a second
source, not from better extraction.

---

## 10. Reproducing

```bash
python scripts/01_build_iucn_index.py path/to/iucn-latest.zip
python scripts/02_refresh_and_diff.py
python scripts/03_extract_and_score.py
python scripts/04_validate_score.py
python scripts/05_triage_unmatched.py
python scripts/06_audit_false_negatives.py
python scripts/07_assemble.py
python scripts/08_verify_ne.py
python scripts/09_verify_dd.py
python scripts/10_build_site.py
python scripts/11_make_og.py          # needs Pillow
python scripts/12_build_map.py
python scripts/13_geocode_localities.py
python scripts/14_build_pages.py
python scripts/15_check_figures.py   # exits non-zero if the prose has drifted
```

Standard library only apart from `11_make_og.py`, which needs Pillow. That matters on
this machine because the default Python is ARM64 and cannot build most wheels.

Scripts 12 and 13 are the slow ones: 12 makes two GBIF calls per species, and 13 is
capped at one Nominatim request per second by their usage policy, so allow about 15
minutes for a cold run. Both cache, so reruns are free.

### Deliverables

| File | Contents |
|---|---|
| `SPECIES_BLACK_LIST_dd.csv` | List 1, ranked by restriction tier |
| `SPECIES_BLACK_LIST_ne.csv` | List 2, verified never assessed |
| `prehistoric_extinctions.csv` | Out of IUCN scope by policy |
| `validation_report.txt` | The evidence the ranking rests on |
| `dd_movement_2024_to_2026.csv` | The 108 reassessments, i.e. the labelled set |
| `unmatched_triage.csv`, `ne_audit_flagged.csv`, `ne_verify_removed.csv`, `dd_verify_removed.csv` | Full audit trail — every exclusion, with its reason |

Website payloads, in `site/`:

| File | Contents |
|---|---|
| `index.html` | The whole application, self-contained; source for the sub-pages |
| `data.json` | 2,407 species accounts, tiers, sites, validation figures |
| `map.json` | 17,068 occurrence points, species names, Natural Earth land |
| `geo.json` | Geocoded localities with their cross-check verdict |
| `favicon.svg`, `brand/mark.svg` | The original logomark |
| `register/`, `map/`, `sites/`, `methods/` | Generated by `14_build_pages.py` — do not hand-edit |

### Refreshing when the next Red List ships

Re-download the archive and rerun. Script 02's diff becomes a fresh labelled set, and
script 04 re-tests the ranking against it. The validation gets stronger with each
release, and if a future release contradicts the tier 3–5 result, that has to be
reported rather than explained away.
