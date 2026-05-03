"""Transform cleaned data (in MinIO) into the Postgres data warehouse.

Flow:
1. Read cleaned dataframe from MinIO (bucket + object_key, etag captured).
2. Look up `etl_runs` — skip if a successful run already exists for the same
   (bucket, object_key, etag).
3. Open a single transaction:
   - Insert a new `etl_runs` row with status='running'.
   - Upsert dimension rows (idempotent on natural keys), build id maps.
   - Delete prior fact rows from earlier runs of the same source object
     (so the warehouse stays consistent if the source is re-loaded).
   - Insert fact rows linking back to this run via `loaded_run_id`.
   - Update `etl_runs` to status='success', completed_at, row_count.
4. On exception: mark run failed and re-raise.
"""
from __future__ import annotations

import posixpath
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import psycopg
from psycopg.rows import tuple_row

from src.data.storage import (
    copy_object,
    download_dataframe,
    get_bucket_name,
    get_minio_client,
    set_object_tags,
)
from src.warehouse.db import pg_connection
from src.warehouse.geo_mapping import lookup as lookup_region


EXPERIENCE_CODES = {
    "Entry-level": ("EN", "Entry-level", 1),
    "Mid-level":   ("MI", "Mid-level",   2),
    "Senior":      ("SE", "Senior",      3),
    "Executive":   ("EX", "Executive",   4),
}

EMPLOYMENT_CODES = {
    "Full-time": ("FT", "Full-time"),
    "Part-time": ("PT", "Part-time"),
    "Contract":  ("CT", "Contract"),
    "Freelance": ("FL", "Freelance"),
}

COMPANY_SIZE_DESC = {"L": "Large", "M": "Medium", "S": "Small"}


# ---------------------------------------------------------------------------
# Source-side helpers (MinIO)
# ---------------------------------------------------------------------------

def _stat_source(bucket: str, object_key: str) -> str | None:
    client = get_minio_client()
    try:
        st = client.stat_object(bucket, object_key)
        return st.etag
    except Exception:  # noqa: BLE001 — allow missing/unreadable
        return None


# ---------------------------------------------------------------------------
# Run bookkeeping
# ---------------------------------------------------------------------------

def is_already_loaded(conn: psycopg.Connection, bucket: str, key: str, etag: str | None) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM etl_runs
            WHERE source_bucket = %s
              AND source_object_key = %s
              AND COALESCE(source_etag, '') = COALESCE(%s, '')
              AND status = 'success'
            LIMIT 1
            """,
            (bucket, key, etag),
        )
        return cur.fetchone() is not None


def _start_run(conn: psycopg.Connection, bucket: str, key: str, etag: str | None) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etl_runs (source_bucket, source_object_key, source_etag, status)
            VALUES (%s, %s, %s, 'running')
            RETURNING run_id
            """,
            (bucket, key, etag),
        )
        return cur.fetchone()[0]


def _finish_run(conn: psycopg.Connection, run_id: int, status: str, row_count: int | None, error: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE etl_runs
            SET status = %s,
                completed_at = NOW(),
                row_count = %s,
                error_message = %s
            WHERE run_id = %s
            """,
            (status, row_count, error, run_id),
        )


# ---------------------------------------------------------------------------
# Dimension upserts
# ---------------------------------------------------------------------------

def _upsert_returning(
    conn: psycopg.Connection,
    table: str,
    columns: list[str],
    rows: Iterable[tuple],
    conflict_cols: list[str],
    pk: str,
) -> dict[tuple, int]:
    """Insert rows; on conflict do nothing. Re-select to build {natural_key: pk}."""
    rows = list(rows)
    if not rows:
        return {}

    placeholders = ", ".join(["(" + ", ".join(["%s"] * len(columns)) + ")"] * len(rows))
    flat = [v for row in rows for v in row]
    col_list = ", ".join(columns)
    conflict_list = ", ".join(conflict_cols)

    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {table} ({col_list}) VALUES {placeholders} "
            f"ON CONFLICT ({conflict_list}) DO NOTHING",
            flat,
        )
        # Re-select all rows by natural key
        natural_idx = [columns.index(c) for c in conflict_cols]
        keys = [tuple(row[i] for i in natural_idx) for row in rows]
        sel_placeholders = "(" + ", ".join(conflict_cols) + ") IN (" + \
            ", ".join(["(" + ", ".join(["%s"] * len(conflict_cols)) + ")"] * len(keys)) + ")"
        flat_keys = [v for k in keys for v in k]
        cur.execute(
            f"SELECT {pk}, {conflict_list} FROM {table} WHERE {sel_placeholders}",
            flat_keys,
        )
        result = {}
        for row in cur.fetchall():
            result[tuple(row[1:])] = row[0]
        return result


def _load_dim_date(conn: psycopg.Connection, df: pd.DataFrame) -> dict[int, int]:
    years = sorted(df["work_year"].dropna().astype(int).unique().tolist())
    rows = [(y,) for y in years]
    m = _upsert_returning(conn, "dim_date", ["year"], rows, ["year"], "date_id")
    return {k[0]: v for k, v in m.items()}


def _load_dim_currency(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    codes = sorted(df["salary_currency"].dropna().astype(str).unique().tolist())
    rows = [(c,) for c in codes]
    m = _upsert_returning(conn, "dim_currency", ["currency_code"], rows, ["currency_code"], "currency_id")
    return {k[0]: v for k, v in m.items()}


def _load_dim_work_setting(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    names = sorted(df["work_setting"].dropna().astype(str).unique().tolist())
    rows = [(n,) for n in names]
    m = _upsert_returning(conn, "dim_work_setting", ["setting_name"], rows, ["setting_name"], "work_setting_id")
    return {k[0]: v for k, v in m.items()}


def _load_dim_company_size(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    codes = sorted(df["company_size"].dropna().astype(str).unique().tolist())
    rows = [(c, COMPANY_SIZE_DESC.get(c, c)) for c in codes]
    m = _upsert_returning(conn, "dim_company_size", ["size_code", "size_desc"], rows, ["size_code"], "company_size_id")
    return {k[0]: v for k, v in m.items()}


def _load_dim_experience(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    levels = sorted(df["experience_level"].dropna().astype(str).unique().tolist())
    rows = []
    for lvl in levels:
        code, name, rank = EXPERIENCE_CODES.get(lvl, (lvl[:5].upper(), lvl, 99))
        rows.append((code, name, rank))
    m = _upsert_returning(
        conn, "dim_experience",
        ["level_code", "level_name", "rank_order"],
        rows, ["level_code"], "experience_id",
    )
    # Map back from level_name (the value present in the source) to id
    name_to_id = {row[1]: m[(row[0],)] for row in rows}
    return name_to_id


def _load_dim_employment_type(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    types = sorted(df["employment_type"].dropna().astype(str).unique().tolist())
    rows = []
    for t in types:
        code, name = EMPLOYMENT_CODES.get(t, (t[:5].upper(), t))
        rows.append((code, name))
    m = _upsert_returning(
        conn, "dim_employment_type",
        ["type_code", "type_name"],
        rows, ["type_code"], "employment_type_id",
    )
    name_to_id = {row[1]: m[(row[0],)] for row in rows}
    return name_to_id


def _load_dim_job_category(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    cats = sorted(df["job_category"].dropna().astype(str).unique().tolist())
    rows = [(c,) for c in cats]
    m = _upsert_returning(
        conn, "dim_job_category",
        ["job_category_name"], rows, ["job_category_name"], "job_category_id",
    )
    return {k[0]: v for k, v in m.items()}


def _load_dim_job(
    conn: psycopg.Connection, df: pd.DataFrame, job_category_map: dict[str, int]
) -> dict[tuple[str, int], int]:
    pairs = (
        df[["job_title", "job_category"]]
        .dropna()
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    rows = []
    for title, cat in pairs:
        cat_id = job_category_map.get(cat)
        if cat_id is None:
            continue
        rows.append((title, cat_id))
    return _upsert_returning(
        conn, "dim_job",
        ["job_title", "job_category_id"], rows,
        ["job_title", "job_category_id"], "job_id",
    )


def _load_geo(conn: psycopg.Connection, df: pd.DataFrame) -> dict[str, int]:
    """Populate dim_continent / dim_region / dim_location and return country -> location_id."""
    countries = sorted(set(
        df["employee_residence"].dropna().astype(str).tolist()
        + df["company_location"].dropna().astype(str).tolist()
    ))

    # 1. continents
    continent_to_region = [(c, lookup_region(c)) for c in countries]
    continents = sorted({r[1][0] for r in continent_to_region})
    cont_map = _upsert_returning(
        conn, "dim_continent",
        ["continent_name"], [(c,) for c in continents],
        ["continent_name"], "continent_id",
    )
    cont_map = {k[0]: v for k, v in cont_map.items()}

    # 2. regions
    region_rows = sorted({(region, cont_map[continent]) for _, (continent, region) in continent_to_region})
    region_map_raw = _upsert_returning(
        conn, "dim_region",
        ["region_name", "continent_id"], region_rows,
        ["region_name", "continent_id"], "region_id",
    )
    region_map = {(name, cont_id): rid for (name, cont_id), rid in region_map_raw.items()}

    # 3. locations
    loc_rows = []
    for country in countries:
        continent, region = lookup_region(country)
        rid = region_map[(region, cont_map[continent])]
        loc_rows.append((country, rid))
    loc_map_raw = _upsert_returning(
        conn, "dim_location",
        ["country", "region_id"], loc_rows,
        ["country"], "location_id",
    )
    return {k[0]: v for k, v in loc_map_raw.items()}


# ---------------------------------------------------------------------------
# Fact load
# ---------------------------------------------------------------------------

def _delete_prior_facts(conn: psycopg.Connection, bucket: str, key: str, current_run_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM fact_salary
            WHERE loaded_run_id IN (
                SELECT run_id FROM etl_runs
                WHERE source_bucket = %s AND source_object_key = %s AND run_id <> %s
            )
            """,
            (bucket, key, current_run_id),
        )
        return cur.rowcount


def _insert_facts(
    conn: psycopg.Connection,
    df: pd.DataFrame,
    run_id: int,
    *,
    date_map, currency_map, work_setting_map, company_size_map,
    experience_map, employment_map, job_map, job_category_map, location_map,
) -> int:
    cols = [
        "date_id", "job_id", "employee_location_id", "company_location_id",
        "experience_id", "employment_type_id", "work_setting_id",
        "company_size_id", "currency_id",
        "salary", "salary_in_usd", "loaded_run_id",
    ]
    rows = []
    skipped = 0
    for r in df.itertuples(index=False):
        try:
            cat_id = job_category_map[r.job_category]
            row = (
                date_map[int(r.work_year)],
                job_map[(r.job_title, cat_id)],
                location_map[r.employee_residence],
                location_map[r.company_location],
                experience_map[r.experience_level],
                employment_map[r.employment_type],
                work_setting_map[r.work_setting],
                company_size_map[r.company_size],
                currency_map[r.salary_currency],
                None if pd.isna(r.salary) else int(r.salary),
                None if pd.isna(r.salary_in_usd) else int(r.salary_in_usd),
                run_id,
            )
            rows.append(row)
        except (KeyError, ValueError):
            skipped += 1

    if skipped:
        print(f"  warn: skipped {skipped} fact rows due to missing dim mapping")

    if not rows:
        return 0

    # Use COPY (bulk insert) — INSERT ... VALUES would blow past Postgres'
    # 65535-parameter wire-protocol limit on datasets of this size.
    col_list = ", ".join(cols)
    with conn.cursor() as cur:
        with cur.copy(f"COPY fact_salary ({col_list}) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
    return len(rows)


# ---------------------------------------------------------------------------
# Post-load: mark source object as historical
# ---------------------------------------------------------------------------

def _archive_loaded_object(bucket: str, source_key: str, run_id: int, etag: str | None) -> str:
    """Tag the canonical object as historical and copy a versioned snapshot.

    - Tags applied to the canonical object: etl_status=loaded, etl_run_id,
      etl_loaded_at, etl_etag — visible in MinIO console and via API.
    - Snapshot copied to `<dir>/historical/run_<id>_<ts>_<filename>` so the
      exact bytes loaded by this run are preserved even if the canonical is
      overwritten by the next cleaning run.
    """
    loaded_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parent = posixpath.dirname(source_key)
    filename = posixpath.basename(source_key)
    prefix = f"{parent}/historical" if parent else "historical"
    historical_key = f"{prefix}/run_{run_id}_{loaded_at}_{filename}"

    copy_object(source_key, historical_key, src_bucket=bucket, dst_bucket=bucket)
    set_object_tags(
        source_key,
        {
            "etl_status": "loaded",
            "etl_run_id": str(run_id),
            "etl_loaded_at": loaded_at,
            "etl_etag": (etag or "").strip('"'),
        },
        bucket=bucket,
    )
    return historical_key


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def transform_to_dw(
    object_key: str,
    bucket: str | None = None,
    fmt: str = "parquet",
    *,
    force: bool = False,
) -> dict:
    """Load the cleaned object from MinIO into the warehouse.

    Returns a dict with run metadata. If a successful run already exists for
    the same (bucket, object_key, etag) and `force=False`, the load is skipped
    and the existing run info is returned.
    """
    bucket = bucket or get_bucket_name()
    etag = _stat_source(bucket, object_key)

    with pg_connection() as conn:
        conn.row_factory = tuple_row

        if not force and is_already_loaded(conn, bucket, object_key, etag):
            print(f"Skip: {bucket}/{object_key} (etag={etag}) already loaded")
            return {"status": "skipped", "bucket": bucket, "object_key": object_key, "etag": etag}

        df = download_dataframe(object_key, bucket=bucket, fmt=fmt)
        print(f"Downloaded {len(df)} rows from s3://{bucket}/{object_key}")

        # Record the run start in its own committed transaction, so the row
        # survives even if the dim/fact load fails and gets rolled back.
        run_id = _start_run(conn, bucket, object_key, etag)
        conn.commit()

        try:
            date_map = _load_dim_date(conn, df)
            currency_map = _load_dim_currency(conn, df)
            work_setting_map = _load_dim_work_setting(conn, df)
            company_size_map = _load_dim_company_size(conn, df)
            experience_map = _load_dim_experience(conn, df)
            employment_map = _load_dim_employment_type(conn, df)
            job_category_map = _load_dim_job_category(conn, df)
            job_map = _load_dim_job(conn, df, job_category_map)
            location_map = _load_geo(conn, df)

            deleted = _delete_prior_facts(conn, bucket, object_key, run_id)
            if deleted:
                print(f"Deleted {deleted} fact rows from prior runs of same source")

            n = _insert_facts(
                conn, df, run_id,
                date_map=date_map, currency_map=currency_map,
                work_setting_map=work_setting_map, company_size_map=company_size_map,
                experience_map=experience_map, employment_map=employment_map,
                job_map=job_map, job_category_map=job_category_map,
                location_map=location_map,
            )

            _finish_run(conn, run_id, "success", n, None)
            conn.commit()
            print(f"Loaded run_id={run_id} with {n} fact rows")

            historical_key = _archive_loaded_object(bucket, object_key, run_id, etag)
            print(f"Archived snapshot -> s3://{bucket}/{historical_key}")

            return {
                "status": "success", "run_id": run_id, "row_count": n,
                "bucket": bucket, "object_key": object_key, "etag": etag,
                "historical_key": historical_key,
            }
        except Exception as exc:
            conn.rollback()
            # Mark the (committed) run as failed in a fresh transaction.
            _finish_run(conn, run_id, "failed", None, str(exc)[:500])
            conn.commit()
            raise
