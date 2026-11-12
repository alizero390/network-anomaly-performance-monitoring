# Design Specification: Strategies A, B and C under Delayed and Partial Labels

Status: **Proposed, 2026-11-12.** D3, D4, D7 and D8 are implemented as proposed
(`nadmon.scenarios`, `nadmon.labels`; Ali: "do the next step", explicit approval still
to be recorded). All other decisions are not yet approved. Each decision below (D1-D14) needs an
"approve", "change" or "reject" before the code that depends on it is written. Approved
decisions move into `RESEARCH_DECISIONS.md` under the change policy (section 15); until
then that file stays authoritative.

This spec answers the ten open questions in `RESEARCH_DECISIONS.md` section 12, using the
Paper 1 evidence (`results/robustness_summary.md`, `results/alarm_attribution/`).

## Approval checklist

| # | Decision | Answers open question | Changes an approved decision? | Your answer |
|---|---|---|---|---|
| D1 | Data roles: calibrate on February validation, evaluate on February test | - | No | |
| D2 | CIC-IDS-2017: new split with a Thursday validation part | - | Adds runs; Paper 1 runs unchanged | |
| D3 | Scenarios built by resampling real records from strata | Q10 | No | |
| D4 | Ground truth: harmful/harmless defined by expected calibrated F1 | Q10 | No | |
| D5 | Strategy B monitors calibrated F1; raw F1 kept as a comparison | - | **Yes: section 3 (primary metric F1)** | |
| D6 | Reference: pooled validation value, fixed | Q1 | No | |
| D7 | Label release and availability mechanics, plus one biased condition | Q8 | No (adds a condition) | |
| D8 | Minimum labelled sample and cohort pooling | Q2 | No | |
| D9 | Alarm rule for B unchanged: 0.05 drop, 2 consecutive eligible cohorts | - | No | |
| D10 | Strategy A: tests, sparse categories, calibrated proportion threshold | Q3, Q4 | No | |
| D11 | Strategy C: passive and active variants; association period | Q5 | Adds a variant | |
| D12 | Event counting and matching | Q6, Q7 | No | |
| D13 | Repetitions and statistics | Q9 | No | |
| D14 | Experiment grid | - | No | |

---

## D1. Data roles

**Proposal.**

- Primary model: February Random Forest (`feb_rf`), frozen. Secondary: `feb_hgb`.
- **Calibration** (every threshold in this spec): February validation partition (290,575
  records), the same data used in Paper 1.
- **Evaluation**: February test partition (435,843 records), used here for the first time.
- **Freeze before test.** All calibrated values are written to `configs/strategies.toml`
  and committed before any code reads the test partition. After that, test results
  cannot change a parameter (RESEARCH_DECISIONS.md section 9).
- January stays a supporting replication (no test partition exists).

**Why.** This is the existing approved separation; the spec only states when the test
partition is opened.

## D2. CIC-IDS-2017 in the thesis

**Problem.** The Paper 1 CIC split (train Monday-Thursday, monitor Friday) has no
validation part, so nothing can be calibrated on CIC and Strategy B has no out-of-sample
reference.

Thursday's attacks (`results/cicids2017_profile/`): Web attacks 12:00-13:00 (fewer than
200 flows) and Infiltration-Portscan 17:00-18:59 (71,767 flows, 68,793 of them after 18:00).

**Proposal.** New runs `cic2_rf` and `cic2_hgb` (Paper 1 runs untouched):

- Train: Monday-Wednesday plus the first 50% of Thursday's records in time order.
- Validate: the last 50% of Thursday (about 180,000 records, about 36 windows), which
  contains most of the Infiltration-Portscan block.
- Monitor: Friday, as before, with known natural events: Botnet (unseen, harmful),
  Portscan and DDoS, and attack-free stretches.

The 50% boundary may cut the 18:00 Infiltration-Portscan hour; a quick check after
approval confirms both parts have at least 100 attacks (the existing `MIN_ATTACKS` guard).

**Alternatives.** (a) Use CIC only as a case study with parameters transferred from
UNSW-NB15 and no CIC calibration; simpler, but B's reference would come from training
predictions, which are inflated. (b) Drop CIC from the thesis core and keep it in Paper 1
only.

## D3. Scenario construction (open question 10)

**Proposal.** Every scenario stream is built by **resampling real records** from defined
strata of one partition (validation for calibration, test for evaluation). No feature
values are edited, so no unrealistic records are created. The frozen model's prediction
for every record is computed once, so a stream is only a list of record indices.

- Stream: 40 windows of 5,000 records. Windows 1-20 follow the partition's normal
  composition; the change starts at window 21 (onset) and lasts to window 40.
- Abrupt change is primary; a 10-window ramp is a robustness check.
- Strata: benign records by `service`; attack records by attack category.
- Records are drawn with replacement within each stratum. Paper 1's exchangeability
  limitation applies; a block-sampling variant (runs of consecutive records) is an
  optional robustness check.

| Scenario | What changes from window 21 | Expected effect |
|---|---|---|
| S0 Stable | Nothing | No alarm of any kind should fire |
| H1 Fewer attacks | Attack share falls to 2%, category mix unchanged | Input changes; per-class performance does not (harmless) |
| H2 Benign service mix | The largest benign service is replaced by other services whose FPR is within 0.5 percentage points of its own; noisy services keep their share | Input changes; performance does not (harmless) |
| H3 Easy attack mix | The largest attack category is replaced by categories whose recall is within 0.03 of its own; hard categories keep their share | Input changes; performance does not (harmless) |
| X1 Hard attack mix | Attacks shift towards Fuzzers (and other categories with low recall) | Recall falls (harmful) |
| X2 False-positive burst | Benign traffic shifts towards services with high FPR | FPR rises (harmful) |
| X3 Unseen attack (CIC only) | Natural Friday Botnet period | Recall of the new attack is 0 (harmful) |

Shift sizes are set per scenario so the ground truth (D4) is unambiguous: harmful
shifts use the smallest share moved (10%, 20%, ... 100%) that reaches the harmful
threshold. Strata with fewer than 50 records are not used as targets.

*Implementation note (2026-11-12).* The first version of H2 and H3 moved traffic towards
strata whose rate was close to the **pooled** rate. On UNSW-NB15 no attack category is
close to the pooled recall (0.968 sits between Generic at 1.0 and Fuzzers at 0.58), so H3
could not be built; H2 barely changed the input. Both now replace the largest stratum.
On February validation (attack strata only), H1, H3 and X1 get clean ground truth; X1
needs half of all attacks to be Fuzzers (recall 0.77, calibrated F1 -0.11). Each stratum's
recall and FPR come from the partition the stream is drawn from.

Natural-order runs (February test in time order; CIC Friday) are reported as case
studies alongside the controlled scenarios, without constructed ground truth.

**Why.** A drawn scenario has a known onset and a known effect on per-class performance,
which natural traffic does not (RESEARCH_DECISIONS.md section 11: "Controlled experiments
must establish known event conditions"). Paper 1 already identified the real sources of
harmless change (attack share, attack mix) and harmful change (Fuzzers, false-positive
bursts, unseen attacks), so the scenarios mirror what was observed.

**Note.** Using test labels to compute stratum performance for evaluation scenarios is
ground-truth construction, not tuning; no monitor parameter is chosen from it (D1).

## D4. Ground truth for harmful and harmless

**Proposal.** For each scenario, compute the **expected calibrated F1** after onset from
the stratum mix and each stratum's recall and FPR:

- **Harmful**: expected calibrated F1 falls by at least 0.10 (twice the alarm threshold).
- **Harmless**: expected calibrated F1 changes by less than 0.02, and the input
  distribution measurably changes.
- Anything in between is not used as a scenario.
- "Measurably changes" = total variation distance between the stratum mixes of at
  least 0.10.

**Why.** Calibrated F1 combines recall and FPR but is not moved by the attack share
(Paper 1, claim 6). So H1 is harmless by definition, which raw F1 would contradict. Gaps
between the two thresholds keep the labels clean.

## D5. Strategy B's monitored metric (changes an approved decision)

**Approved now (section 3):** primary metric F1.

**Proposal.** Strategy B monitors **calibrated F1** at the validation attack share.
Raw F1 is kept as variant **B-F1**, so the thesis shows the Paper 1 effect inside the
strategy comparison. Recall and FPR are recorded for every cohort.

**Evidence.** Paper 1: at 1% attacks, raw F1 false-alarms in 100% of simulated UNSW-NB15
streams, calibrated F1 in 0-0.5%; calibrated F1 keeps the January false-positive bursts
that recall and balanced accuracy miss. Under D4, raw F1 would raise alarms on harmless
scenario H1 by construction.

**If approved:** record the change in RESEARCH_DECISIONS.md (original decision, reason,
evidence) and CHANGELOG.md, per section 15.

## D6. Reference value (open question 1)

**Proposal.** The B reference is the **pooled calibrated F1 over all validation windows**,
fixed before monitoring. It is never taken from the first monitored windows.

**Evidence.** Paper 1 claim 2: first-window references were 0 or undefined on CIC Friday
and a low-performance period on February validation (first alarm at window 57 vs 2).

## D7. Label release and availability (open question 8)

**Proposal.**

- A window's labels are released together at the end of window `w + d`, with delay
  `d` of 0, 5 or 10 windows.
- Availability `p` of 100%, 50% or 20%: each record is labelled independently with
  probability `p`, regardless of class or prediction, with a fixed seed.
- Labels stay attached to their original window (the cohort). B evaluates cohorts, not
  the window in which labels arrive.
- **One biased condition (alert-first)**: predicted attacks are labelled with probability
  0.9, predicted normal records with 0.1, as when analysts triage alerts first. Missed
  attacks are then rarely labelled, so recall is overestimated. This tests the most
  realistic bias without a full grid.

**Why.** The first three items are the approved grid with its mechanics made explicit.
The alert-first condition answers open question 8 with one realistic case instead of
leaving it as a limitation.

## D8. Minimum labelled sample and cohort pooling (open question 2)

**Proposal.**

- A cohort is eligible when it has at least `n_min` labelled attacks and at least 500
  labelled normal records.
- `n_min = ceil(z^2 * r(1 - r) / 0.05^2)`, with `r` the validation recall and z = 2.326
  (a 1% chance per cohort that sampling noise alone puts recall 0.05 below its true
  value). For `feb_rf` (r = 0.968): **n_min = 68**.
- **Cohort pooling**: an ineligible cohort is merged with the following cohorts, up to 5
  windows, until it is eligible. Still short after 5 windows: ineligible, which is never
  read as stable.
- The 500-normal minimum gives FPR a standard error of about 0.003 at FPR 0.5%.

**Evidence (February validation, `feb_rf`).** Windows contain 250-3,535 attacks (median
993). At 100% and 50% availability every window has at least 68 labelled attacks; at 20%
availability, 17% of windows fall short. In a 2%-attack window (H1), 20% availability
leaves about 20 labelled attacks, so pooling about 4 windows is needed. Paper 1 (cic_rf)
showed that skipping small windows silences a real Botnet failure lasting 11 windows;
pooling should recover it, at the cost of a later alarm (to be checked).

## D9. Strategy B alarm rule

**Proposal.** Unchanged: alarm when the metric is at least 0.05 below the reference in 2
consecutive eligible cohorts. The planned sensitivity analysis (0.03 and 0.10) stays.

## D10. Strategy A (open questions 3 and 4)

**Proposal.**

- **Reference sample**: 20,000 records drawn at random from the validation partition
  (fixed seed). For calibration on validation, the validation records are split at
  random into two halves: one for the reference sample, one for drawing streams.
- **Tests**: Kolmogorov-Smirnov for numeric features; chi-square for `proto`, `state`
  and `service`. Benjamini-Hochberg correction across the features of one window at 0.01.
- **Sparse categories (Q3)**: categories with an expected count below 5 in a window are
  merged into "other" before the chi-square test.
- **Warning rule (Q4)**: a window is flagged when at least a proportion `q` of features
  changed; a warning needs 2 consecutive flagged windows (mirroring B). `q` is the
  smallest value giving at most 5% false warnings on stable validation streams (S0).
- **Ablation**: a practical-significance floor (a feature counts only if its KS
  statistic is also at least 0.1), and single-feature warnings.

**Expected behaviour.** A should warn on H1-H3 (input changes) and X1-X2. That it cannot
tell harmful from harmless is the point of the comparison; Strategy C is meant to resolve it.

## D11. Strategy C (open question 5)

**Proposal.** Two variants:

- **C-passive** (the approved architecture): alarms are B's alarms; A's warnings are
  labelled afterwards as confirmed, unconfirmed or absent. This changes reporting, not
  detection.
- **C-active**: while an A warning is active, B confirms on **one** flagged eligible
  cohort instead of two. This can shorten detection delay, at the risk of more false
  alerts. Without a warning, B's normal two-cohort rule runs as the independent path.
- **Association period (Q5)**: `L = d + 5` windows after the warning, then calibrated on
  validation harmful scenarios as the smallest `L` that captures 95% of warning-to-
  confirmation gaps.

**Why.** C-passive alone would report exactly B's detections, with labels attached. An
active variant tests whether the input warning has value for detection itself.

## D12. Event counting and matching (open questions 6 and 7)

**Proposal.**

- Each controlled stream has exactly one event (onset at window 21) or none (S0), so
  overlapping events do not arise.
- After an alarm, the monitor stays in an alarm state; it re-arms after 2 consecutive
  eligible, unflagged cohorts. Alarms during the alarm state are not counted again.
- A **true alert** is raised between the onset and the end of the stream on a harmful
  scenario. Any alarm on S0 or a harmless scenario, or before the onset, is a **false alert**.
- **Detection delay**: alarm window minus onset window (in windows; wall-clock time in
  the natural-order case studies).
- **Warning lead time**: B's confirmation window minus A's warning window, for
  confirmed warnings.

## D13. Repetitions and statistics (open question 9)

**Proposal.**

- 200 streams per scenario and condition, fixed seeds. Every strategy runs on the
  **same** streams, so comparisons are paired.
- Rates (event recall, false-alert rate): Wilson 95% confidence intervals.
- Detection delay: median with a bootstrap 95% interval.
- Paired comparisons: McNemar's test for detected/missed; Wilcoxon signed-rank for delays.

## D14. Experiment grid

| Factor | Levels |
|---|---|
| Scenarios | S0, H1, H2, H3, X1, X2 (UNSW-NB15); natural Friday incl. X3 (CIC) |
| Label conditions | 9 (delay x availability) + 1 alert-first |
| Strategies | A; B-F1; B (calibrated F1); C-passive; C-active |
| Models | feb_rf (primary), feb_hgb; cic2_rf, cic2_hgb |
| Repetitions | 200 streams per scenario and condition |

A uses no labels, so it is computed once per stream and reused across label conditions.
Predictions are computed once per partition; streams only index into them. The cost is
dominated by A's per-window tests (about 6 scenarios x 200 streams x 40 windows).

---

## After approval: implementation order

1. `nadmon.labels`: release and availability simulation, cohorts, pooling (D7, D8), with tests.
2. `nadmon.scenarios`: strata, stream builder, expected calibrated F1 (D3, D4), with tests.
3. `nadmon.strategies`: A, B, C-passive, C-active (D5, D9-D11), with tests.
4. `nadmon.evaluation`: event counting and statistics (D12, D13).
5. Calibration on validation, then `configs/strategies.toml` committed (D1 freeze).
6. Evaluation on test and CIC Friday.

Steps 1-2 need only D3, D4, D7 and D8 approved, so they can start first.
