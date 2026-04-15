# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

**Trường hợp 1: Policy sai**
- User / agent trả lời "khách hàng có 14 ngày để hoàn tiền" (sai, nên 7 ngày)
- Hoặc "nhân viên được 10 ngày phép" (sai, nên 12 ngày)
- Root cause: chunk stale từ tài liệu version cũ

**Trường hợp 2: Chunk missing**
- CSR / agent không tìm được câu trả lời cho P1 SLA query
- Root cause: chunk bị lọc vào quarantine hoặc không embed

---

## Detection

**Metric 1: Freshness SLA**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_*.json
# FAIL: "age_hours": 120, "sla_hours": 24
```

**Metric 2: Expectation fail**
- `refund_no_stale_14d_window` → FAIL = stale window detected
- `hr_leave_no_stale_10d_annual` → FAIL = old policy still in index

**Metric 3: Eval hits_forbidden**
```csv
q_refund_window,...,hits_forbidden=yes  # Content audit phát hiện sai policy trong top-k
```

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Check manifest `latest_exported_at` | Timestamp ≤ 24h trước publish; nếu > 24h → FAIL |
| 2 | Review `artifacts/quarantine/*.csv` | Nếu > 10% raw → investigate source quality |
| 3 | Run `python eval_retrieval.py --out /tmp/diag.csv` | `hits_forbidden=yes` cho refund/leave → expectation fail? |
| 4 | Grep `artifacts/logs/run_*.log` cho "FAIL" | Nếu expectation halt (severity=halt) → rollback embed |
| 5 | Check Chroma collection: `embed_upsert_count` | Nếu 0 → nothing changed; nếu spike → investigate upstream |

---

## Mitigation

**Nếu freshness FAIL (data > 24h):**
```bash
# Rerun pipeline (with mới) nếu source đã update
python etl_pipeline.py run --run-id hotfix-2026-04-15
# Nếu source chưa update: tạm banner UI "data last updated 120h ago"
```

**Nếu expectation fail (stale policy):**
```bash
# Xác nhận tài liệu source trong data/docs/
# Update policy file (VD policy_refund_v4.txt sửa 14→7 ngày)
# Rerun pipeline
python etl_pipeline.py run --run-id policy-fix-2026-04-15
# Verify: grep "expectation\[refund_no_stale_14d_window\] OK" artifacts/logs/run_*.log
```

**Rollback embed:**
```bash
# Nếu vừa embed dữ liệu xấu (skip-validate)
# Restore Chroma từ backup hoặc rerun pipeline chuẩn (mà không --skip-validate)
python etl_pipeline.py run --run-id rollback-2026-04-15
```

---

## Prevention

1. **Expectation coverage:** Thêm expectation mới khi phát hiện bug (PR → review + merge vào `quality/expectations.py`)
2. **Freshness alert:** Setup PagerDuty / Slack khi manifest `age_hours` > 18h (warn trước deadline 24h)
3. **Owner RACI:** "Data Engineering" owns ingest; "QA/SME" owns expectation setup; "ML Eng" owns embed idempotency
4. **Runbook versioning:** Sau mỗi incident, update runbook + test ("Tried Mitigation Step 3, took 15min")
5. **Day 11 continuity:** Nếu pipeline mở rộng → add CI/CD guardrail (schema compatibility, quarantine spike detection)
