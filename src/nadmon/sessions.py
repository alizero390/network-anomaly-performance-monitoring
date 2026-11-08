"""Capture sessions of UNSW-NB15 and their chronological splits.

The dataset holds two separate capture periods (January 22-23 and February 18,
2015), each split on its own and in time order. A split boundary is always placed
at the end of a timestamp group, so records sharing a timestamp stay together.

- February ("50_20_30"): training (first 50%), validation (next 20%), test (last
  30%), frozen at audited counts.
- January ("attack_period_50_50"): all January attacks fall in a two-hour burst at
  the start of the session, so the 50/20/30 rule leaves validation without attacks.
  January is a replication-only session (no held-out test): its attack period, from
  the session start to the end of the last attack's timestamp group, is split 50/50
  into training and validation. Later, attack-free traffic is not used. See
  RESEARCH_DECISIONS.md, section 13.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from nadmon import dataset

TRAIN_FRACTION = 0.5
VALIDATION_FRACTION = 0.2
DATASET_TOTAL = 2_540_047  # all four raw files (audited; see PROJECT_CONTEXT.md)


@dataclass(frozen=True)
class Session:
    name: str
    start: int  # UTC epoch seconds, inclusive
    end: int  # UTC epoch seconds, exclusive
    total: int | None = None  # audited record count, when frozen
    train_end: int | None = None
    validation_end: int | None = None
    rule: str = "50_20_30"


FEBRUARY = Session(
    name="feb",
    start=dataset.FEB_START,
    end=dataset.FEB_END,
    total=dataset.FEB_TOTAL,
    train_end=dataset.TRAIN_END,
    validation_end=dataset.VALIDATION_END,
)
# January 22-23, 2015 (UTC).
JANUARY = Session(name="jan", start=1421884800, end=1422057600, rule="attack_period_50_50")

SESSIONS = {s.name: s for s in (FEBRUARY, JANUARY)}


def read_timestamps_and_labels(files: Sequence[Path]) -> tuple[np.ndarray, np.ndarray]:
    """All Stime and Label values, in file order."""
    stimes, labels = [], []
    for file in files:
        print("Reading timestamps:", file.name)
        for chunk in pd.read_csv(
            file,
            header=None,
            usecols=[dataset.STIME_INDEX, dataset.LABEL_INDEX],
            dtype={dataset.STIME_INDEX: "int64"},
            chunksize=200_000,
        ):
            stimes.append(chunk[dataset.STIME_INDEX].to_numpy(dtype=np.int64))
            labels.append(chunk[dataset.LABEL_INDEX].to_numpy(dtype=np.int8))
    return np.concatenate(stimes), np.concatenate(labels)


def check_sessions_cover_dataset(all_timestamps: np.ndarray) -> dict[str, int]:
    """Every record must belong to exactly one session."""
    counts = {
        name: int(((all_timestamps >= s.start) & (all_timestamps < s.end)).sum())
        for name, s in SESSIONS.items()
    }
    outside = len(all_timestamps) - sum(counts.values())
    if outside:
        raise RuntimeError(f"{outside} records fall outside both capture sessions.")
    return counts


def _group_end(ordered: np.ndarray, position: int) -> int:
    """Smallest count >= position that does not split a timestamp group."""
    if position >= len(ordered):
        return len(ordered)
    value = ordered[position - 1]
    return int(np.searchsorted(ordered, value, side="right"))


@dataclass(frozen=True)
class Split:
    total: int
    train_end: int
    validation_end: int
    cutoff: int  # last timestamp included in training + validation


def split_session(
    timestamps: np.ndarray, session: Session, labels: np.ndarray | None = None
) -> Split:
    """Chronological split of one session (timestamps and labels in file order)."""
    order = np.argsort(timestamps, kind="stable")
    ordered = timestamps[order]
    total = len(ordered)

    if session.rule == "attack_period_50_50":
        if labels is None:
            raise ValueError(f"{session.name}: the attack-period rule needs labels.")
        attack_positions = np.flatnonzero(labels[order] == 1)
        if len(attack_positions) == 0:
            raise RuntimeError(f"{session.name}: no attacks in the session.")
        validation_end = _group_end(ordered, int(attack_positions[-1]) + 1)
        train_end = _group_end(ordered, round(validation_end * 0.5))
    elif session.total is not None:
        if total != session.total:
            raise RuntimeError(f"{session.name}: record count does not match the audited total.")
        train_end, validation_end = session.train_end, session.validation_end
        for boundary in (train_end, validation_end):
            if _group_end(ordered, boundary) != boundary:
                raise RuntimeError(f"{session.name}: a frozen boundary splits a timestamp group.")
    else:
        train_end = _group_end(ordered, round(total * TRAIN_FRACTION))
        validation_end = _group_end(ordered, round(total * (TRAIN_FRACTION + VALIDATION_FRACTION)))

    if not 0 < train_end < validation_end < total:
        raise RuntimeError(f"{session.name}: invalid split boundaries.")

    return Split(
        total=total,
        train_end=int(train_end),
        validation_end=int(validation_end),
        cutoff=int(ordered[validation_end - 1]),
    )


def load_training_and_validation(
    files: Sequence[Path],
    session: Session,
    split: Split,
    extra_columns: Sequence[int] = (),
) -> pd.DataFrame:
    """Training + validation records of one session, in stable time order."""
    columns = sorted(set(dataset.REQUIRED_COLUMNS) | set(extra_columns))
    parts = []
    for file in files:
        print("Reading features:", file.name)
        for chunk in pd.read_csv(
            file, header=None, usecols=columns, chunksize=100_000, low_memory=False
        ):
            stime = chunk[dataset.STIME_INDEX]
            selected = chunk[(stime >= session.start) & (stime <= split.cutoff)]
            if not selected.empty:
                parts.append(selected)

    data = pd.concat(parts, ignore_index=True)
    if len(data) != split.validation_end:
        raise RuntimeError(f"{session.name}: loaded records do not match the split.")

    data = data.sort_values(by=dataset.STIME_INDEX, kind="stable").reset_index(drop=True)
    if not data[dataset.STIME_INDEX].is_monotonic_increasing:
        raise RuntimeError("Chronological ordering verification failed.")
    return data
