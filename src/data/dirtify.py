"""Inject artificial noise into the raw dataset.

Mục đích: tạo một bản "dirty" của raw data để bước cleaning có nhiều case
xử lý thực tế hơn (NULL, duplicates, kiểu sai, khoảng trắng, sai chính tả,
outlier, đổi tên cột). Mọi phép noise đều dùng `random.Random(seed)` /
`np.random.default_rng(seed)` để reproducible.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ENUM_TYPOS = {
    "experience_level": {"Senior": "Sneior", "Mid-level": "Mid level", "Entry-level": "Entry"},
    "employment_type": {"Full-time": "Fulltime", "Freelance": "Frelance", "Contract": "Contrct"},
    "work_setting": {"Remote": "Remot", "In-person": "On-Site ", "Hybrid": "hybrid"},
    "company_size": {"L": "l", "M": " M", "S": "s "},
}

WHITESPACE_COLS = ("job_title", "job_category", "experience_level", "employment_type", "work_setting")
NULL_TARGET_COLS = ("salary_currency", "experience_level", "work_setting", "company_size", "job_category")
RENAME_MAP = {"salary_in_usd": "Salary In USD", "company_size": "CompanySize"}


def dirtify(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Return a dirtied copy of `df`. Original is not mutated."""
    rng = np.random.default_rng(seed)
    out = df.copy()

    # 1. Inject NULL ~4% per target column
    for col in NULL_TARGET_COLS:
        if col not in out.columns:
            continue
        mask = rng.random(len(out)) < 0.04
        out.loc[mask, col] = np.nan

    # 2. Duplicate ~1.5% rows
    n_dup = max(1, int(len(out) * 0.015))
    dup_idx = rng.choice(out.index, size=n_dup, replace=False)
    out = pd.concat([out, out.loc[dup_idx]], ignore_index=True)

    # 3. Whitespace + mixed case in categorical cols (~5%)
    for col in WHITESPACE_COLS:
        if col not in out.columns:
            continue
        mask = rng.random(len(out)) < 0.05
        idx = out.index[mask & out[col].notna()]
        flips = rng.integers(0, 4, size=len(idx))
        for i, flip in zip(idx, flips):
            val = str(out.at[i, col])
            if flip == 0:
                out.at[i, col] = f" {val}"
            elif flip == 1:
                out.at[i, col] = f"{val} "
            elif flip == 2:
                out.at[i, col] = val.upper()
            else:
                out.at[i, col] = val.lower()

    # 4. Enum typos
    for col, mapping in ENUM_TYPOS.items():
        if col not in out.columns:
            continue
        mask = rng.random(len(out)) < 0.03
        idx = out.index[mask & out[col].notna()]
        for i in idx:
            val = out.at[i, col]
            if val in mapping:
                out.at[i, col] = mapping[val]

    # 5. Numeric-as-string with junk chars in `salary` (~2%)
    if "salary" in out.columns:
        mask = rng.random(len(out)) < 0.02
        idx = out.index[mask]
        out["salary"] = out["salary"].astype(object)
        flips = rng.integers(0, 3, size=len(idx))
        for i, flip in zip(idx, flips):
            v = out.at[i, "salary"]
            if pd.isna(v):
                continue
            v_int = int(v)
            if flip == 0:
                out.at[i, "salary"] = f"{v_int}$"
            elif flip == 1:
                out.at[i, "salary"] = f"{v_int:,}"
            else:
                out.at[i, "salary"] = f" {v_int} "

    # 6. Inject obvious outliers in `salary_in_usd` (x100 on a few rows)
    if "salary_in_usd" in out.columns:
        n_outliers = max(1, int(len(out) * 0.002))
        out_idx = rng.choice(out.index, size=n_outliers, replace=False)
        out.loc[out_idx, "salary_in_usd"] = (
            pd.to_numeric(out.loc[out_idx, "salary_in_usd"], errors="coerce") * 100
        )

    # 7. Rename a couple of columns to non-snake_case
    out = out.rename(columns={k: v for k, v in RENAME_MAP.items() if k in out.columns})

    return out


def make_dirty_dataset(
    raw_path: str | Path = "data/raw/jobs_in_data.csv",
    dirty_path: str | Path = "data/raw_dirty/jobs_in_data_dirty.csv",
    seed: int = 42,
) -> Path:
    """Read raw CSV, dirtify, write to `dirty_path`. Returns the output path."""
    raw_path = Path(raw_path)
    dirty_path = Path(dirty_path)
    df = pd.read_csv(raw_path)
    dirty = dirtify(df, seed=seed)
    dirty_path.parent.mkdir(parents=True, exist_ok=True)
    dirty.to_csv(dirty_path, index=False)
    print(f"Wrote {len(dirty)} rows -> {dirty_path}")
    return dirty_path
