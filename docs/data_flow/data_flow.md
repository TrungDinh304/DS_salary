# Data Flow Documentation

## Overview
Tài liệu mô tả luồng dữ liệu từ source đến dashboard.

So với phiên bản đầu, flow đã được điều chỉnh ở 3 điểm:
1. **Thêm bước "dirtying"**: chủ động làm dơ raw data trước khi đưa vào cleaning, để bước cleaning có nhiều case xử lý thực tế hơn (NULL, duplicates, sai kiểu, ngoại lai, sai chính tả, khoảng trắng thừa, ...).
2. **Object storage = MinIO**: dữ liệu đã xử lý không còn ghi xuống `data/processed/` ở local nữa, mà được upload lên MinIO.
3. **Transform vào Postgres DW**: cleaned data trên MinIO được nạp vào star schema (`migrations/001_*`, `002_*`) qua module `src/warehouse/`. Mỗi lần load được đánh dấu trong bảng `etl_runs` (migration `003_*`) — idempotent theo `(bucket, object_key, etag)`, mỗi fact row mang `loaded_run_id` để truy vết. Power BI đọc từ DW (không còn đọc trực tiếp MinIO).

---

## Data Flow Diagram

```
┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────┐
│ Kaggle  │──▶│ data/raw │──▶│ data/raw_    │──▶│ Cleaning │──▶│  MinIO   │──▶│ Transform →  │──▶│ Power BI │
│         │   │          │   │  dirty/      │   │ (NB 01)  │   │ (bucket: │   │ Postgres DW  │   │ (DW)     │
└─────────┘   └──────────┘   │ (artificial  │   └──────────┘   │ ds-salary)   │   (NB 02)    │   └──────────┘
                  │          │   noise)     │        │         └──────────┘   └──────────────┘
                  ▼          └──────────────┘        ▼                │              │
            ┌──────────┐            ▲                                 ▼              ▼
            │ Profiling│            │                          ┌──────────┐    ┌──────────┐
            │ (NB 00,  │            │                          │ Modeling/│    │ etl_runs │
            │  on dirty│     ┌──────────────┐                  │   EDA    │    │ (status, │
            │  layer)  │     │   Dirtying   │                  │  (src/)  │    │  lineage)│
            └──────────┘     │ (src/data/   │                  └──────────┘    └──────────┘
                             │  dirtify.py) │
                             └──────────────┘
```

---

## Layers

### 1. Source Layer
- **Source:** Kaggle dataset `hummaamqaasim/jobs-in-data`
- **Format:** CSV
- **Update frequency:** One-time download
- Tải về qua `src/data/load_data.py::load_raw_data_with_fallback`.

### 2. Raw Layer (`data/raw/`)
- Dữ liệu gốc, **KHÔNG chỉnh sửa**, không commit lại sau khi tải.
- File: `jobs_in_data.csv`
- Vai trò: nguồn tham chiếu (source of truth) cho mọi downstream.

### 3. Dirty Layer (`data/raw_dirty/`)  ← **NEW**
- Phiên bản raw được **chủ động làm dơ** để tạo bài tập cho cleaning.
- File: `jobs_in_data_dirty.csv`
- Sinh từ raw bằng module `src/data/dirtify.py` (sẽ thêm).
- Các phép "noise" nên áp dụng (ngẫu nhiên, có seed để reproducible):
  - Inject NULL vào ~3–5% các cell ở các cột không-key.
  - Duplicate ~1–2% số dòng (full-row hoặc near-duplicate).
  - Đổi kiểu: chuyển vài giá trị numeric thành string có ký tự lạ (vd. `"120000$"`, `"120,000"`).
  - Khoảng trắng thừa, mixed-case ở cột categorical (`" Senior "`, `"senior"`, `"SENIOR"`).
  - Sai chính tả vài giá trị enum (`"Remot"`, `"On-Site "`, `"Frelance"`).
  - Outlier rõ rệt cho `salary_in_usd` (vd. nhân 100).
  - Đổi tên 1–2 cột về dạng không chuẩn (snake_case ↔ Title Case).
- **Lưu ý**: dirty layer là input duy nhất của bước cleaning trong scope project; raw layer chỉ dùng để re-generate dirty khi cần.

### 4. Cleaning Step (Notebook `notebooks/01_cleaning.ipynb`)
- **Input:** `data/raw_dirty/jobs_in_data_dirty.csv`
- **Output:** dataframe đã clean → upload thẳng lên MinIO (không ghi local `data/processed/`).
- Transformations bắt buộc xử lý (đối ứng với các noise đã inject):
  - [ ] Standardize column names (snake_case)
  - [ ] Strip / normalize case ở cột categorical
  - [ ] Sửa giá trị enum sai chính tả (mapping)
  - [ ] Parse lại numeric columns (loại `$`, `,`)
  - [ ] Handle missing values
  - [ ] Remove duplicates
  - [ ] Detect & xử lý outlier salary
  - [ ] Data type conversion cuối cùng

### 5. Object Storage Layer — MinIO  ← **NEW**
- Service: `ds_salary_minio` (đã khai báo trong `compose.yaml`).
- Endpoint nội bộ: `http://minio:9000`; console: `http://localhost:${MINIO_CONSOLE_PORT}`.
- Credentials lấy từ `${MINIO_ACCESS_KEY}` / `${MINIO_SECRET_KEY}`.
- Bucket layout đề xuất:
  | Bucket | Object key | Nội dung |
  |--------|-----------|----------|
  | `processed` | `jobs/cleaned_data.parquet` | Output của bước cleaning |
  | `processed` | `jobs/cleaned_data.csv` | Bản CSV cho consumer không đọc Parquet (Power BI) |
  | `processed` | `jobs/_meta/run=<timestamp>.json` | Metadata mỗi lần chạy (row count, schema hash, ...) |
- Helper sẽ thêm vào `src/data/storage.py`:
  - `get_minio_client()` — đọc env, trả về `Minio` client.
  - `upload_dataframe(df, bucket, key, fmt="parquet")`
  - `download_dataframe(bucket, key)` cho EDA / modeling.

### 6. Warehouse Layer — Postgres DW  ← **NEW**
- Service: `ds_salary_db` (Postgres 15, đã khai báo trong `compose.yaml`).
- Schema: star schema được tạo bởi `migrations/001_create_dimensions.sql` + `migrations/002_create_fact_table.sql`.
  - Dims: `dim_date`, `dim_job_category`, `dim_job`, `dim_continent`, `dim_region`, `dim_location`, `dim_experience`, `dim_employment_type`, `dim_work_setting`, `dim_company_size`, `dim_currency`.
  - Fact: `fact_salary` với FK đến tất cả dims + `salary`, `salary_in_usd`, `loaded_run_id` (lineage).
- **ETL bookkeeping**: `migrations/003_create_etl_runs.sql` thêm bảng `etl_runs`:
  | Column | Ý nghĩa |
  |--------|---------|
  | `run_id` | PK, mỗi lần chạy `transform_to_dw` có 1 row |
  | `source_bucket`, `source_object_key`, `source_etag` | định danh object MinIO đã được nạp |
  | `status` | `running` / `success` / `failed` |
  | `started_at`, `completed_at`, `row_count`, `error_message` | telemetry |
- **Idempotency rule**: trước khi nạp, `transform_to_dw` query `etl_runs` theo `(bucket, key, etag, status='success')`. Nếu match → skip. Nếu etag đã đổi (data mới) → tạo run mới, **xoá fact rows của các run trước cùng object_key** (qua `loaded_run_id`), rồi insert lại.
- Module: `src/warehouse/`
  - `db.py` — `get_pg_connection()`, `pg_connection()` context manager.
  - `geo_mapping.py` — country → (continent, region) static dict, fallback `("Other", "Other")`.
  - `transform.py` — `transform_to_dw(object_key, bucket=None, fmt="parquet", force=False)`.

### 7. Dashboard Layer (`dashboards/`)
- Power BI file: `salary_dashboard.pbix`
- **Data source mới:** kết nối trực tiếp tới Postgres DW (host `localhost:${POSTGRES_PORT}`, db `${POSTGRES_DB}`).
- Không còn phụ thuộc file local `data/processed/` hay đọc trực tiếp MinIO — DW là nguồn duy nhất.

---

## Power BI Data Model

### Tables
| Table Name | Source | Description |
|------------|--------|-------------|
| fact_salary | DW `fact_salary` | Main fact table (salary, salary_in_usd + FK keys) |
| dim_* | DW `dim_*` | 11 dimensions: date, job, job_category, location, region, continent, experience, employment_type, work_setting, company_size, currency |

### Relationships
_(Define relationships between tables)_

### Measures
| Measure | Formula | Description |
|---------|---------|-------------|
| Avg Salary | `AVERAGE(Jobs[salary_in_usd])` | Average salary |
| Job Count | `COUNTROWS(Jobs)` | Total job postings |

---

## Dashboard Pages

### Page 1: Overview
- KPIs: Total Jobs, Avg Salary, Top Locations
- Salary distribution chart
- Jobs by category

### Page 2: Salary Analysis
- Salary by experience level
- Salary by job title
- Salary trend over time

### Page 3: Geographic Analysis
- Salary by country/region
- Remote vs On-site comparison

---

## Refresh Strategy
- **Manual refresh** (dataset là static).
- Khi re-run pipeline:
  1. (Tùy chọn) Re-download raw từ Kaggle.
  2. Chạy lại `dirtify` để regenerate `data/raw_dirty/`.
  3. Chạy lại `01_cleaning.ipynb` → upload object mới lên MinIO (overwrite `cleaned_data.{csv,parquet}`, MinIO sinh etag mới).
  4. Chạy lại `02_transform_to_dw.ipynb` → vì etag đã đổi, `etl_runs` không match cũ → tạo run mới, xoá fact rows cũ của cùng object_key, insert lại từ snapshot mới. Nếu etag không đổi thì notebook skip — đây chính là cơ chế "đánh dấu đã transform".
  5. Power BI bấm Refresh để pull bản mới từ DW.

---

## Env vars cần có (`.env`)
```
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
POSTGRES_PORT=5432
POSTGRES_HOST=localhost      # optional, default localhost

MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ENDPOINT=localhost:9000  # optional
MINIO_SECURE=false             # optional
BUCKET_NAME=ds-salary
```
