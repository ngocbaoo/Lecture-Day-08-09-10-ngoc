# Kiến trúc pipeline — Lab Day 10

**Nhóm:** _______________  
**Cập nhật:** _______________

---

## 1. Sơ đồ luồng

```
data/raw/policy_export_dirty.csv (10 rows)
              |
              v
        [INGEST]
         load CSV
       run_id = timestamp
              |
              v log: raw_records=10
        [TRANSFORM]
     clean_rows() x2
   - allowlist doc_id
   - normalize date ISO
   - deduplicate text
   - fix refund 14->7
   - quarantine stale HR
              |
          6 cleaned / 4 quarantine
              |
              v log: cleaned=6, quarantine=4
    [QUALITY VALIDATE]
  run_expectations()
        All PASS
              |
              v
     [EMBED & VECTOR]
   -> vectorize 6 chunks
   -> upsert to Chroma (idempotent)
              |
     [FRESHNESS CHECK]
   latest_exported_at = 2026-04-10 (120h old)
   SLA cutoff = 24h
          RESULT: FAIL
              |
              v
          run_id logged
```

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|-----------------|
| Ingest | `data/raw/policy_export_dirty.csv` | raw_records (10), run_id | Ingestion Owner |
| Transform | raw_records + allowlist | cleaned CSV (6) + quarantine (4) | Cleaning Owner |
| Quality | cleaned CSV | expectation results + halt flag | Cleaning + QA Owner |
| Embed | cleaned CSV | vectors in Chroma + manifest | Embed Owner (idempotent upsert) |
| Monitor | manifest + SLA config | freshness PASS/WARN/FAIL | Monitoring Owner |

---

## 3. Idempotency & rerun

Một lần rerun pipeline với cùng raw data (không đổi):

1. **Transform:** 6 cleaned (cùng dữ liệu) → same `chunk_id`
2. **Embed:** Upsert theo `chunk_id` → Chroma **update existing vector** (không duplicate)
3. **Prune:** Xóa chunk id **không còn trong cleaned** → tường thời vector cũ

**Rerun 2 lần:** No duplicate vectors; collection state idempotent → safe to re-embed after code fix.

**Strategy:** `chunk_id = hash(doc_id + chunk_text)` → stable across runs; Chroma upsert với `ids=` parameter.

---

## 4. Liên hệ Day 09

Pipeline Day 10 cung cấp **cleaned KB corpus** cho Day 09 retrieval worker:
- **Shared `data/docs/`:** cùng 5 tài liệu (policy_refund, sla_p1, it_helpdesk, hr_leave, access_control)
- **Embed target:** Chroma collection `day10_kb` – thế này Day 09 agent có lệnh khởi tạo hoặc query
- **Before/after:** Day 09 `eval.py` có thể query collection này vào lúc trước & sau (sau fix Day 10 inject) → thấy hit quality từng bước

---

## 5. Rủi ro đã biết

- **Freshness FAIL in demo:** Raw data từ 2026-04-10 (intentional test case) – re-export nếu muốn PASS
- **Expectation halt injection:** `--skip-validate` flag cho phép embed dữ liệu xấu (Sprint 3 only)
- **HR version conflict:** v2015 (10 ngày) vs v2026 (12 ngày) cùng có thể nguy ụ nhầu; allowlist by `effective_date` là safeguard
- **Duplicate policy versions:** Nếu export chứa cả 14d + 7d window → quarantine sai cái, keep nguyên quán giải quyết upstream
