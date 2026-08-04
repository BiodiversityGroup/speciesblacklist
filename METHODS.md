# The Species Black List — Methods

**The Biodiversity Group** · pipeline rebuilt August 2026 against IUCN Red List v2026-1

---

## 1. What this project claims

Two claims, deliberately kept separate because they are not equally strong.

**List 1 — Data Deficient: 2,372 species**, of which **795 are tranche A**, the
validated priority stratum. IUCN has assessed these and returned *we don't know*. A
Cambridge University Press reference documents most of them as narrowly restricted,
often to a single river or a single collecting event. Ranked by how severe that
restriction is.

**List 2 — Not Evaluated: 36 species.** IUCN has never assessed these at all, yet the
same reference treats them as threatened or recently extinct. Small because the claim
is hard to make safely — see §5.

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

| Script | Does |
|---|---|
| `01_build_iucn_index.py` | Parses the DwC-A into a flat name → category index. Carries family and order, without which the audit in 06 cannot run. |
| `02_refresh_and_diff.py` | Cross-references the 9,162 book names against v2026-1 and diffs against the September 2024 baseline. |
| `03_extract_and_score.py` | Re-extracts evidence using the book's biogeographic structure and scores geographic restriction. |
| `04_validate_score.py` | Tests the score against species IUCN reassessed independently. **Run this before trusting anything downstream.** |
| `05_triage_unmatched.py` | Resolves names absent from IUCN against the GBIF backbone. |
| `06_audit_false_negatives.py` | Catches species IUCN files under a different genus or family. |
| `07_assemble.py` | Builds both lists. |
| `08_verify_ne.py` | Independent confirmation of the NE list; splits off pre-1500 extinctions. |
| `09_verify_dd.py` | Same verification applied to the DD list. |
| `10_build_site.py` | Builds `site/data.json`: register payload, recovered common names, cleaned localities, site metadata. |
| `11_make_og.py` | Draws the shared-link preview card. **Needs Pillow** — the only script with a third-party dependency. |
| `12_build_map.py` | Fetches georeferenced GBIF occurrence points per species plus the Natural Earth basemap → `site/map.json`. |
| `13_geocode_localities.py` | Geocodes the locality names and cross-checks each against real records → `site/geo.json`. |
| `14_build_pages.py` | Writes the four sub-pages from `site/index.html` and regenerates the sitemap. **Run after any edit to index.html.** |
| `_locality.py` | Shared: recovers a locality from a species' own evidence sentence. |
| `_common.py` | Shared: class normalisation. |

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
to. All 2,372 DD species were located in the text.

Restriction is the primary axis because IUCN **Criterion B** lets a species qualify
as threatened on a small range plus decline or fragmentation: area of occupancy under
2,000 km² for Vulnerable, 500 for Endangered, 10 for Critically Endangered. A species
*known only from its type locality* sits prima facie inside the CR envelope for B2.
That is the strongest defensible claim this corpus can make.

Tiers, strongest first:

| Tier | Basis |
|---|---|
| 5 | Type locality, original collection, or a single specimen |
| 4 | A single named site — one river, cave, spring, island, massif |
| 3 | A single drainage, archipelago, or mountain range |
| 2 | Restricted, extent unclear |
| 1 | No restriction statement |

### The validation

Between the 2024 export and v2026-1, IUCN independently reassessed **108** of the
book's DD species. Those 108 are a held-out labelled set the scoring rules never saw.

| | n | threatened or extinct | 95% CI |
|---|---|---|---|
| **Tier 4–5** | 19 | **52.6%** | 32–73% |
| Tier 1–3 | 89 | 20.2% | 13–30% |
| *All 108* | *108* | *25.9%* | *19–35%* |

**Fisher exact two-sided p = 0.0075, odds ratio 4.38.**

Two things follow. First, restriction severity genuinely predicts IUCN's own verdict.
Second, the tier 4–5 rate lands on the 56% that Borgelt et al. (2022, *Communications
Biology*) predicted for DD species generally — which suggests that figure belongs to
the narrowly restricted subset, and that a flat DD list dilutes a real signal with
vague-range species.

Read the base rate honestly: taken flat, the 108 came out threatened at 25.9%, which
is the ordinary all-species rate of roughly 28%. **The unranked premise does not
hold.** The ranking is what makes the list defensible, not the DD status by itself.

Caveats worth stating whenever the result is quoted: n=19 in the top stratum is
small, and the reassessed cohort is not a random sample of DD species — IUCN
reassesses where data has appeared, which likely favours species that turned out to
be more widespread. That bias runs against the tier 4–5 finding rather than
manufacturing it.

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
 36  after removing pre-1500 extinctions                   (08)   -7
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

Practical consequence: List 1 can be quoted with confidence. List 2 is 36 species,
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

**From a locality account (450 species).** Richardson organises geographically, so most
species sit inside a paragraph introduced by a place. That place, and its opening
sentence, attach to every species in the paragraph. The stronger provenance.

**From the species entry itself (999 species).** Where a species is not inside a
locality account, the place is usually named in its own sentence anyway — *"collected
from the upper Pungwe River"*, *"collected off Mauritius"*. `_locality.py` extracts
those. Named physical features are preferred over a bare capitalised word after a
preposition, and a capture is rejected when it collides with the species' own common
name or genus.

Coverage went from **19% to 60%** of the register (1,449 of 2,408) and the site list from
42 to 102. Clusters that were entirely invisible appeared — the Gulf of California holds
19 species, none of which had a locality before. **959 still have none**, because their
sentence names no place specific enough to record. Nothing is invented to fill that gap.

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
answered **399 of 2,408 requests with HTTP 429**, and the script cached those failures as
though they were results — so re-running never retried them, and 16.6% of the register
was silently recorded as having no records.

Because the register is sorted by tier descending, the failures landed on the tail:
**tier 1 appeared to be 3.6% mappable when it is actually 80%.** That impossible-looking
number is what exposed the bug. The fetcher now backs off exponentially, uses four
threads, and **never caches a failure** — a cached failure is indistinguishable from a
genuine absence and makes the miss permanent.

Corrected: **1,779 of 2,408** species mappable from **17,098** points; **629** have no
georeferenced record anywhere in GBIF.

### Geocoding the locality names, with two independent checks

Refusing to look up *Salween River* while printing it was inconsistent, so the names are
geocoded — but one check is not enough.

*Type agreement* catches the obvious failures: asked for "The Cordillera Central",
Nominatim returns a **university** in Baguio. Names ending *River* must resolve as
waterways, *Island* as islands; buildings, roads and campuses are rejected outright.
That removed 295 of 889 candidates.

*But type agreement cannot see a same-type homonym*, and those are common. "Congo River"
resolved to a real river of that name in **Sierra Leone**, 4,000 km from the Congo,
passing cleanly as river/river; "Dunk Island" resolved near Sydney rather than
Queensland. So each geocode is measured against the GBIF records of the species sitting
at that locality — an independent witness already held:

| | |
|---|---|
| Agree within 500 km — plotted | **315** |
| Disagree by more — discarded | **89** |
| No records to check against — off by default | **119** |

About one in five checkable geocodes was wrong by more than 500 km, and none of those
errors was detectable from the name or the feature type. That rate is why the unverified
119 are not shown by default. The validated rings add **66** species that have no
georeferenced record of their own.

**Total placeable: 1,845 of 2,408 (77%). 563 cannot be placed at all.**

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
3. **n=19 in the validated stratum.** The tier 4–5 result is significant but thin.
   The next Red List release adds labels and should be used to re-run script 04.
4. **Restriction is inferred from prose, not from range data.** No area of occupancy
   has been computed. Tier 4–5 is an argument that Criterion B *should be evaluated*,
   not a finding that it is met.
5. **Sites are inconsistent in grain.** Extracted localities run from a single named
   river to the entire Tropical Atlantic. Site-level clustering in the output needs a
   granularity filter before it can drive site-based prioritisation.
6. **Tier 2 of the audit will have residual homonyms.** GBIF confirmation removes most
   but the rank is coarse; every tier-2 demotion is written out for inspection.
7. **Tier 1 is a weak-evidence bucket, not a severity one.** It means the extractor found
   no restriction statement, and inspection shows it holds a mix of genuinely widespread
   species, restrictions phrased in ways the patterns miss (*"only definitely known
   from"*, *"known for certain only from"* — at least 40 of 279), and sentences that are
   about the species but say nothing about range. It has the **lowest** validated
   threatened rate of any tier, 3/20 = 15%. Widening the patterns would move real
   restrictions out of tier 1 and is the clearest remaining improvement.
8. **The map maps collecting effort.** Density clusters where institutions and
   expeditions have worked, so it is a picture of where the evidence sits rather than
   where risk is concentrated.
9. **959 species have no locality and 563 cannot be placed at all.** Both numbers are
   published rather than rounded away, because the least documented species are the ones
   the register exists to surface.

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
| `data.json` | 2,408 species accounts, tiers, sites, validation figures |
| `map.json` | 17,098 occurrence points, species names, Natural Earth land |
| `geo.json` | Geocoded localities with their cross-check verdict |
| `favicon.svg`, `brand/mark.svg` | The original logomark |
| `register/`, `map/`, `sites/`, `methods/` | Generated by `14_build_pages.py` — do not hand-edit |

### Refreshing when the next Red List ships

Re-download the archive and rerun. Script 02's diff becomes a fresh labelled set, and
script 04 re-tests the ranking against it. The validation gets stronger with each
release, and if a future release contradicts the tier 4–5 result, that has to be
reported rather than explained away.
