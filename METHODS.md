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
to. All 2,355 DD species were located in the text.

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

## 6. Known limitations

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

---

## 7. Reproducing

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
```

Standard library only — no third-party dependencies, which matters on this machine
because the default Python is ARM64 and cannot build most wheels.

### Deliverables

| File | Contents |
|---|---|
| `SPECIES_BLACK_LIST_dd.csv` | List 1, ranked by restriction tier |
| `SPECIES_BLACK_LIST_ne.csv` | List 2, verified never assessed |
| `prehistoric_extinctions.csv` | Out of IUCN scope by policy |
| `validation_report.txt` | The evidence the ranking rests on |
| `dd_movement_2024_to_2026.csv` | The 108 reassessments, i.e. the labelled set |
| `unmatched_triage.csv`, `ne_audit_flagged.csv`, `ne_verify_removed.csv`, `dd_verify_removed.csv` | Full audit trail — every exclusion, with its reason |

### Refreshing when the next Red List ships

Re-download the archive and rerun. Script 02's diff becomes a fresh labelled set, and
script 04 re-tests the ranking against it. The validation gets stronger with each
release, and if a future release contradicts the tier 4–5 result, that has to be
reported rather than explained away.
