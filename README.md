# LawCodex — Andorra (ad)

Legislation of the Principality of Andorra as Markdown, in Catalan (the official language),
generated from the **Butlletí Oficial del Principat d'Andorra (BOPA)** — https://www.bopa.ad.

Retrieved: **2026-10-13**.

## Coverage

**1,189 Markdown files** — every document the BOPA classifies under its *Legislació* section
(themes *Constitució del Principat d'Andorra*, *Lleis* and *Legislació delegada*), from the first
BOPA of 1989 to October 2026:

| Directory | Content | Files |
|---|---|---|
| `constitucio/` | Constitució del Principat d'Andorra (1993) | 1 |
| `lleis/<year>/` | Laws of the Consell General (*lleis*, *lleis qualificades*, codes, budget laws...) | 1,062 |
| `legislacio-delegada/<year>/` | Legislative decrees (*decrets legislatius*: texts refosos / consolidated recasts approved by the Govern by delegation of the Consell General) | 126 |

By front-matter `type`: `act` 899, `qualified_act` 124, `legislative_decree` 126, `code` 5,
`constitution` 1, `other` 34 (older acts whose title does not start with "Llei", e.g. the 1989–1993
pre-constitutional laws and *Codi de l'Administració*).

**Important — these are the texts as published in the BOPA, not consolidated versions.**
Amending laws appear as separate documents and repealed laws are not removed, so
`status` is `unknown` (`in_force` only for the Constitution, which has never been amended) and
`consolidated: false`. Andorra itself regularly publishes *texts refosos* (consolidated recasts)
as legislative decrees, which are included in `legislacio-delegada/` and are the closest thing to
official consolidated law available here.

### Not covered

- **Consolidated versions** from the *Portal jurídic del Principat d'Andorra*
  (https://portaljuridicandorra.ad), the official site (Govern + Consell General, operated by the
  BOPA service) that publishes consolidated texts of laws and Govern regulations. Its legal notice
  (*Avís legal*, https://portaljuridicandorra.ad/AdvertenciaLegal) states "Tots els drets estan
  reservats", authorises only **personal use** of downloadable files and forbids modification of
  the site's contents; its robots.txt also sets `Crawl-Delay: 10`. In accordance with LawCodex rules
  it was **not** crawled. Mirroring it would require the permission of the Servei del BOPA / Govern
  d'Andorra.
- **Govern regulations** (*reglaments*, *decrets*), parish (*comuns*) ordinances, international
  treaties published in the BOPA, and all other BOPA sections — only the *Legislació* section is
  mirrored.
- Images embedded in a few documents (not copied; text only).

## Structure

```
constitucio/constitucio.md
lleis/<year>/<publication-date>-llei-<n>-<year>.md          e.g. lleis/2026/2026-06-03-llei-9-2026.md
lleis/<year>/<publication-date>-<title-slug>.md             older acts without a number
legislacio-delegada/<year>/<publication-date>-decret-legislatiu-....md
```

`<year>` is the year of publication in the BOPA. Front matter:

```yaml
title: "Llei 9/2026, del 7 de maig, del Registre Civil."
identifier: "Llei 9/2026"
type: act                 # constitution | act | qualified_act | legislative_decree | code | other
jurisdiction: ad
language: ca
date: 2026-05-07          # date of the act (from its title, else BOPA article date)
published: 2026-06-03     # BOPA publication date
bopa: "BOPA núm. 56, any 2026"
status: unknown
consolidated: false
source: "https://www.bopa.ad/Documents/Detall?doc=CGL_2026_06_01_15_25_49"
document_url: "https://bopadocuments.blob.core.windows.net/bopa-documents/..."   # official HTML file
retrieved: 2026-10-13
```

Headings: *Títol / Capítol / Secció* map to `##`… and articles to the next level. Documents from
1989 to the early 2010s are stored by the BOPA as line-wrapped plain HTML; their paragraphs were
re-joined heuristically (line breaks inside sentences removed) without changing the wording.
Large recent documents that the BOPA splits into several HTML files (`1_X.html`, `2_X.html`...)
were taken from the unsplit file `X.html`.

## Sources

- BOPA web site, *Legislació* section: https://www.bopa.ad — the document list is obtained from the
  site's public API (`bopaazurefunctions.azurewebsites.net/api/GetFiltersLaws`,
  `GetPaginatedDocuments2Indexes`, the same calls the web page makes; the public function keys
  are read from the site's JavaScript at run time).
- Official HTML of each document: `https://bopadocuments.blob.core.windows.net/bopa-documents/<bulletin>/html/<doc>.html`.

## Licence / copyright

The texts are official legislative acts of the Principality of Andorra published in the official
gazette. The BOPA legal notice (https://www.bopa.ad/AvisLegal) reserves the BOPA's intellectual
property rights over the *structure, selection, arrangement and presentation* of its site; this
repository reproduces only the text of the legal acts (re-formatted), not the site's presentation.
Official texts are reproduced for information; for legally binding versions consult the BOPA.

## Regenerate

```sh
pip install -r scripts/requirements.txt
python scripts/ad_fetch.py      # list + download into ../_raw/ad/ (cached)
python scripts/ad_convert.py    # write Markdown into this repository
```
