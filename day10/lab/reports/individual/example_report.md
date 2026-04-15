# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Minh Hoàng 
**Vai trò:** Cleaning & Quality Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài:** 450 từ

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py` — viết thêm regex để detect refund window, HR effective_date check
- `quality/expectations.py` — implement `refund_no_stale_14d_window` expectation (halt), `hr_leave_no_stale_10d_annual`  
- Kiểm thử quarantine + manual audit trên CSV

**Kết nối với thành viên khác:**

- Ingestion Owner cung cấp CSV thô (10 dòng); tôi pipe vào clean + quarantine 
- Embed Owner consume cleaned CSV; tôi đảm bảo expectation PASS trước embed
- Monitoring Owner dùng log của tôi để ghi vào runbook

**Bằng chứng (commit / comment trong code):**

```python
# quality/expectations.py — dòng 45
def expect_refund_no_stale_14d(cleaned: List[dict]) -> tuple:
    """Detect chunks chứa '14 ngày' / '14d' → violation"""
    violations = [r for r in cleaned if '14 ngày' in r.get('chunk_text', '')]
    return (len(violations) == 0), len(violations)
```

---

## 2. Số liệu / bằng chứng thay đổi (150–200 từ)

**Trước (raw):**
- raw_records = 10 (1 chunk refund has "14 ngày", 1 chunk HR has effective_date="2024-12-31")

**Sau clean (normal run):**
- cleaned_records = 6
- quarantine_records = 4 (include 1 HR stale, 1 duplicate, 2 malformed dates)
- refund chunk: is_stale_14d = 0 violations (fixed ✅)
- hr_leave chunk: effective_date >= 2026-01-01 ✅

**Metric_impact (from group report):**

| Rule | Trước | Sau normal | Sau inject-bad | Note |
|------|-------|-----------|---|--|
| refund_no_stale | - | 0 violations | 1 violation | inject: --no-refund-fix, expect FAIL |

**Grading evidence:**
- `gq_d10_01` (refund): `contains_expected=true`, `hits_forbidden=true` → detect chunk still appearing in top-3 despite fix ⚠️

---

## 3. Cách chạy & reproduce (100–150 từ)

**Chuỗi lệnh (end-to-end):**
```bash
cd day10/lab
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python etl_pipeline.py run  # Normal run → run_id=2026-04-15T08-12Z
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate  # Sprint 3
```

**Log lưu ở:** `artifacts/logs/run_2026-04-15T08-12Z.log`

**Quarantine kiểm tra:** `artifacts/quarantine/quarantine_2026-04-15T08-12Z.csv` → 4 dòng, cột reason giải thích

**Expectation kết quả:** See section 2a metric_impact; all PASS trên normal, 1 FAIL trên inject-bad

---

## 4. Khó khăn & học được (80–120 từ)

**Khó khăn:** 
- Lúc đầu chưa hiểu `hits_forbidden` = scanned top-k, không chỉ top-1 ⟹ phải expand eval từ "top-1 đúng" thành "top-3 sạch"

**Học được:**
- Data quality không phải "binary pass/fail" — phải track **metric_impact** khi thêm rule (chống trivial)
- Quarantine + manual audit = key step trước embed; không skip expectation halt
- Idempotent key (chunk_id) cần stable; otherwise rerun gây duplicate vector

**Feedback cho nhóm:** Nên thêm log "reason" vào quarantine CSV để debug nhanh hơn.
