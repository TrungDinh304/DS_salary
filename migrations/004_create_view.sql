CREATE OR REPLACE VIEW vw_salary_analytics AS
SELECT
    fs.fact_id,

    -- Date
    dd.year,

    -- Job
    dj.job_title,
    djc.job_category_name,

    -- Employee Location
    emp_loc.country AS employee_country,
    emp_reg.region_name AS employee_region,
    emp_cont.continent_name AS employee_continent,

    -- Company Location
    comp_loc.country AS company_country,
    comp_reg.region_name AS company_region,
    comp_cont.continent_name AS company_continent,

    -- Experience
    de.level_code,
    de.level_name,
    de.rank_order,

    -- Employment
    det.type_code,
    det.type_name,

    -- Work Setting
    dws.setting_name,

    -- Company Size
    dcs.size_code,
    dcs.size_desc,

    -- Currency
    dc.currency_code,

    -- Salary Metrics
    fs.salary,
    fs.salary_in_usd--,

    -- -- ETL Metadata
    -- er.run_id,
    -- er.started_at,
    -- er.completed_at,
    -- er.status

FROM fact_salary fs

-- Date
LEFT JOIN dim_date dd
    ON fs.date_id = dd.date_id

-- Job
LEFT JOIN dim_job dj
    ON fs.job_id = dj.job_id

LEFT JOIN dim_job_category djc
    ON dj.job_category_id = djc.job_category_id

-- Employee Location
LEFT JOIN dim_location emp_loc
    ON fs.employee_location_id = emp_loc.location_id

LEFT JOIN dim_region emp_reg
    ON emp_loc.region_id = emp_reg.region_id

LEFT JOIN dim_continent emp_cont
    ON emp_reg.continent_id = emp_cont.continent_id

-- Company Location
LEFT JOIN dim_location comp_loc
    ON fs.company_location_id = comp_loc.location_id

LEFT JOIN dim_region comp_reg
    ON comp_loc.region_id = comp_reg.region_id

LEFT JOIN dim_continent comp_cont
    ON comp_reg.continent_id = comp_cont.continent_id

-- Experience
LEFT JOIN dim_experience de
    ON fs.experience_id = de.experience_id

-- Employment Type
LEFT JOIN dim_employment_type det
    ON fs.employment_type_id = det.employment_type_id

-- Work Setting
LEFT JOIN dim_work_setting dws
    ON fs.work_setting_id = dws.work_setting_id

-- Company Size
LEFT JOIN dim_company_size dcs
    ON fs.company_size_id = dcs.company_size_id

-- Currency
LEFT JOIN dim_currency dc
    ON fs.currency_id = dc.currency_id

-- ETL Run
LEFT JOIN etl_runs er
    ON fs.loaded_run_id = er.run_id;