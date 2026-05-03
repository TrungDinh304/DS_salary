-- =========================================
-- Migration: ETL run tracking + fact lineage
-- =========================================

BEGIN;

-- Track each load attempt from a MinIO source object into the warehouse.
CREATE TABLE IF NOT EXISTS etl_runs (
    run_id           SERIAL PRIMARY KEY,
    source_bucket    TEXT NOT NULL,
    source_object_key TEXT NOT NULL,
    source_etag      TEXT,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    row_count        INT,
    status           TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'success', 'failed')),
    error_message    TEXT
);

CREATE INDEX IF NOT EXISTS idx_etl_runs_lookup
    ON etl_runs (source_bucket, source_object_key, source_etag, status);

-- Lineage: link each fact row back to the run that loaded it.
ALTER TABLE fact_salary
    ADD COLUMN IF NOT EXISTS loaded_run_id INT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_fact_salary_run'
    ) THEN
        ALTER TABLE fact_salary
            ADD CONSTRAINT fk_fact_salary_run
            FOREIGN KEY (loaded_run_id) REFERENCES etl_runs(run_id);
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_fact_salary_run
    ON fact_salary (loaded_run_id);

COMMIT;
