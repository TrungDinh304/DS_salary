# Jobs in Data — Salary Analysis

End-to-end data pipeline phân tích lương ngành Data: từ raw CSV trên Kaggle → object storage → data warehouse → Power BI dashboard.

Project được thiết kế theo **mindset Data Engineer**: tách rõ raw / dirty / cleaned / DW layers, idempotent ETL với lineage tracking, object storage thay vì local CSV, star schema cho phân tích.

---

## 1. Problem

Xác định các yếu tố ảnh hưởng đến `salary_in_usd` trong ngành Data (Data Scientist, Engineer, Analyst, ML, ...).

- **Objective**: ranking các chiều theo mức độ giải thích variance của salary.
- **Metric**: ANOVA F-stat + eta² per dim, Spearman correlation.
- **Stakeholder**: job seekers, HR, recruiters, career planners.

## 2. Dataset

- **Source**: [Kaggle — Jobs in Data](https://www.kaggle.com/datasets/hummaamqaasim/jobs-in-data) (`hummaamqaasim/jobs-in-data`).
- 9,355 rows × 12 cols (post-dedup ≈ 5,500).
- Cột chính: `work_year`, `job_title`, `job_category`, `experience_level`, `employment_type`, `work_setting`, `company_size`, `salary_currency`, `salary`, `salary_in_usd`, `employee_residence`, `company_location`.

## 3. Architecture

![](docs\data_flow\dataflow.png)

| Layer | Path / Service | Vai trò |
|---|---|---|
| Source | Kaggle | One-time download |
| Raw | `data/raw/jobs_in_data.csv` | Bản gốc immutable, không sửa |
| Dirty | `data/raw_dirty/jobs_in_data_dirty.csv` | **Cố tình làm dơ** raw (NULL, dup, typo, sai dtype, outlier, đổi tên cột) để cleaning có nội dung xử lý thực tế |
| Cleaned (canonical) | MinIO `processed/jobs/cleaned_data.{parquet,csv}` | Output của cleaning. Tag `etl_status=loaded` sau khi transform |
| Cleaned (historical) | MinIO `processed/jobs/historical/run_<id>_<ts>_*` | Snapshot bất biến mỗi lần load thành công — audit trail |
| Warehouse | Postgres `ds_salary` | Star schema: 1 fact + 11 dim + bảng `etl_runs` để track loads |
| Dashboard | `dashboards/DS_salary_dashboard.pbix` | Đọc trực tiếp từ DW (Npgsql connector) |

Chi tiết: [docs/data_flow/data_flow.md](docs/data_flow/data_flow.md).

## 4. Tech Stack

- **Python 3.13** — `pandas`, `numpy`, `seaborn`, `matplotlib`, `scipy`, `scikit-learn`
- **Storage**: MinIO (S3-compatible) cho processed data
- **DW**: PostgreSQL 15, star schema
- **Driver**: `minio` (S3 SDK), `psycopg[binary]` v3, `pyarrow` (parquet)
- **Infra**: Docker Compose orchestrates `ds_salary_db` + `ds_salary_minio`
- **BI**: Power BI Desktop với Npgsql connector

## 5. Project Structure

```
DS_salary/
├── compose.yaml                   # Postgres + MinIO services
├── config.yaml                    # paths, dataset id, bucket layout, dirty seed
├── requirements.txt
├── .env                           # POSTGRES_*, MINIO_*, BUCKET_NAME (gitignored)
│
├── data/
│   ├── raw/                       # immutable Kaggle dump (gitignored)
│   └── raw_dirty/                 # artificially-noised version
│
├── migrations/                    # auto-applied by Postgres on first boot
│   ├── 001_create_dimensions.sql
│   ├── 002_create_fact_table.sql
│   └── 003_create_etl_runs.sql
│
├── notebooks/
│   ├── 00_data_profiling.ipynb    # profile on dirty layer (issues to motivate cleaning)
│   ├── 01_cleaning.ipynb          # normalize + upload to MinIO
│   ├── 02_transform_to_dw.ipynb   # MinIO → DW, etl_runs + archive
│   └── 03_EDA.ipynb               # query DW, effect-size ranking, heatmaps
│
├── src/
│   ├── data/
│   │   ├── load_data.py           # Kaggle download w/ fallback
│   │   ├── dirtify.py             # inject artificial noise
│   │   ├── preprocess.py          # cleaning helpers
│   │   └── storage.py             # MinIO client: upload / download / copy / tag
│   ├── warehouse/
│   │   ├── db.py                  # Postgres connection (env-driven)
│   │   ├── geo_mapping.py         # country → (continent, region) static map
│   │   └── transform.py           # MinIO → dims + fact, etl_runs bookkeeping, archive
│   ├── features/                  # (placeholder)
│   └── models/                    # (placeholder)
│
├── dashboards/
│   ├── DS_salary_dashboard.pbix
│   └── Visualize idea.md
│
├── docs/
│   └── data_flow/data_flow.md     # full pipeline reference
│
└── outputs/                       # figures / reports
```

## 6. Setup

### Prereqs
- Python 3.13
- Docker Desktop
- Power BI Desktop + [Npgsql](https://www.npgsql.org/) (.NET Framework Provider, with GAC install) — restart PBI after install

### Steps

```powershell
# 1. Install Python deps
pip install -r requirements.txt

# 2. Create .env (Postgres + MinIO credentials)
#    Required keys: POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB POSTGRES_PORT
#                   MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_PORT MINIO_CONSOLE_PORT
#                   BUCKET_NAME (default: ds-salary)

# 3. Start infra (Postgres auto-applies migrations on first boot)
docker compose up -d

# 4. Run pipeline (notebooks in order): 00 -> 01 -> 02 -> 03
#    00 (profiling) and 03 (EDA) are read-only; 01 and 02 mutate state.
```

## 7. Pipeline Execution Order

| Step | Notebook | Reads from | Writes to | Idempotent? |
|---|---|---|---|---|
| 1 | `00_data_profiling` | `data/raw_dirty/` (auto-gen if missing) | (read-only) | ✓ |
| 2 | `01_cleaning` | `data/raw_dirty/` | MinIO `processed/jobs/cleaned_data.{parquet,csv}` | ✓ overwrites |
| 3 | `02_transform_to_dw` | MinIO canonical | Postgres DW + MinIO `processed/jobs/historical/` + tags | ✓ skips if `(bucket, key, etag)` already loaded |
| 4 | `03_EDA` | Postgres DW | (read-only) | ✓ |

**Re-run policy**: nếu data nguồn không đổi → re-run cleaning đẻ etag y nguyên → transform skip ngay. Nếu data đổi (cleaning ra etag mới) → transform tạo run mới, xoá fact rows từ run cũ cùng object_key, archive snapshot.

## 8. Key Design Decisions

- **Dirtify step (cố tình làm dơ raw)** — raw Kaggle khá sạch (chỉ có duplicates), nên không có nội dung cho cleaning. Dirtify chủ động inject NULL ~4%, dup ~1.5%, mixed-case, typo (`Sneior`, `Frelance`, `Remot`), salary-as-string (`"212,000"`), outlier (x100), rename cột — để cleaning có pipeline xử lý thực tế đầy đủ.
- **MinIO thay vì `data/processed/`** — object storage làm bridge giữa cleaning (write) và transform (read), không phụ thuộc filesystem local. Tag + historical snapshot phục vụ audit.
- **`etl_runs` table cho idempotency + lineage** — mỗi load = 1 row (`running` → `success` / `failed`); fact rows mang `loaded_run_id`. Re-run cùng etag → skip. Etag đổi → xoá facts cũ via lineage rồi insert lại.
- **Smart title-case + acronym preservation trong cleaning** — mode-based normalization fail với value hiếm (vd `Business Intelligence Manager` chỉ có vài rows). Smart-title deterministic + bảo toàn acronym (`AI`/`BI`/`ML`/`MLOps`/`AWS`/`ETL`) + lowercase connective (`of`/`and`).

## 9. Star Schema (DW)

```
                           ┌────────────┐
                           │ dim_date   │ (year)
                           └────────────┘
                                  │
                                  ▼
   dim_job ◀── dim_job_category  ─┤
                                  │
       dim_experience ────────────┤
                                  │
       dim_employment_type ───────┤
                                  │
       dim_work_setting ──────────┼──▶ fact_salary
                                  │    (salary, salary_in_usd, loaded_run_id)
       dim_company_size ──────────┤
                                  │
       dim_currency ──────────────┤
                                  │
       dim_location ──── dim_region ──── dim_continent
       (used 2x: employee + company)
```

- 11 dimensions + 1 fact (`fact_salary`)
- `fact_salary.loaded_run_id` → `etl_runs.run_id` (lineage)
- `dim_location` JOIN 2 lần vào fact (employee residence + company location). Khi dùng trong Power BI, đặt 1 relationship inactive và gọi qua `USERELATIONSHIP` trong measure.

## 10. EDA Highlights

Từ [notebooks/03_EDA.ipynb](notebooks/03_EDA.ipynb) chạy trên DW (5,500 rows):

- **Salary distribution**: median **$140k**, mean **$146k**, skew **+0.65** (mild right-skew — linear scale OK, không bắt buộc log).
- **Effect-size — 2 ranking song song**:
  - Theo **omega²** (cardinality-adjusted): `job_title` (0.163) > `employee_country` (0.158) > `experience_level` (0.153). Top-7 đều > 0.13 nhưng các chiều geographic chồng lấp lẫn nhau.
  - Theo **F/df** (per-group separation — clean signal nhất): `experience_level` (110.7) > `work_setting` (46.9) > `company_size` (43.5). `experience_level` áp đảo, 2.5× chiều thứ 2.
- **Tukey HSD on experience_level**: cả 6 cặp đều khác nhau có ý nghĩa (`p < 1e-9`). Ladder: Entry → Mid +$31k → Senior +$44k → Executive +$27k. Senior → Executive gap nhỏ nhất.
- **Spearman** `experience_rank ↔ salary_in_usd` = **+0.41** (monotonic vừa phải, không cao vì cùng level có spread rộng theo country).
- **Cross-border employment**: chỉ **2.1%** rows; trong đó **77% là Remote**.
- **Surprise**: `work_setting` (Remote/Hybrid/In-person) chỉ giải thích **3%** variance — narrative "remote = lương cao" không đúng trong dataset này.
- **employment_type** gần như vô nghĩa (omega² ≈ 0.009): ~99% rows là Full-time → unbalanced groups, có thể bỏ khỏi slicer.

## 11. Visualization Ideas

Xem [dashboards/Visualize idea.md](dashboards/Visualize%20idea.md) cho danh sách dashboard pages đề xuất: Overview, Salary deep-dive, Geography, Work setting, Decomposition Tree.
- Dashboard:
  ![](dashboards\Dashboard.png)

## 12. Roadmap

- [x] Star schema + ETL + lineage
- [x] EDA notebook (effect-size ranking)
- [x] Object storage tag + historical archive
- [x] Power BI dashboard (in progress) — kết nối DW qua Npgsql
- [ ] Data enrichment: PPP-adjusted salary (World Bank), cost-of-living
- [ ] Job-title normalization (collapse 125 titles → ~20 canonical families)
- [ ] Salary prediction model (XGBoost + SHAP) → factor contribution display trong PBI

## 13. References

- [docs/data_flow/data_flow.md](docs/data_flow/data_flow.md) — full pipeline reference
- [dashboards/Visualize idea.md](dashboards/Visualize%20idea.md) — visualization plan
- [migrations/](migrations/) — DDL for DW + ETL bookkeeping
