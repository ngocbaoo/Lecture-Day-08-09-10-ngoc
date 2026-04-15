# Quality report — Lab Day 10 (nhóm)

**run_id:** 2026-04-15T08-12Z (normal) + inject-bad (inject)  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (raw) | Sau clean | Quarantine | Ghi chú |
|---------|--------------|-----------|------------|----------|
| raw_records | 10 | - | - | 10 dòng từ policy export |
| cleaned_records | - | 6 | - | 6 hàng hợp lệ |
| quarantine_records | - | - | 4 | incomplete doc_id, stale HR, malformed date |
| Expectation halt? | - | PASS | - | All 6 halt-level expectations OK |
| Refund no_stale_14d | - | OK (0 violations) | - | Fixed 14d → 7d successfully |
| HR leave no_stale | - | OK (0 violations) | - | Filtered < 2026-01-01 |

---

## 2. Before / after retrieval (bắt buộc)

### Normal run (2026-04-15T08-12Z)

**Câu hỏi then chốt:** refund window (`q_refund_window`)  

| Mô tả | top1_doc_id | top1_preview | contains_expected | hits_forbidden | Ý nghĩa |
|------|------------|--------------|-------------------|----|----------|
| **Sau fix** | policy_refund_v4 | "Yêu cầu...vòng 7 ngày" | yes | **yes** | ⚠️ Chặt: chunk 14d vẫn ở trong top-k sau fix |

**Merit (khuyến nghị):** HR versioning — `q_leave_version`

| Mô tả | top1_doc_id | top1_preview | contains_expected | top1_doc_expected | Ý nghĩa |
|------|-------------|--------------|-------------------|----|----------|
| **Sau filter** | hr_leave_policy | "Nhân viên dưới 3 năm...12 ngày" | yes | **yes** | ✅ Top-1 đúng version 2026 (12d); stale 10d lọc ra |

---

## 3. Freshness & monitor

Kết quả: **FAIL** — data from 2026-04-10 08:00:00 → age ~120 hours (exceeds 24h SLA).

**Diễn giải SLA:**
- `measured_at: publish` = điểm tính là `exported_at` trong manifest
- `sla_hours: 24` = dữ liệu phải ≤ 24h từ publication
- **FAIL reason:** Mẫu dữ liệu có intentional 120h lag (mô phỏng scenario "export gặp" hoặc "sync broken")
- **Mitigation:** Re-export fresh data; setup SLA alert at 18h threshold (warn before hard 24h)

---

## 4. Corruption inject (Sprint 3)

**Mô tả kịch bản inject:**
1. Chạy `etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
2. `--no-refund-fix`: bỏ qua fix 14d → 7d, giữ nguyên chunk cũ "14 ngày"
3. `--skip-validate`: bỏ qua hàng expectation halt → continue embed xấu

**Kết quả:**
- Expectation `refund_no_stale_14d_window` = **FAIL** (1 violation detected)
- Nhưng embed vẫn giữ vì `--skip-validate` (simulation: imagine ops force-embed despite warning)
- `embed_prune_removed=1` = xóa chunk id cũ → nhưng 14d chunk mới lại được upsert *(lỗi bẳn tờ)*

**Proof:**
- Log: `artifacts/logs/run_inject-bad.log` chỉ FAIL expectation nhưng CONTINUE
- CSV: `artifacts/eval/retrieval_eval.csv` still shows `hits_forbidden=yes` cho refund q (14d vẫn có trong top-k)

---

## 5. Hạn chế & việc chưa làm

- **Sampling validation:** Hiện chỉ kiểm tra top-3; cần expand đến top-10 phát hiện "chặt" đủ sâu
- **Policy lineage tracking:** Chưa ghi "source commit / PDF version" trong metadata → cần thêm
- **CI/CD guardrail:** Expectation fail nên tự động block merge (hiện chỉ log warning)
- **Grading mở rộng:** 3 golden question; có thể thêm injection scenario → 5 question grading
