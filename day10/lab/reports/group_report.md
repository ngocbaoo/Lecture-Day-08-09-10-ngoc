# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** D1
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Lê Minh Hoàng | Ingestion / Raw Owner | phamhaihau1976@gmail.com |
| Tạ Bảo Ngọc | Cleaning & Quality Owner | ngoctabao@gmail.com |
| Nguyễn Xuân Hải | Embed & Idempotency Owner | nxhaicr7@gmail.com |
| Thái Minh Kiên | Monitoring / Docs Owner | minhkien242003@gmail.com |

**Ngày nộp:** 15/04/2026
**Repo:** https://github.com/ngocbaoo/Lecture-Day-08-09-10
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md`.  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after**.

---

## 1. Pipeline tổng quan (150–200 từ)

Hệ thống pipeline dữ liệu Day 10 tập trung vào việc xử lý các lỗi dữ liệu thô (Dirty CSV) để đảm bảo Agent không trả về các thông tin cũ hoặc sai lệch. Quy trình bao gồm: Ingest từ `policy_export_dirty.csv`, chuẩn hóa qua `cleaning_rules.py`, kiểm soát chất lượng qua `expectations.py` và nạp vào ChromaDB một cách idempotent.

**Tóm tắt luồng:**
- **Ingest:** Tải 10 bản ghi thô.
- **Clean:** Loại bỏ duplicate và fix quy định refund 14 -> 7 ngày. Kết quả thu được 6 bản ghi sạch.
- **Validate:** Chạy 8 expectations. Toàn bộ PASSED trong bản chạy chuẩn.
- **Embed:** Upsert 6 bản ghi vào collection `day10_kb`.

**Lệnh chạy một dòng:**
```bash
python etl_pipeline.py run --run-id 2026-04-15T08-41Z
```

---

## 2. Cleaning & expectation (150–200 từ)

Nhóm đã triển khai các rule để xử lý dữ liệu thực tế:

### 2a. Bảng metric_impact

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `raw_records` | 10 | 10 | Console Log |
| `cleaned_records` | 6 | 6 | `artifacts/cleaned/` |
| `embed_upsert` (Idempotent) | 6 (lần 1) | 6 (lần 2) | Console Log |
| `gq_d10_01` (refund grading) | stale refund rule disabled -> expectation FAIL | grading run `contains_expected=true`, `hits_forbidden=false` | `artifacts/logs/run_sprint3-bad.log`, `artifacts/eval/grading_run.jsonl` |
| `gq_d10_02` (P1 resolution grading) | source docs available but chưa chốt bằng grading artifact | grading run `contains_expected=true` với `top1_doc_id=sla_p1_2026` | `artifacts/eval/grading_run.jsonl` |
| `gq_d10_03` (HR version grading) | stale HR version bị quarantine khỏi cleaned snapshot | grading run `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` | `artifacts/quarantine/`, `artifacts/eval/grading_run.jsonl` |

**Rule chính:**
- **Auto-fix Refund:** Tự động sửa text "14 ngày" thành "7 ngày" kèm tag `[cleaned: stale_refund_window]`.
- **HR Stale Version:** Quarantine các policy cũ theo cutoff versioning đọc từ contract/env, không hard-code trực tiếp trong code.
- **Mojibake Fix:** Sửa lỗi hiển thị phông chữ tiếng Việt.

**Bằng chứng vượt baseline (Distinction - dynamic versioning):**
- Run `distinction-contract` dùng cutoff từ contract `2026-01-01` -> `stale_hr_quarantine_count=2`, `cleaned_records=6`.
- Run `distinction-env-override` dùng env `HR_LEAVE_MIN_EFFECTIVE_DATE=2025-01-01` -> `stale_hr_quarantine_count=0`, `cleaned_records=7`, `quarantine_records=16`.
- Khi nới cutoff xuống 2025-01-01, dòng HR 2025 đi vào cleaned CSV và expectation `hr_leave_no_stale_10d_annual` chuyển từ `OK` sang `FAIL (halt) :: violations=1`.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

Dựa trên log inject, cleaned CSV diff, và artifact grading `artifacts/eval/grading_run.jsonl`:

**Kịch bản inject:**
Khi chạy bản inject với flag `--no-refund-fix --skip-validate`, nhóm cố ý giữ lại chunk refund stale để kiểm tra khả năng phát hiện dữ liệu cũ. Ở bản inject, bằng chứng mạnh nhất đến từ expectation log `refund_no_stale_14d_window FAIL` và cleaned CSV còn chứa `14 ngày`.

**Kết quả định lượng (từ `artifacts/eval/grading_run.jsonl`):**
- **`gq_d10_01` - Refund window:** `top1_doc_id=policy_refund_v4`, `contains_expected=true`, `hits_forbidden=false`.
- **`gq_d10_02` - P1 resolution:** `top1_doc_id=sla_p1_2026`, `contains_expected=true`.
- **`gq_d10_03` - HR leave version:** `top1_doc_id=hr_leave_policy`, `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true`.
- **Tổng quan:** 3/3 câu grading đạt điều kiện theo artifact hiện tại.

**Before/after thực tế mà nhóm dùng để kết luận:**
- **Before (inject bad):** `artifacts/logs/run_sprint3-bad.log` ghi `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`, và `artifacts/cleaned/cleaned_sprint3-bad.csv` vẫn còn chunk refund `14 ngày làm việc`.
- **After (clean run):** `artifacts/logs/run_sprint2-smoke-conda.log` ghi `violations=0`, còn `artifacts/eval/grading_run.jsonl` xác nhận trạng thái collection sạch với 3/3 câu grading đạt, đặc biệt `gq_d10_03` có `top1_doc_matches=true`.

---

## 4. Freshness & monitoring (100–150 từ)

SLA được đặt là **24 giờ**. Trong manifest `2026-04-15T08-41Z`, kết quả báo **FAIL** vì `age_hours` lên tới 121h (do source data từ ngày 10/04). Điều này giúp nhóm nhận diện rõ sự lệch pha giữa hệ thống nguồn và pipeline.

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu sạch sau pipeline giúp Agent của Day 09 trả về câu trả lời chính xác cho người dùng (ví dụ: không trả lời sai về 14 ngày hoàn tiền). Việc tách biệt tầng dữ liệu này giúp Agent tập trung vào logic hội thoại thay vì phải lo lắng về tính đúng đắn của tài liệu.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Freshness SLA:** Cần cập nhật hệ thống nguồn để export đều đặn hơn nhằm đáp ứng SLA 24h.
- **Storage:** Vẫn cần theo dõi tình trạng Disk I/O của Chroma trên các môi trường khác nhau.
