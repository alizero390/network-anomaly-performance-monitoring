# Database queries to run (Scopus, IEEE Xplore, eLibrary)

These databases need an institutional login (HSE library), so they are run by hand.
Copy each query exactly, apply the filters, export the results, and put the exported
files in `literature/exports/` (or send them in the chat). Screening and the write-up
happen afterwards in `structured_search.md` and `search_log.md`.

Filters for every query: years **2015-2026**; document types article, conference paper,
review. Record the number of results each query returned.

## Scopus (Advanced search)

Export: select all results, **Export → CSV**, tick *Citation information* and
*Abstract & keywords*. One file per query: `scopus_q1.csv` ... `scopus_q4.csv`.

```text
Q1  TITLE-ABS-KEY ( "intrusion detection" AND ( monitor* OR "concept drift" OR "performance degradation" ) AND ( "delayed label*" OR "label delay" OR "label latency" OR "verification latency" OR "partial label*" ) )

Q2  TITLE-ABS-KEY ( "intrusion detection" AND ( "class imbalance" OR prevalence OR "base rate" ) AND ( "F1" OR "Matthews correlation" OR "MCC" OR "balanced accuracy" ) AND ( window* OR temporal OR drift OR monitor* ) )

Q3  TITLE-ABS-KEY ( ( "model monitoring" OR "performance monitoring" OR "drift detection" ) AND ( "false alarm*" OR "false positive*" ) AND ( "label shift" OR "prior probability shift" OR prevalence OR "class imbalance" ) )

Q4  TITLE-ABS-KEY ( ( "UNSW-NB15" OR "CIC-IDS2017" OR "CICIDS2017" ) AND ( temporal OR chronological OR drift OR "per-class" OR "per-category" OR "unseen attack*" ) )
```

## IEEE Xplore (Advanced search → Command search, "All Metadata")

Export: **Export → Search Results → CSV**. One file per query: `ieee_q1.csv` ... `ieee_q4.csv`.

```text
Q1  ("intrusion detection") AND (monitoring OR "concept drift" OR "performance degradation") AND ("delayed labels" OR "label delay" OR "label latency" OR "verification latency")

Q2  ("intrusion detection") AND ("class imbalance" OR prevalence OR "base rate") AND (F1 OR "Matthews correlation" OR "balanced accuracy") AND (temporal OR drift OR monitoring)

Q3  ("model monitoring" OR "drift detection") AND ("false alarms" OR "false positives") AND ("label shift" OR "prior probability shift" OR prevalence)

Q4  ("UNSW-NB15" OR "CICIDS2017" OR "CIC-IDS2017") AND (temporal OR chronological OR drift OR "unseen attacks")
```

## eLibrary (Расширенный поиск)

Search in: *название, аннотация, ключевые слова*; years 2018-2026; tick *с учетом
морфологии*. eLibrary has no bulk export for most accounts: open the results page,
press **Ctrl+P → Save as PDF**, one PDF per query (`elibrary_q1.pdf` ...), first 50
results is enough.

```text
Q1  обнаружение вторжений дрейф
Q2  мониторинг моделей машинного обучения сдвиг данных
Q3  обнаружение сетевых атак метрики оценки несбалансированные классы
Q4  UNSW-NB15 CICIDS2017
```

## Papers to download

| Paper | How | File name |
|---|---|---|
| Zoghi Z., Serpen G. Building an intrusion detection system on UNSW-NB15: Reducing the margin of error to deal with data overlap and imbalance. *Concurrency and Computation: Practice and Experience*, 2024. DOI 10.1002/cpe.8242 | Done 2026-11-10 (PDF supplied; read) | - |

Already read without login (no download needed): Botacin and Gomes, label delays in
malware detection, *Computers & Security* 2024 (author's copy).
