# Data Flow Documentation

## Overview
Tài liệu mô tả luồng dữ liệu từ source đến dashboard.

---

## Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Kaggle    │────▶│  data/raw/  │────▶│ data/       │────▶│  Power BI   │
│  (Source)   │     │             │     │ processed/  │     │ Dashboard   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                          │                   │
                          ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Profiling  │     │  Modeling   │
                    │ & Cleaning  │     │             │
                    │ (Notebook)  │     │  (src/)     │
                    └─────────────┘     └─────────────┘
                          │                   
                          ▼                  
                    ┌─────────────┐
                    │    EDA      │
                    │ (Notebook)  │
                    └─────────────┘
```

---

## Layers

### 1. Source Layer
- **Source:** Kaggle dataset `hummaamqaasim/jobs-in-data`
- **Format:** CSV
- **Update frequency:** One-time download

### 2. Raw Layer (`data/raw/`)
- Dữ liệu gốc, KHÔNG chỉnh sửa
- File: `jobs_in_data.csv`

### 3. Processed Layer (`data/processed/`)
- Dữ liệu đã clean
- File: `cleaned_data.csv`
- Transformations:
  - [ ] Remove duplicates
  - [ ] Handle missing values
  - [ ] Standardize column names
  - [ ] Data type conversion

### 4. Dashboard Layer (`dashboards/`)
- Power BI file: `salary_dashboard.pbix`
- Data source: `data/processed/cleaned_data.csv`

---

## Power BI Data Model

### Tables
| Table Name | Source | Description |
|------------|--------|-------------|
| Jobs | cleaned_data.csv | Main fact table |
| (Dim tables if needed) | | |

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
- **Manual refresh** (dataset is static)
- Hoặc setup scheduled refresh nếu data được update định kỳ
