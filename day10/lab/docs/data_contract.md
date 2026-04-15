# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| policy_refund_v4.txt | CSV export + parser | Stale version còn 14-day window thay vì 7-day | `refund_no_stale_14d_window` expectation (halt) |
| sla_p1_2026.txt | CSV export + parser | SLA timeout hoặc version conflict | `p1_sla_15min` expectation (halt) |
| it_helpdesk_faq.txt | CSV export + parser | Missing lockout count rule | `lockout_5_attempts` expectation (halt) |
| hr_leave_policy.txt | CSV export + parser | Old version 10 ngày vs new 12 ngày | `hr_leave_min_effective_date: 2026-01-01` allowlist |
| access_control_sop.txt | CSV export + parser | Duplicate SOP sections | `no_duplicate_chunk_text` deduplication |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash hoặc `doc_id + seq`; dùng để upsert idempotent trong Chroma |
| doc_id | string | Có | Từ allowlist (policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy); không allow doc lạ |
| chunk_text | string | Có | ≥ 8 ký tự sau strip; UTF-8 + tiếng Việt |
| effective_date | date | Có | ISO format YYYY-MM-DD; HR policy phải ≥ 2026-01-01 |
| exported_at | datetime | Có | Khi embed chunk (publish timestamp); dùng cho freshness check |

---

## 3. Quy tắc quarantine vs drop

**Quarantine → artifacts/quarantine/*.csv:**
- Dòng missing doc_id
- Dòng có effective_date không ISO format
- Dòng HR policy cũ (trước 2026-01-01)
- Dòng duplicate (cùng chunk_text)
- **Ai approve:** Cleaning & Quality Owner + SME (khi cần giải thích)

**Drop (không lưu log):**
- Dòng chunk_text < 8 ký tự (trim whitespace)
- Dòng whitespace-only

**Merge lại:** Khi SME xác nhận fix trong source; re-export + re-ingest (không hot-fix cleaned CSV)

---

## 4. Phiên bản & canonical

| Policy | File (source of truth) | Version | Effective | Comment |
|--------|------------------------|---------|-----------|----------|
| Refund | policy_refund_v4.txt | v4 | 2026-03-01 | **7 ngày làm việc** (lỗi: v3 còn 14 ngày) |
| P1 SLA | sla_p1_2026.txt | 2026 | 2026-01-01 | **15 phút** response; 4 giờ resolution |
| IT Helpdesk | it_helpdesk_faq.txt | 2026 | 2026-01-01 | Lockout **5 lần** đăng nhập sai |
| HR Leave | hr_leave_policy.txt | 2026 | 2026-01-01 | **12 ngày/năm** (< 3 năm); lỗi: v2015 còn 10 ngày |
| Access Control | access_control_sop.txt | 2026-Q1 | 2026-03-15 | Baseline trước RAG production |
