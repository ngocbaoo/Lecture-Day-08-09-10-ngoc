# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Tạ Bảo Ngọc
**Vai trò trong nhóm:** MCP Owner
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
- File chính: `mcp_server.py` và `workers/policy_tool.py`
- Functions tôi implement: `dispatch_tool`, `analyze_policy`

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi đóng vai trò là người cung cấp "công cụ" cho hệ thống. Khi Supervisor điều hướng các câu hỏi về chính sách hoặc quyền hạn (ví dụ: cấp quyền Level 3), Worker của tôi sẽ nhận nhiệm vụ. Tôi kết nối với các thành viên khác bằng cách sử dụng kết quả từ Retrieval Worker để làm dữ liệu đầu vào cho việc phân tích chính sách và cung cấp kết quả MCP cho Synthesis Worker tổng hợp câu trả lời. Nếu không có phần của tôi, Agent sẽ không thể trả lời các câu hỏi cần dữ liệu thực tế như Ticket Info hay Access Log.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Tôi đã hoàn thiện logic trong `mcp_server.py` và hàm `_call_mcp_tool` trong `policy_tool.py`. Commit hash: `5a307e7` (Update: Code sprint 2).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Tôi quyết định sử dụng mô hình **In-Process Mock MCP Server** thay vì xây dựng một Server HTTP độc lập bằng thư viện MCP chính thức.

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**
Việc sử dụng In-process Mock giúp toàn bộ pipeline chạy đồng bộ và nhanh hơn trong môi trường Lab. Các lựa chọn thay thế là dựng một server FastAPI hoặc dùng `mcp-sdk` chạy tiến trình riêng. Tôi chọn cách Mock vì nó giúp nhóm dễ dàng debug lỗi "Dimension mismatch" và các lỗi đường dẫn Database ngay trong một lần chạy lệnh `python graph.py`, thay vì phải quản lý nhiều terminal cùng lúc.

**Trade-off đã chấp nhận:**
Hệ thống sẽ bị phụ thuộc chặt chẽ (tightly coupled) vào code Python. Nếu muốn tích hợp một Agent viết bằng ngôn ngữ khác, chúng tôi sẽ phải viết lại phần giao tiếp MCP thành chuẩn HTTP/JSON-RPC.

**Bằng chứng từ trace/code:**
```python
def dispatch_tool(name: str, args: dict) -> dict:
    if name == "get_ticket_info":
        return tool_get_ticket_info(**args)
    elif name == "check_access_permission":
        return tool_check_access_permission(**args)
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** **Unicode / Emoji Loading Error trên Windows Terminal.**

**Symptom (pipeline làm gì sai?):**
Khi in các kết quả gọi Tool MCP ra terminal, hệ thống thỉnh thoảng báo lỗi `UnicodeEncodeError` hoặc hiển thị các ký tự lạ như `ðŸ”`. Điều này khiến các file log JSON bị lỗi định dạng khi lưu trữ.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi nằm ở phần log và print của `mcp_server.py`. Terminal mặc định của Windows (CP1252) không hỗ trợ tốt các emoji (như 🎯, 📋) mà mã nguồn ban đầu sử dụng để trang trí log.

**Cách sửa:**
Tôi đã loại bỏ toàn bộ các emoji phức tạp trong file `mcp_server.py` và thay thế bằng các ký tự văn bản đơn giản. Đồng thời, tôi bổ sung tham số `encoding="utf-8"` khi mở và ghi các file log trong `eval_trace.py` để đảm bảo tính nhất quán trên nền tảng Windows.

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.
Trước: `[retrieval] Loading model... ðŸŽ¯` -> Lỗi crash terminal.
Sau: `[retrieval] Loading SentenceTransformer model into memory...` -> Chạy mượt mà, lưu được trace JSON chuẩn.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

> Trả lời trung thực — không phải để khen ngợi bản thân.

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được lớp `dispatch_tool` giúp các Worker khác gọi công cụ một cách dễ dàng mà không cần quan tâm đến logic phức tạp bên dưới. Việc tích hợp thành công cả 3 công cụ MCP giúp điểm đánh giá của nhóm về khả năng sử dụng công cụ đạt tối đa.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi chưa xử lý tốt các trường hợp MCP Tool trả về lỗi (Error handling). Nếu Jira API giả lập bị lỗi, Worker của tôi có thể làm sập toàn bộ luồng xử lý của Agent.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_
Nếu tôi chưa hoàn thành phần `check_access_permission`, Nhóm sẽ bị block hoàn toàn ở các câu hỏi liên quan đến cấp quyền Level 3 — một phần quan trọng để đạt điểm Sprint 3.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_
Tôi phụ thuộc vào Retrieval Owner để lấy context tài liệu chính xác, từ đó mới có dữ liệu để thực hiện hàm `analyze_policy`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ thực hiện **Parallel Tool Calling** (gọi tool song song). Lý do: Trace của các câu hỏi phức tạp (như gq09) cho thấy hệ thống phải gọi tuần tự 3 tool (Jira, Access, KB) khiến latency tăng lên trên 15 giây. Nếu gọi song song, chúng ta có thể giảm latency xuống chỉ còn khoảng 5 giây.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
