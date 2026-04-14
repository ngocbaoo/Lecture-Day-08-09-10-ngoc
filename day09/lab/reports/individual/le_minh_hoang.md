# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Minh Hoàng  
**Vai trò trong nhóm:** Supervisor Owner
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
- File chính: `graph.py`
- Functions tôi implement: `supervisor_node()`, `route_decision()`, `AgentState`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi đã refactor RAG pipeline từ Day 08 thành Supervisor-Worker graph. Supervisor node đọc task và quyết định route sang retrieval_worker, policy_tool_worker, hoặc human_review dựa trên keyword matching và risk flag. Policy_tool_worker kiểm tra policy và gọi MCP tools (mocked) để lấy thông tin ticket/policy. Synthesis_worker tổng hợp answer với citation. Các worker giao tiếp qua AgentState chia sẻ.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

```
commit ceb8a30 (hoang)
Author: Le Minh Hoang
Date:   Mon Apr 14 16:02:52 2026 +0700

    Finish graph.py
```

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi quyết định dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**
Việc sử dụng keyword-based routing giúp hệ thống đạt độ trễ cực thấp (gần như 0ms cho bước định tuyến) so với việc gọi LLM (thường mất 500ms - 2s). Với các bài toán nội bộ có bộ từ khóa đặc trưng (như "P1", "SLA", "hoàn tiền", "quy trình"), phương pháp này đảm bảo tính ổn định tuyệt đối và dễ dàng kiểm soát luồng dữ liệu mà không lo ngại về tính ngẫu nhiên (hallucination) của LLM trong bước quyết định kiến trúc.

**Trade-off đã chấp nhận:**
Hệ thống sẽ kém linh hoạt với những câu hỏi hành văn quá phức tạp hoặc không chứa từ khóa chỉ định. Tuy nhiên, tôi đã bù đắp bằng cách đặt `retrieval_worker` làm mặc định và thêm logic `risk_high` để kích hoạt Human-In-The-Loop (HITL) cho các trường hợp chứa mã lỗi lạ mà chưa có keyword phân loại rõ ràng.

**Bằng chứng từ trace/code:**

```python
    # 0. Defaults
    route = "retrieval_worker"
    route_reason = "default routing"
    needs_tool = False
    risk_high = False

    # 2. Logic routing
    if any(kw in task for kw in policy_keywords):
        route = "policy_tool_worker"
        route_reason = "task contains policy/access keywords"
        needs_tool = True
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** `UnicodeEncodeError` và `UnboundLocalError` trong module `graph.py`.

**Symptom (pipeline làm gì sai?):**
Khi chạy thử nghiệm trên terminal Windows, pipeline bị crash ngay lập tức khi gặp các ký tự định danh Unicode như `▶` hoặc `⚠️`. Ngoài ra, nếu input không khớp với bất kỳ bộ từ khóa nào, hệ thống báo lỗi biến `route` chưa được khởi tạo.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi nằm ở hạ tầng log của `graph.py` (không tương thích encoding mặc định của Windows) và thiếu sót trong việc khởi tạo giá trị mặc định cho logic điều hướng (routing logic).

**Cách sửa:**
Tôi đã thay thế toàn bộ ký tự Unicode sang ASCII (`>>>`, `[!]`) để tương thích mọi môi trường, đồng thời bổ sung khối giá trị mặc định (`Defaults`) ở đầu hàm `supervisor_node` để đảm bảo hệ thống luôn có fallback route an toàn.

**Bằng chứng trước/sau:**
> Trước: `UnicodeEncodeError: 'charmap' codec can't encode character '\u25b6'`
> Sau: Pipeline chạy thành công qua 4 kịch bản test khác nhau, lưu được trace JSON mà không gặp lỗi runtime.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Xây dựng khung xương cho toàn bộ graph, xử lý triệt để các lỗi môi trường và thiết lập hệ thống trace (run_id, history) giúp nhóm có thể quan sát (observability) tốt trạng thái của Agent xuyên suốt các node.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Do ưu tiên tính ổn định, bộ keywords hiện tại vẫn còn thủ công và có thể bỏ sót các từ đồng nghĩa nếu người dùng sử dụng văn phong quá khác lạ.

**Nhóm phụ thuộc vào tôi ở đâu?**
File `graph.py` là trung tâm điều phối. Nếu tôi không hoàn thiện logic routing và state management, các thành viên khác sẽ không thể kết nối worker của họ vào luồng chạy chung của nhóm.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần các bạn phụ trách Worker Owner cung cấp implementation thực tế của `retrieval.py` và `policy_tool.py` để thay thế cho các hàm placeholder mà tôi đang dùng để test graph.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ xây dựng một công cụ "Keyword Optimizer" sử dụng LLM để tự động mở rộng bộ từ khóa dựa trên các câu hỏi thực tế trong trace, từ đó giảm thiểu sai sót khi định tuyến (routing) mà vẫn giữ được tốc độ phản hồi tối ưu cho hệ thống.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
