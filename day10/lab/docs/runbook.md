# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

- **Agent trả lời sai:** User hỏi về chính sách hoàn tiền, Agent trả lời "14 ngày làm việc" (quy định cũ) thay vì "7 ngày làm việc" (quy định mới v4).
- **Thiếu dữ liệu:** Agent không tìm thấy thông tin về IT Helpdesk mặc dù đã có document nguồn.

---

## Detection

- **Expectation Fail:** Log chạy pipeline báo `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`.
- **Freshness Alert:** Chạy `python etl_pipeline.py freshness` báo status `FAIL` do dữ liệu manifest đã quá 24h.
- **Eval Retrieval:** Cột `hits_forbidden` trong file eval có giá trị `True`.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Xác nhận `run_id`, `latest_exported_at`, `cleaned_records`, `quarantine_records` khớp với log của run đang điều tra. |
| 2 | Mở `artifacts/quarantine/*.csv` | Tìm các dòng có `reason: unknown_doc_id`, `missing_effective_date`, `duplicate_chunk_text` hoặc lỗi schema khác. |
| 3 | Chạy `python eval_retrieval.py` | Kiểm tra top-k context xem có chứa văn bản cấm (forbidden keywords) không. |
| 4 | Kiểm tra `artifacts/logs/run_*.log` và `artifacts/cleaned/*.csv` | Xác nhận expectation nào fail và tìm trực tiếp chunk refund stale `14 ngày` trong cleaned CSV nếu cần. |

---

## Mitigation

1. **Fix Source:** Cập nhật file CSV xuất từ hệ thống nguồn để khớp với canonical policy (v4).
2. **Rerun:** Chạy lại `python etl_pipeline.py run`.
3. **Emergency Fix:** Nếu pipeline halt do expectation, sử dụng flag `--skip-validate` (không khuyến nghị trừ khi cấp bách).
4. **Re-index:** Nếu vector store bị nhiễm dữ liệu cũ, thực hiện rerun pipeline clean để Chroma upsert/prune theo cleaned snapshot mới nhất.

---

## Prevention

- **Expectation suite:** Duy trì các rule kiểm tra refund stale, version HR và timestamp ở mức phù hợp (`halt` hoặc `warn`).
- **Automated Check:** Tích hợp freshness check vào cronjob hàng giờ.
- **Data Owner Alert:** Gửi notify qua Slack/Email khi `quarantine_records` tăng đột biến (> 20% raw).
