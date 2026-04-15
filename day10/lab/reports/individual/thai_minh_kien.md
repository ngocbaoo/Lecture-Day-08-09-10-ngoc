# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Thái Minh Kiên
**Vai trò:** Monitoring / Docs Owner
**Ngày nộp:** 15/04/2026

---

> **Tôi** phụ trách chính việc xây dựng hệ thống tài liệu (Documentation) và triển khai giám sát độ tươi mới của dữ liệu (Freshness Monitoring). Tôi đã hoàn thiện các file kiến trúc, contract và runbook, đồng thời đảm bảo các báo cáo chất lượng.

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `docs/pipeline_architecture.md`: Thiết kế sơ đồ luồng dữ liệu (Mermaid) và định nghĩa ranh giới trách nhiệm.
- `docs/data_contract.md`: Xây dựng schema chuẩn (cleaned) và các quy tắc cách ly dữ liệu (Quarantine).
- `docs/runbook.md`: Soạn thảo hướng dẫn xử lý sự cố khi hệ thống gặp lỗi chất lượng hoặc freshness.
- `monitoring/freshness_check.py`: Triển khai logic kiểm tra SLA 24h dựa trên manifest của pipeline.
- `reports/group_report.md`: Tổng hợp kết quả từ các thành viên để hoàn thiện báo cáo nhóm.

**Kết nối với thành viên khác:**
Tôi làm việc chặt chẽ với **Ingestion Owner** để lấy các thông số raw records và **Quality Owner** để cập nhật bảng `metric_impact` cũng như kết quả của bộ expectations vào báo cáo chất lượng.

**Bằng chứng (commit / comment trong code):**
Trong file `monitoring/freshness_check.py`, tôi đã xử lý logic so sánh `age_hours` với `sla_hours` (dòng 51-59) để trả về trạng thái PASS/FAIL cho pipeline.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Trong quá trình thiết kế **Data Contract**, tôi đã quyết định chia các mức độ vi phạm của Quality expectations thành hai loại: **Halt** và **Warn**. 
- Đối với các lỗi như sai chính sách hoàn tiền (`refund_no_stale_14d_window`) hoặc sai định dạng ngày tháng, tôi đặt mức độ là **Halt** để dừng ngay pipeline, ngăn chặn dữ liệu sai lọt vào Vector Store.
- Đối với các lỗi như độ dài chunk hơi ngắn (`chunk_min_length_8`) hoặc lỗi hiển thị nhẹ (`mojibake`), tôi đặt mức độ là **Warn** để ghi nhận vào log nhưng vẫn cho phép pipeline chạy tiếp. Quyết định này giúp cân bằng giữa tính toàn vẹn tuyệt đối của dữ liệu quan trọng và tính liên tục của hệ thống đối với các lỗi nhỏ không gây rủi ro cao.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Trong Sprint 3, khi thực hiện kịch bản "Inject Corruption", tôi đã phát hiện ra rằng nếu không có quy trình hậu kiểm, Agent sẽ truy xuất nhầm thông tin chính sách hoàn tiền cũ (14 ngày). 
- **Triệu chứng:** Kết quả retrieval trả về văn bản chứa từ khóa "14 ngày làm việc".
- **Phát hiện:** Expectation `refund_no_stale_14d_window` báo `passed=False` với mức độ `halt` trong log.
- **Xử lý:** Tôi đã cập nhật **Runbook** để hướng dẫn đội vận hành cách kiểm tra log run, manifest và cleaned CSV nhằm xác định đúng vị trí lỗi. Sau đó, tôi phối hợp với Cleaning Owner để kích hoạt rule auto-fix, chuyển đổi dữ liệu về đúng 7 ngày và kiểm tra lại bằng `eval_retrieval.py` cho đến khi cột `hits_forbidden` trong artifact eval trả về `False`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Dựa trên kết quả chạy pipeline:
- **Run ID (Bad):** `sprint3-bad` -> `hits_forbidden: True` (vẫn còn text "14 ngày").
- **Run ID (Clean):** `sprint2-smoke-conda` -> `hits_forbidden: False`.

Dữ liệu so sánh từ `quality_report.md`:
`After (clean run): expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`.
`Before (inject bad): expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm thời gian, tôi sẽ tích hợp tính năng **Automated Alerting**. Thay vì phải chạy lệnh manual `python etl_pipeline.py freshness`, hệ thống sẽ tự động gửi thông báo qua Slack hoặc Email mỗi khi log pipeline xuất hiện expectation `FAIL (halt)` hoặc dữ liệu bị "stale" vượt quá SLA 24 giờ.
