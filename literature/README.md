# Literature

This folder supports the literature review and every paper written from this project.

## Files

- `references.bib`: one BibTeX library for the thesis and all papers. Export it from Zotero (Better BibTeX keeps citation keys stable) or edit it by hand.
- `notes/`: one Markdown file per paper read, named after its citation key, for example `notes/lipton2018bbse.md`.
- `search_log.md`: every database search (date, database, exact query, number of results, number kept). A systematic review must report this, so keep it from the start.

## Note template

```markdown
# <citation key>

- **Problem:**
- **Data and setting:** (datasets, label assumptions, drift type)
- **Method:**
- **Evaluation:** (metrics, how degradation or drift is defined)
- **Relevance to this thesis:** (Strategy A / B / C, label delay, prevalence)
- **Limitations / gaps:**
```

## Review themes

1. Concept drift detection for network intrusion detection.
2. Monitoring deployed models with delayed or partial labels.
3. Label-free performance estimation (confidence-based estimation, label-shift estimation).
4. Prevalence sensitivity of F1 and alternative metrics (MCC, balanced accuracy).
5. Known problems in intrusion detection datasets, including UNSW-NB15.

Check every entry in `references.bib` against the publisher's page (authors, venue, year, DOI) before citing it.
