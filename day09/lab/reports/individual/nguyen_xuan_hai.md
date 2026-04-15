# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Xuân Hải  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `eval_trace.py`
- Functions tôi implement: `_normalize_trace`, `analyze_traces`, `compare_single_vs_multi`, `run_test_questions` và quản lý lưu trữ logs trong thư mục `artifacts/`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi xây dựng script đánh giá hệ thống, tiến hành gọi các luồng (từ `run_graph`) bằng các câu hỏi chuẩn bị sẵn. Kết quả chạy được tôi lưu trữ và biến đổi thành metadata chuẩn (trace JSON). Dựa vào các file traces được sinh ra từ quy trình của các agent khác, tôi tính toán metrics như `avg_confidence`, `hitl_rate` để đánh giá xem module routing và workers có hoạt động hiệu quả không.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
file eval_trace.py


---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Chuẩn hóa schema cho traces bằng `_normalize_trace` và tự động hóa định danh duy nhất (`run_id`).

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Việc log metrics từ multi-agent phức tạp hơn nhiều so với baseline vì phải thu thập từ mcp_tools_used, workers_called, route,... Việc code hàm chuẩn hóa kết quả đầu ra thành format cố định kèm tự động đặt tên file JSON theo ID câu hỏi và timestamp (`_make_unique_run_id`) giúp bảo vệ dữ liệu không bị ghi đè, và phân tích số liệu tự động (`analyze_traces`) hoạt động ổn định.

**Trade-off đã chấp nhận:**

Kích thước mỗi file JSON bị phình ra đôi chút vì lưu tất tần tật các key dù mang giá trị `False` hay list rỗng `[]`, nhưng đánh đổi này rất đáng do việc parse trace thống nhất sẽ không gặp lỗi KeyError.

**Bằng chứng từ trace/code:**

```python
# Đoạn code tự động tạo run_id unique chống ghi đè:
def _make_unique_run_id(base_run_id: str, q_id: str, index: int) -> str:
    """Ensure trace filename is unique per question/run to avoid overwrite collisions."""
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_base = base_run_id.strip() or "run"
    return f"{safe_base}_{q_id}_{index:02d}_{suffix}"

# Chuẩn hoá Schema để lưu file đồng nhất
def _normalize_trace(result: dict, task: str) -> dict:
    # ...
    trace = {
        "run_id": run_id,
        "task": str(result.get("task") or task),
        "supervisor_route": str(result.get("supervisor_route", "")),
        "workers_called": [str(w) for w in result.get("workers_called", []) if str(w).strip()],
        "mcp_tools_used": _normalize_mcp_tools(result.get("mcp_tools_used", [])),
        # ...
    }
    return trace
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** TypeError chặn quá trình tự động tạo báo cáo khi state data thiếu key định dạng chuẩn.

**Symptom (pipeline làm gì sai?):**

Khi chạy tập thử nghiệm test sets, nếu graph sinh ra exception bên trong graph hoặc workflow rẽ nhánh khác chuẩn dẫn đến các key `latency` hay `confidence` trở thành null hoặc String, quá trình đánh giá sụp đổ giữa chừng (văng exception) và làm bài test bị ngừng chạy.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

Do state dictionary trả về từ graph phụ thuộc logic từng worker và supervisor (thành phần của thành viên khác trong nhóm), nên không đồng nhất cấu trúc dữ liệu nếu hệ thống rẽ qua đường bị lỗi.

**Cách sửa:**

Tôi bọc các biến `latency_ms` hay `confidence` vào cấu trúc `try...except (TypeError, ValueError)` trong hàm `_normalize_trace`. Gán giá trị fallback an toàn như 0.0 theo đúng kiểu float/int mà không ngắt chương trình.

**Bằng chứng trước/sau:**

> Code trước khi sửa (Dễ bị crash khi biến bị null do route error):
```python
# Code cũ (nếu node lỗi trả về None cho latency_ms hoặc confidence)
latency_ms = int(result.get("latency_ms")) # Lỗi TypeError
confidence = float(result.get("confidence", 0.0)) # Lỗi TypeError hoặc ValueError nếu là chuỗi bậy
```

> Code sau khi sửa với Fallback an toàn, nằm tại hàm _normalize_trace:
```python
    latency = result.get("latency_ms")
    try:
        latency_ms = int(latency) if latency is not None else 0
    except (TypeError, ValueError):
        latency_ms = 0

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**

Xây dựng logic phân tích (`analyze_traces`) linh hoạt, cung cấp metric overview rõ ràng qua CLI cho test questions. Phương thức so sánh giúp đánh giá được ưu điểm của multi-agent thông qua metrics thay vì chỉ cảm tính.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Hàm `compare_single_vs_multi` chưa tự động load baseline mà mới chỉ làm nền tảng dictionary trống (TODO) dành cho người dùng điền manually điểm của Day 08.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Tiêu chuẩn đầu ra (grading logs) và chất lượng đánh giá báo cáo artifacts. Nếu không có file evaluaton chuẩn, nhóm sẽ không thể làm báo cáo xem luồng graph multi-agent xây dựng mới có tối ưu độ trễ và độ chính xác thực tế so với baseline cũ hay chưa.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào Worker Owner và Supervisor Owner phải tuân thủ chuẩn State Graph contract, nghĩa là phải chèn đầy đủ metadata (`route_reason`, `latency`, `retrieved_sources`) vào đúng các field quy định để đoạn mã thống kê không báo cáo sai số.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ sử dụng module `matplotlib` hoặc `seaborn` để trích xuất `artifacts/eval_report.json` thành biểu đồ (chart) trực quan hóa độ khác biệt latency giữa Single và Multi-agent, đồng thời tích hợp logic tự đọc file kết quả test của Day 08 vào baseline thay cho dữ liệu giả định.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
