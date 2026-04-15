# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Minh Hoàng  
**Vai trò:** Ingestion Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** 420 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `etl_pipeline.py` — entrypoint ingestion, log run_id và raw_records
- `transform/cleaning_rules.py` — hàm `load_raw_csv()` để đọc CSV thô và xác định schema ingest
- `contracts/data_contract.yaml` / `docs/data_contract.md` — định nghĩa schema cleaned và nguồn dữ liệu canonical

**Mô tả trách nhiệm:**

Tôi chịu trách nhiệm phần ingestion: đọc file raw CSV (`data/raw/policy_export_dirty.csv`), xác định schema cần ingest, tạo `run_id`, và ghi log số lượng bản ghi đầu vào. Tôi đảm bảo rằng pipeline bắt đầu với dữ liệu thô đúng format và thông tin `run_id` được gắn xuyên suốt các artifact.

**Bằng chứng (code):**

```python
rows = load_raw_csv(raw_path)
raw_count = len(rows)
log(f"run_id={run_id}")
log(f"raw_records={raw_count}")
```

---

## 2. Số liệu / bằng chứng thay đổi (150–200 từ)

**Trước (raw ingestion):**

- Data source: `data/raw/policy_export_dirty.csv` chứa 10 dòng export thô.
- Tôi kiểm tra schema ingest gồm: `chunk_id`, `doc_id`, `chunk_text`, `effective_date`, `exported_at`.
- `raw_records=10` là chỉ số đầu tiên được log ngay sau ingest.

**Sau chạy pipeline ingestion:**

- `run_id=2026-04-15T08-12Z` được tạo và ghi trong log.
- `raw_records=10` được ghi thành công.
- Artifact log lưu tại: `artifacts/logs/run_2026-04-15T08-12Z.log`.

Phần ingestion của tôi chịu trách nhiệm thu thập và chuyển raw CSV vào pipeline, không bao gồm phần quy trình clean/quality chi tiết sau đó.

---

## 3. Cách chạy & reproduce (100–150 từ)

**Chuỗi lệnh:**

```bash
cd day10/lab
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python etl_pipeline.py run
```

**Kết quả mong đợi:**

- Log `run_id` xuất hiện
- `raw_records=10` được ghi
- `artifacts/logs/run_<run_id>.log` được tạo

Tôi chỉ cần chạy pipeline này để xác nhận ingestion đã hoạt động đúng; các bước sau đó (clean, validate, embed) là phần tiếp theo của flow nhưng không phải trọng tâm của vai trò ingestion.

---

## 4. Khó khăn & học được (80–120 từ)

**Khó khăn:**

- Phân biệt rõ ranh giới ingestion vs cleaning: ingestion phải đảm bảo dữ liệu thô được nạp và log đủ, còn việc xử lý chi tiết thuộc phần transform/quality.
- Ban đầu tôi có thể bị cuốn vào các rule clean mà quên phải tập trung vào `run_id` và `raw_records`.

**Học được:**

- Dữ liệu đầu vào phải được xác thực sơ bộ và traceable bằng `run_id`.
- Đoạn log `raw_records` là chỉ số cơ bản nhất để kiểm chứng ingest thành công trước khi chuyển sang bước clean.
- Cần phối hợp rõ với phần clean/quality để không lặp logic ingest và không mở rộng phạm vi quá sớm.

**Đề xuất:**

- Nên giữ `etl_pipeline.py` phần ingest đơn giản, chỉ extract + schema map + log.
- Các bước clean/validation nên triển khai ở module riêng để tránh nhập nhằng trách nhiệm.
