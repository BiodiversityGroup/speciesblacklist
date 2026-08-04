# The Species Black List

Live at **https://speciesblacklist.org**

A register of vertebrate species that the IUCN Red List records as **Data Deficient**
or has **never assessed**, ranked by how narrowly restricted the published record says
they are.

Data Deficient and Not Evaluated species are excluded from conservation in practice
and, in one case, by treaty language: Target 4 of the Kunming-Montreal Global
Biodiversity Framework commits governments to halting the extinction of *known
threatened species*, a phrase that excludes both categories by definition. Under 3.5%
of Mohamed bin Zayed Species Conservation Fund awards have gone to Data Deficient
taxa. This register is an attempt to say which of those species most deserve a look.

| | |
|---|---|
| Data Deficient | **3,031** species |
| of those, priority stratum | **1,123** (tier 3–5) |
| coverage of IUCN's DD vertebrates | **35%** (3,031 of 8,659) |
| Never assessed by IUCN | **35** |
| Red List version | v2026-1 (accessed 2026-07-28) |

## The ranking is tested, not asserted

Between the previous data and v2026-1, IUCN independently reassessed **140** of these
species. Those outcomes are a held-out answer key the ranking rules never saw.

| | n | proved threatened or extinct |
|---|---|---|
| Priority (restriction tier 3–5) | 28 | **53.6%** (95% CI 36–70%) |
| Rest (tier 1–2) | 112 | 21.4% (95% CI 15–30%) |
| All 140, undifferentiated | 140 | 27.9% |

Fisher exact two-sided **p = 0.0016**, odds ratio **4.23**.

Read that honestly: taken as one flat group, these species proved threatened at about
the ordinary all-species rate. **Data Deficient status by itself predicts very
little.** The ranking is what carries the signal, and the priority rate lands near the
56% that Borgelt et al. (2022, *Communications Biology*) predicted for Data Deficient
species generally — suggesting that figure belongs to the narrowly restricted subset.

## What this is not

Not Red List assessments, and they must not be cited as such. The ranking comes from a
text-classification rule applied to published range statements; **no taxonomist or
conservation biologist has reviewed the individual species.** What has been tested is
the rule's average behaviour, which is a claim about the group, not about any one row.

Treat it as a prioritised research agenda: an argument about where to look.

## Contents

```
index.html      the site (self-contained; no build step, no dependencies)
data.json       2,408 species accounts
og-image.png    the shared-link preview card, drawn from data.json
METHODS.md      full method, validation, and limitations
pipeline/       the scripts that build it, in run order
```

`pipeline/` is included so the result can be checked rather than taken on trust. It
needs only the Python standard library, except `11_make_og.py`, which draws the
preview card and needs Pillow. The IUCN source archive and intermediate build files
are not committed — see `METHODS.md` for how to fetch them and re-run.

## Sources

- Richardson, M. (2023) *Threatened and Recently Extinct Vertebrates of the World: A
  Biogeographic Approach.* Cambridge University Press.
- IUCN (2026). *The IUCN Red List of Threatened Species.* Version 2026-1.
  https://www.iucnredlist.org — doi:10.15468/0qnb58, accessed via GBIF.org.
  IUCN Red List Terms of Use apply.
- GBIF Backbone Taxonomy, for synonym resolution and independent verification.

Built by [The Biodiversity Group](https://biodiversitygroup.org).
