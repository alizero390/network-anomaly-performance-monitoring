"""Label-bias study on a natural stream (D20): ground truth, alarm verdicts, scoring."""

import numpy as np
import pandas as pd

from nadmon import experiment as ex
from nadmon import label_bias as lbs
from nadmon import natural_bias as nb

W = 1000
S = ex.Settings(window_size=W, m_min=100, max_span=5)


def _stream(recalls, share=0.3, seed=0):
    rng = np.random.default_rng(seed)
    y, p = [], []
    for r in recalls:
        yy = (rng.random(W) < share).astype(int)
        pp = np.where(yy == 1, rng.random(W) < r, 0).astype(int)  # no false positives
        y.append(yy)
        p.append(pp)
    return np.concatenate(y), np.concatenate(p)


def _cal():
    yv, pv = _stream([0.9] * 20, seed=1)
    base = ex.Calibration(pi0=0.3, recall=0.9, n_min=1, reference_f1_calibrated=1, reference_f1=1)
    return lbs.model_reference(base, yv, pv)


def test_window_truth_finds_the_event():
    cal = _cal()
    y, p = _stream([0.9] * 10 + [0.1] * 10 + [0.9] * 10)
    truth = nb.window_truth(y, p, W, cal)
    assert truth.events == [(10, 19)]
    assert truth.defined.all()


def test_undefined_windows_do_not_break_an_event():
    cal = _cal()
    y, p = _stream([0.9] * 5 + [0.1] * 3 + [0.1] * 2 + [0.1] * 3 + [0.9] * 5)
    y[8 * W : 10 * W] = 0  # two windows without attacks
    p[8 * W : 10 * W] = 0
    truth = nb.window_truth(y, p, W, cal)
    assert not truth.defined[8] and not truth.defined[9]
    assert truth.events == [(5, 12)]


def test_weighting_detects_without_false_alarms_and_random_labels_agree():
    cal = _cal()
    y, p = _stream([0.9] * 10 + [0.1] * 10 + [0.9] * 10)
    truth = nb.window_truth(y, p, W, cal)
    conds = {c.name: c for c in lbs.policy_conditions()}
    rows = []
    for name in ("random_p100_d5", "pa90_pn10_d5"):
        for d in range(5):
            rows += [
                {**r, "draw": d} for r in nb.run_condition(y, p, conds[name], cal, S, truth, d)
            ]
    t = nb.policy_table(pd.DataFrame(rows)).set_index(["condition", "strategy"])
    assert t.loc[("random_p100_d5", "B"), "detection_rate"] == 1.0
    assert t.loc[("random_p100_d5", "B"), "any_false_alarm"] == 0.0
    assert t.loc[("pa90_pn10_d5", "B_ipw"), "detection_rate"] == 1.0
    assert t.loc[("pa90_pn10_d5", "B_ipw"), "any_false_alarm"] == 0.0


def test_judge_alarms():
    cal = _cal()
    y, p = _stream([0.9] * 3 + [0.1] * 3)
    from nadmon import labels as lb

    full = lb.cohort_counts(y, p, np.ones(len(y), dtype=bool), W)
    alarms = pd.DataFrame({"first": [0, 3], "last": [1, 4], "available_at": [6, 9]})
    assert nb.judge_alarms(alarms, full, cal).tolist() == ["false", "true"]
