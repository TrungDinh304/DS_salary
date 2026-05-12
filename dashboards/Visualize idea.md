# 1. Salary Trend Analysis

## Mục tiêu

Hiểu xu hướng lương theo thời gian.

### Các câu hỏi phân tích

* Mức lương trung bình theo năm tăng hay giảm?
* Job category nào tăng lương nhanh nhất?
* Quốc gia nào có tốc độ tăng salary cao nhất?
* Salary của remote jobs thay đổi thế nào qua từng năm?

### Visualization gợi ý

* Line chart: AVG(salary_in_usd) theo year
* Multi-line chart theo job_category_name
* Area chart cho salary trend

---

# 2. Geographic Salary Analysis

## Mục tiêu

So sánh chênh lệch lương giữa các khu vực.

### Các câu hỏi phân tích

* Quốc gia nào trả lương cao nhất?
* Region nào có mức lương ổn định nhất?
* Chênh lệch salary giữa employee_country và company_country?
* Có hiện tượng “cross-border salary arbitrage” không?

### Insight thú vị

Ví dụ:

* Employee ở Asia nhưng làm cho company US → salary cao hơn local market bao nhiêu?

### Visualization

* Choropleth map
* Bubble map
* Heatmap country vs salary

---

# 3. Experience vs Salary Growth

## Mục tiêu

Phân tích ảnh hưởng của kinh nghiệm đến lương.

### Các câu hỏi

* Salary tăng bao nhiêu giữa Junior → Mid → Senior → Executive?
* Growth rate giữa các level có đồng đều không?
* Job category nào có salary progression mạnh nhất?

### Visualization

* Boxplot theo level_name
* Violin plot
* Bar chart AVG salary theo experience

---

# 4. Remote / Hybrid / Onsite Analysis

## Mục tiêu

Đánh giá tác động của work setting.

### Các câu hỏi

* Remote jobs có lương cao hơn onsite không?
* Quốc gia nào trả cao nhất cho remote worker?
* Remote phổ biến nhất ở ngành nào?
* Remote salary gap giữa senior và junior?

### Visualization

* Stacked bar
* Pie chart
* Boxplot salary theo setting_name

---

# 5. Company Size Impact

## Mục tiêu

Phân tích ảnh hưởng của quy mô công ty.

### Các câu hỏi

* Large companies trả cao hơn bao nhiêu?
* Startup nhỏ có trả cạnh tranh ở role nào?
* Company size nào tuyển nhiều remote nhất?

### Visualization

* Boxplot salary theo size_desc
* Heatmap size vs work setting
* Scatter average salary

---

# 6. Employment Type Analysis

## Mục tiêu

So sánh Full-time, Contract, Part-time,...

### Các câu hỏi

* Contract jobs có hourly-equivalent salary cao hơn không?
* Part-time có tập trung ở role nào?
* Employment type nào tăng mạnh theo thời gian?

### Visualization

* Bar chart
* Stacked area chart
* Sankey diagram

---

# 7. Job Market Demand & Premium

## Mục tiêu

Xác định role “hot”.

### Các câu hỏi

* Job title nào có salary cao nhất?
* Job category nào có salary variance lớn nhất?
* Những role nào có median salary tăng nhanh nhất?

### Visualization

* Treemap
* Pareto chart
* Histogram
* Ranking table

---

# 8. Salary Distribution Analysis

## Mục tiêu

Hiểu phân phối lương.

### Các câu hỏi

* Dataset có bị skewed không?
* Outlier salary nằm ở đâu?
* Salary distribution khác nhau thế nào giữa region?

### Visualization

* Histogram
* KDE plot
* Boxplot
* Violin plot

---

# 9. Employee vs Company Location Analysis

## Mục tiêu

Phân tích globalization của workforce.

### Các câu hỏi

* Quốc gia nào thuê nhiều international workers?
* Workers từ continent nào thường làm cho US companies?
* Có xu hướng outsource sang region lương thấp không?

### Visualization

* Sankey diagram
* Chord diagram
* Flow map

---

# 10. Currency & Economic Analysis

## Mục tiêu

Đánh giá salary raw vs normalized.

### Các câu hỏi

* Currency nào có salary raw cao nhất nhưng USD normalized thấp?
* Chênh lệch giữa salary và salary_in_usd?

### Visualization

* Dual-axis chart
* Scatter plot

---

# 11. Advanced Insights / Data Science Ideas

## A. Salary Prediction

Dự đoán salary_in_usd từ:

* experience
* country
* work setting
* company size
* employment type
* job category

### Model

* Linear Regression
* XGBoost
* Random Forest

---

## B. Clustering Job Market

Cluster các job theo:

* salary
* remote ratio
* region
* experience

→ tìm “market segment”.

---

## C. Anomaly Detection

Tìm:

* salary quá cao bất thường
* company size nhỏ nhưng trả cực cao
* junior salary cao bất thường

---

# 12. Dashboard Storytelling Ideas

## Dashboard 1 — Global Salary Overview

KPI:

* Avg Salary
* Highest Paying Country
* Fastest Growing Role
* Remote Ratio

Charts:

* Salary trend
* Salary map
* Top jobs

---

## Dashboard 2 — Career Growth Dashboard

* Salary theo experience
* Salary progression
* Job category comparison
* Remote impact

---

## Dashboard 3 — Hiring & Company Analysis

* Company size distribution
* Employment type
* Global hiring map
* International workforce flow

---

# 13. Một vài business question “xịn” để làm portfolio

### Beginner

* “Which countries offer the highest average salary for Data Engineers?”

### Intermediate

* “Does remote work reduce geographic salary gaps?”

### Advanced

* “How does experience level influence salary differently across regions and job categories?”

### Portfolio-level

* “Can we identify global outsourcing patterns in tech hiring based on employee-company location mismatch?”

---

# 14. Một vài metric nên tạo thêm

Bạn có thể tạo thêm calculated field:

```sql
salary_gap =
salary_in_usd - avg_salary_by_country
```

```sql
is_international_worker =
CASE
WHEN employee_country != company_country
THEN 1 ELSE 0
END
```

```sql
salary_band =
CASE
WHEN salary_in_usd < 50000 THEN 'Low'
WHEN salary_in_usd < 100000 THEN 'Medium'
ELSE 'High'
END
```

---

Dataset này khá mạnh để làm:

* Tableau dashboard
* Power BI portfolio
* Data analyst case study
* Data engineering demo warehouse
* ML salary prediction project

vì schema của bạn đã gần như là một star schema hoàn chỉnh cho BI analytics rồi.
