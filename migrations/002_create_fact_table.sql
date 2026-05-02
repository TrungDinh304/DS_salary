CREATE TABLE fact_salary (
    fact_id SERIAL PRIMARY KEY,

    date_id INT REFERENCES dim_date(date_id),
    job_id INT REFERENCES dim_job(job_id),
    employee_location_id INT REFERENCES dim_location(location_id),
    company_location_id INT REFERENCES dim_location(location_id),
    experience_id INT REFERENCES dim_experience(experience_id),
    employment_type_id INT REFERENCES dim_employment_type(employment_type_id),
    work_setting_id INT REFERENCES dim_work_setting(work_setting_id),
    company_size_id INT REFERENCES dim_company_size(company_size_id),
    currency_id INT REFERENCES dim_currency(currency_id),

    salary BIGINT,
    salary_in_usd BIGINT
);