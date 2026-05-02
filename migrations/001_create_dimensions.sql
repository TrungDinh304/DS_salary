-- =========================================
-- Migration: Create Dimension Tables
-- =========================================

BEGIN;

-- ===== dim_date =====
CREATE TABLE IF NOT EXISTS dim_date (
    date_id SERIAL PRIMARY KEY,
    year INT UNIQUE NOT NULL
);

-- ===== dim_job_category =====
CREATE TABLE IF NOT EXISTS dim_job_category (
    job_category_id SERIAL PRIMARY KEY,
    job_category_name TEXT UNIQUE NOT NULL
);

-- ===== dim_job =====
CREATE TABLE IF NOT EXISTS dim_job (
    job_id SERIAL PRIMARY KEY,
    job_title TEXT NOT NULL,
    job_category_id INT REFERENCES dim_job_category(job_category_id),
    UNIQUE(job_title, job_category_id)
);

-- ===== dim_continent =====
CREATE TABLE IF NOT EXISTS dim_continent (
    continent_id SERIAL PRIMARY KEY,
    continent_name TEXT UNIQUE NOT NULL
);

-- ===== dim_region =====
CREATE TABLE IF NOT EXISTS dim_region (
    region_id SERIAL PRIMARY KEY,
    region_name TEXT NOT NULL,
    continent_id INT REFERENCES dim_continent(continent_id),
    UNIQUE(region_name, continent_id)
);

-- ===== dim_location =====
CREATE TABLE IF NOT EXISTS dim_location (
    location_id SERIAL PRIMARY KEY,
    country TEXT NOT NULL,
    region_id INT REFERENCES dim_region(region_id),
    UNIQUE(country)
);

-- ===== dim_experience =====
CREATE TABLE IF NOT EXISTS dim_experience (
    experience_id SERIAL PRIMARY KEY,
    level_code VARCHAR(5) UNIQUE NOT NULL,
    level_name TEXT,
    rank_order INT
);

-- ===== dim_employment_type =====
CREATE TABLE IF NOT EXISTS dim_employment_type (
    employment_type_id SERIAL PRIMARY KEY,
    type_code VARCHAR(5) UNIQUE NOT NULL,
    type_name TEXT
);

-- ===== dim_work_setting =====
CREATE TABLE IF NOT EXISTS dim_work_setting (
    work_setting_id SERIAL PRIMARY KEY,
    setting_name TEXT UNIQUE NOT NULL
);

-- ===== dim_company_size =====
CREATE TABLE IF NOT EXISTS dim_company_size (
    company_size_id SERIAL PRIMARY KEY,
    size_code VARCHAR(5) UNIQUE NOT NULL,
    size_desc TEXT
);

-- ===== dim_currency =====
CREATE TABLE IF NOT EXISTS dim_currency (
    currency_id SERIAL PRIMARY KEY,
    currency_code VARCHAR(10) UNIQUE NOT NULL
);

COMMIT;