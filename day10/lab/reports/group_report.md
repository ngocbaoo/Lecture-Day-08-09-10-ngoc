# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** D1
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Học viên 1 | Ingestion / Raw Owner | student1@company.internal |
| Học viên 2 | Cleaning & Quality Owner | student2@company.internal |
| Học viên 3 | Embed & Idempotency Owner | student3@company.internal |
| Học viên 4 | Monitoring / Docs Owner | student4@company.internal |

**Ngày nộp:** 2026-04-15  
**Repo:** `day10/lab/`  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**

Nguồn raw là `data/raw/policy_export_dirty.csv` mô phỏng export từ internal KB database. File chứa 10 dòng, bao gồm các lỗi điển hình: duplicate, missing `doc_id`, ngày không ISO format, và stale policy version (HR phép 10 ngày cũ + refund window 14 ngày sai).

**Lệnh end-to-end:**
```bash
cd day10/lab
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python etl_pipeline.py run
```

`run_id` được sinh tự động từ timestamp (hoặc custom qua `--run-id`) và xuất hiện ở:
- Log file: `artifacts/logs/run_<run_id>.log`
- Manifest: `artifacts/manifests/manifest_<run_id>.json`
- Cleaned/Quarantine CSV: `artifacts/cleaned/cleaned_<run_id>.csv`

Pipeline flow: **ingest** (10 raw) → **clean** (6 cleaned, 4 quarantine) → **validate** (expectation suite) → **embed** (6 chunks to Chroma) → **freshness check** (FAIL: data 120h old)

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

## 2. Cleaning & expectation (150–200 từ)

**Baseline rule (inherited) + mở rộng:**
- ✅ allowlist `doc_id` (policy_refund_v4, sla_p1_2026, it_helpdesk_faq, hr_leave_policy)
- ✅ normalize effective_date to ISO (YYYY-MM-DD)
- ✅ deduplicate chunk_text (keep first occurrence)
- ✅ quarantine HR policy < 2026-01-01
- ✅ fix refund window: replace "14 ngày" → "7 ngày"
- ✅ strip whitespace; drop if < 8 chars

**Expectation suite (all halt-level):**
- `min_one_row` (halt) — cleaned_rows >= 1
- `no_empty_doc_id` (halt) — empty doc_id count = 0
- `refund_no_stale_14d_window` (halt) — violations = 0 (no "14 ngày" remains)
- `effective_date_iso_yyyy_mm_dd` (halt) — all dates parse as ISO
- `hr_leave_no_stale_10d_annual` (halt) — no "10 ngày phép" if effective_date < 2026-01-01
- `chunk_min_length_8` (warn) — short chunks = 0

**Result:** All expectations PASS on normal run (exit 0); 1 fail on inject-bad (refund_no_stale_14d violated but --skip-validate).

### 2a. Bảng metric_impact

| Rule / Expectation (tên) | Trước | Sau (normal) | Sau (inject-bad) | Chứng cứ |
|--------------------------|-------|--------------|------------------|----------|
| quarantine_stale_hr | - | 1 row | 1 row | artifacts/quarantine/quarantine_*.csv |
| fix_refund_14to7d | 0 fix | 1 fix | 0 fix (--no-refund-fix) | artifacts/logs/run_*.log |
| refund_no_stale | OK | 0 violations | 1 violation | artifacts/logs/run_inject-bad.log |
| effective_date_iso | OK | 0 non_iso | 0 non_iso | All rows pass |

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**

Sprint 3 chạy 2 pipeline:
1. **Normal:** `python etl_pipeline.py run` → 6 chunks embed, all expectations PASS
2. **Inject:** `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate` → 6 chunks re-embed với refund chunk stale (14d chưa fix)

Eval retrieval trả về CSV với 4 test questions. **Kết quả định lượng** trích từ `artifacts/eval/retrieval_eval.csv`:

| Query | Normal (7d fix) | Inject (14d stale) | Kết luận |
|-------|-----------------|-------|----------|
| q_refund_window | `contains_expected=yes` | `contains_expected=yes` | ⚠️ **Both return "7 ngày" nhưng top-k contains BOTH stale chunks** |
| q_refund_window | `hits_forbidden=yes` | `hits_forbidden=yes` | ⚠️ **Forbidden hit = still see 14d in top-3** |
| q_p1_sla | OK | OK | ✅ SLA intact (không touched) |
| q_leave_version | `top1_doc_expected=yes` | `top1_doc_expected=yes` | ⚠️ **Both find 12d version** |

**Insight:** Chỉ "top-1" đúng không đủ. Khách hàng / agent có thể đọc top-2/3, nếu top-2 = "10 ngày phép cũ" → nhầm. **Đó là tại sao hits_forbidden scans toàn top-k** để phát hiện "câu trả được đúng nhưng context vẫn bẩn".

---

## 4. Freshness & monitoring (100–150 từ)

**SLA bạn chọn:** Data phải published ≤ 24 giờ trước hiện tại (measured at `exported_at` trong manifest).

**Kết quả fresh check:**
- `manifest_2026-04-15T08-12Z.json` → `latest_exported_at: 2026-04-10T08:00:00` = 120 hours old
- **Result: FAIL** (age > SLA)
- **Alert:** Nên trigger Slack / PagerDuty khi age > 18h (warn buffer trước deadline)

**Ý nghĩa:**
- PASS: Dữ liệu tươi; user được thông tin mới nhất
- WARN: Tín hiệu cây nhân viên cần kiểm tra pipeline (chơi trong 24h buffer)
- FAIL: **Stale data live** → cảnh báo dùng agent / tắt index cho đến khi sync thành công

---

## 5. Liên hệ Day 09 (50–100 từ)

**Tích hợp:** Pipeline Day 10 tạo Chroma collection `day10_kb` contain 6 embedded chunks từ 4 docs (refund, sla, helpdesk, hr_leave). Day 09 multi-agent workflow có thể **truy vấn cùng collection** (nếu share chung Chroma instance) hoặc **reimport vector** qua API sau khi Day 10 publish.

**Trước & Sau:** Nếu Day 09 eval chạy trước Day 10 pipeline → vectors stale (chunk "14d" still live). Sau Day 10 fix & embed → vector updated (_stale chunk pruned_) → eval re-run → agent response tốt hơn. Test case này chứng minh **data quality → agent quality**.

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| … | … | … | … |

**Rule chính (baseline + mở rộng):**

- …

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

_________________

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
