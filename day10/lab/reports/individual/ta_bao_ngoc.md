# Báo Cáo Cá Nhân - Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Tạ Bảo Ngọc 
**Vai trò:** Cleaning / Quality Owner  
**Ngày nộp:** 2026-04-15  

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi phụ trách phần cleaning và quality gate cho pipeline Day 10. Hai file chính tôi sửa là `transform/cleaning_rules.py` và `quality/expectations.py`, sau đó bổ sung logging trong `etl_pipeline.py` để chứng minh metric impact. Mục tiêu của tôi là làm rõ ranh giới clean, quarantine, và halt trước khi dữ liệu đi sang bước embed. Trong Sprint 1, tôi review raw CSV và đối chiếu với các canonical docs để chốt ground truth cho refund policy và HR leave policy. Sang Sprint 2, tôi thêm rule mới cho `exported_at`, future `effective_date`, và expectation mới cho timestamp và mojibake. 

**Kết nối với thành viên khác:**
Tôi phối hợp với người ingestion để giữ schema cleaned ổn định, và với người embed để xác định scenario inject nào sẽ dễ chứng minh before/after trong Sprint 3.

**Bằng chứng (commit / comment trong code):**
Bằng chứng rõ nhất là hai run `sprint2-smoke-conda` và `sprint3-bad`, cùng với các artifact trong `artifacts/logs/` và `artifacts/cleaned/`.

---

## 2. Một quyết định kỹ thuật
> VD: chọn halt vs warn, chiến lược idempotency, cách đo freshness, format quarantine.
Quyết định kỹ thuật quan trọng nhất của tôi là tách rõ `warn` và `halt` trong expectation suite. Tôi giữ `refund_no_stale_14d_window` là `halt` vì đây là lỗi nghiệp vụ có tác động trực tiếp đến câu trả lời của agent. Nếu pipeline vẫn publish khi còn chunk refund 14 ngày thì retrieval có thể vẫn hit stale context dù câu trả lời top-1 nhìn qua có vẻ đúng. Ngược lại, expectation `no_mojibake_artifacts_in_chunk_text` tôi để ở mức `warn` vì lỗi này ảnh hưởng đến khả năng đọc và chất lượng retrieval, nhưng chưa phải lúc nào cũng nghiêm trọng đến mức dừng toàn bộ publish.

Tôi cũng chọn normalize `exported_at` sang ISO-8601 UTC ngay trong cleaning thay vì để đến monitoring mới kiểm. Lý do là freshness và manifest đều phụ thuộc vào timestamp này. Nếu để timestamp không chuẩn đi qua cleaned layer thì phần freshness check phía sau sẽ khó truy vết hơn, và docs owner cũng khó giải thích boundary ingest/publish.

---

## 3. Một lỗi hoặc anomaly đã xử lý
> Mô tả triệu chứng → metric/check nào phát hiện → fix.
Anomaly rõ nhất tôi xử lý là stale refund policy. Trong raw export có một chunk của `policy_refund_v4` vẫn ghi `14 ngày làm việc`, trong khi canonical source `policy_refund_v4.txt` quy định `7 ngày làm việc`. Tôi dùng expectation để bắt lỗi này và dùng run inject để chứng minh rule cleaning thực sự có tác dụng. Ở run `sprint3-bad`, tôi chủ động tắt refund fix bằng flag `--no-refund-fix --skip-validate`. Kết quả trong log là `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`. Ở run clean `sprint2-smoke-conda`, cùng expectation này trở về `OK (halt) :: violations=0`.

Ngoài ra, tôi bổ sung validation cho `exported_at` và metric `exported_at_normalized_count`. Trong run clean, log ghi `exported_at_normalized_count=6`, cho thấy tất cả 6 cleaned rows đã được đưa về một format timestamp ổn định trước khi publish boundary. Đây là bằng chứng để người 4 có thể viết phần quality evidence và runbook mà không bị mơ hồ.

---

## 4. Bằng chứng trước / sau
> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.
Bằng chứng trực tiếp từ cleaned CSV và expectation log. Ở file `artifacts/cleaned/cleaned_sprint3-bad.csv`, chunk refund thứ hai vẫn chứa chuỗi `14 ngày làm việc`. Ở file `artifacts/cleaned/cleaned_sprint2-smoke-conda.csv`, cùng chunk đó đã được sửa thành `7 ngày làm việc` và có thêm marker `[cleaned: stale_refund_window]`.

Về mặt log, run `sprint3-bad` cho thấy `Expectation halt? = Yes`, còn run `sprint2-smoke-conda` cho thấy `Expectation halt? = No`. Hai dòng này khớp với bảng tổng hợp trong `docs/quality_report.md` và cũng là bằng chứng để group report điền phần metric impact.

---

## 5. Cải tiến tiếp theo
> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).
Nếu có thêm 2 giờ, tôi sẽ tạo một file raw inject riêng để chứng minh hai rule mới còn lại có tác động đo được: một dòng có `effective_date` nằm trong tương lai và một dòng có `exported_at` sai format. Cách này sẽ làm `future_effective_date_count` và expectation timestamp thay đổi thực sự trên artifact, giúp phần Sprint 3 đầy đặn hơn và giảm tranh cãi khi chấm anti-trivial.
