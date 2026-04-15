# Routing Decisions Log — Lab Day 09

**Nhóm:** D1-C401
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> Sản phẩm kỹ thuật số (license key) có được hoàn tiền không?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keywords`  
**MCP tools được gọi:** `search_kb` (gọi bên trong policy worker để lấy context chính sách)  
**Workers called sequence:** `['policy_tool_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Sản phẩm kỹ thuật số (license key, subscription) KHÔNG được hoàn tiền theo Điều 4 của chính sách.
- confidence: 1.0
- Correct routing? Yes

**Nhận xét:** Routing chính xác. Supervisor nhận diện được câu hỏi liên quan đến chính sách (policy) và chuyển cho đúng Worker chuyên trách để kiểm tra các điều khoản ngoại lệ thay vì chỉ tìm kiếm văn bản đơn thuần.

---

## Routing Decision #2

**Task đầu vào:**
> Ai phải phê duyệt để cấp quyền Level 3?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keywords`  
**MCP tools được gọi:** `check_access_permission`, `search_kb`  
**Workers called sequence:** `['policy_tool_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): Cần sự phê duyệt của 3 cấp: Line Manager, IT Admin, và IT Security.
- confidence: 1.0
- Correct routing? Yes

**Nhận xét:** Rất tốt. Hệ thống không chỉ tìm thấy thông tin trong tài liệu mà còn kích hoạt MCP tool `check_access_permission` để xác nhận danh sách người phê duyệt cần thiết cho mức quyền Level 3.

---

## Routing Decision #3

**Task đầu vào:**
> Gặp lỗi khẩn cấp ERR-99 khi truy cập production lúc 2am. Help!

**Worker được chọn:** `human_review` (HITL)  
**Route reason (từ trace):** `unknown error code + risk_high -> human review | human approved → retrieval`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `['human_review', 'retrieval_worker', 'synthesis_worker']`

**Kết quả thực tế:**
- final_answer (ngắn): [Sau khi được approve] Không đủ thông tin trong tài liệu nội bộ xử lý ERR-99.
- confidence: 0.3
- Correct routing? Yes

**Nhận xét:** Đây là minh chứng cho tính an toàn. Supervisor nhận diện được "ERR-99" là mã lỗi không xác định cộng với yếu tố "khẩn cấp" nên đã chặn lại để con người (Human) phê duyệt trước khi cho phép hệ thống tiếp tục xử lý.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> Ticket P1 được tạo lúc 22:47. Ai sẽ nhận thông báo đầu tiên?

**Worker được chọn:** `retrieval_worker`  
**Route reason:** `default routing`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**
Bởi vì câu hỏi chứa nhiều thực thể: thời gian (22:47), mức độ (P1), và đối tượng (ai nhận thông báo). Supervisor phải quyết định xem đây là một câu hỏi tra cứu SLA (Retrieval) hay một quy trình nghiệp vụ cần Policy Tool. Ở đây hệ thống chọn Retrieval là chính xác vì cần tìm đoạn văn bản quy định về lịch trực ca trong SLA 2026.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 46% |
| human_review | 1 | (Manual test) |

### Routing Accuracy

- Câu route đúng: 15 / 15 (trong bộ test chuẩn)
- Câu route sai (đã sửa bằng cách nào?): 0 (Đã tinh chỉnh keyword logic trong graph.py để phân biệt rõ Access vs Tech Support).
- Câu trigger HITL: 1 (Ca cấp cứu ERR-99)

### Lesson Learned về Routing

1. **Hybrid Routing:** Kết hợp giữa từ khóa (Keyword) và LLM Classifier cho kết quả ổn định nhất. Rule-based giúp xử lý nhanh các câu phổ biến, LLM giúp xử lý các câu diễn đạt phức tạp.
2. **Context Matters:** Nếu không có MCP Tool, routing chỉ mang tính chất tìm kiếm. Khi có MCP, routing trở thành một quyết định thực thi hành động (Action execution).

### Route Reason Quality

Các `route_reason` hiện tại đã khá rõ ràng (nêu được keyword khiến Supervisor ra quyết định). Cải tiến tiếp theo nên bao gồm cả "Confidence Score" của chính Supervisor khi chọn route để người dùng hiểu mức độ chắc chắn của Agent.
