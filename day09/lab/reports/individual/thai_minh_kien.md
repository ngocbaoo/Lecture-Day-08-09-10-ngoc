# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Thái Minh Kiên 
**Vai trò trong nhóm:** Supervisor Owner / Worker Owner / MCP Owner
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong buổi Lab hôm nay, tôi đảm nhận cả hai vai trò chính là **Supervisor Owner** và **Worker Owner**. Tôi chịu trách nhiệm thiết kế kiến trúc toàn bộ hệ thống từ điều phối đến thực thi các tác vụ chuyên biệt.

**Module/file tôi chịu trách nhiệm:**
- `graph.py`: Tôi xây dựng lõi điều phối (Orchestrator) sử dụng mô hình Supervisor-Worker. Tôi định nghĩa `AgentState` để lưu trữ dữ liệu xuyên suốt các node và cài đặt hàm `supervisor_node` để phân loại yêu cầu của người dùng.
- `workers/retrieval.py`: Tôi hiện thực hóa khả năng truy xuất dữ liệu từ ChromaDB (Dense Retrieval) bằng cách sử dụng `SentenceTransformers` (hoặc OpenAI Embeddings).
- `workers/policy_tool.py`: Tôi xây dựng worker phân tích chính sách, sử dụng LLM để nhận diện các trường hợp ngoại lệ (Flash Sale, Digital products) và gọi các MCP tools.
- `workers/synthesis.py`: Tôi cài đặt logic tổng hợp câu trả lời, đảm bảo có trích dẫn nguồn (citation) và tính toán độ tin cậy bằng phương pháp LLM-as-a-Judge.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi là người hiện thực hóa các **Worker Contracts** trong `contracts/worker_contracts.yaml`. Cấu trúc `worker_io_logs` mà tôi thiết kế là nguồn dữ liệu chính để thành viên phụ trách **Trace & Docs** có thể chạy script `eval_trace.py` để tính toán các chỉ số Performance và Latency của toàn bộ Pipeline.

**Bằng chứng:**
Tôi đã hoàn thành tất cả các TODO trong `graph.py`, `retrieval.py`, `policy_tool.py` và `synthesis.py`. Các file này đều có logic thực tế thay vì placeholder.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn triển khai cơ chế **LLM-as-a-Judge** ngay bên trong `synthesis_worker` để tính toán chỉ số `confidence` thay vì chỉ dùng điểm số trung bình (distance score) của ChromaDB.

**Lý do:** 
Trong các hệ thống RAG thông thường, điểm tin cậy thường chỉ dựa vào độ tương đồng vector. Tuy nhiên, trong môi trường Multi-Agent, một Worker có thể retrieve đúng tài liệu nhưng LLM lại tổng hợp sai hoặc bỏ sót các lỗi chính sách (ngoại lệ). 
Việc gọi thêm một "Judge" (sử dụng model `gpt-4o-mini` với prompt chuyên biệt) để đối chiếu trực tiếp câu trả lời với context và policy giúp phát hiện hiện tượng Hallucination ngay tại bước cuối cùng. Điều này cực kỳ quan trọng đối với các câu hỏi về tài chính (hoàn tiền) hoặc quyền hạn (P1 escalation).

**Trade-off đã chấp nhận:** 
Quyết định này làm tăng **Latency** của pipeline (thêm khoảng 500ms - 1s cho tool call LLM thứ hai) và tăng chi phí token. Tuy nhiên, độ an toàn của câu trả lời được ưu tiên hơn tốc độ trong kịch bản Helpdesk nội bộ.

**Bằng chứng từ trace/code:**
Trong `workers/synthesis.py`, tôi đã cài đặt hàm `_estimate_confidence`:
```python
prompt = f"""
Bạn là một giám khảo AI (LLM-as-a-Judge) công bằng.
Nhiệm vụ: Đánh giá độ tin cậy (confidence score) của câu trả lời dựa trên tài liệu tham khảo và chính sách...
Trả về kết quả dưới định dạng JSON duy nhất: {{"confidence": <float>}}
"""
```
Kết quả trace ghi nhận độ tin cậy thực tế (ví dụ: 0.95 cho câu trả lời chuẩn xác và 0.1 cho trường hợp không có context).

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Ngắt quãng luồng dữ liệu khi Supervisor chuyển hướng trực tiếp sang `policy_tool_worker`.

**Symptom:** 
Khi người dùng hỏi "Đơn hàng Flash Sale có được hoàn tiền không?", Supervisor nhận diện keyword "Flash Sale" và route thẳng đến `policy_tool_worker`. Tuy nhiên, Worker này ban đầu crash hoặc trả về kết quả rỗng vì nó chưa có `retrieved_chunks` (dữ liệu thô từ tài liệu) để phân tích, do nó "nhảy cóc" qua bước Retrieval.

**Root cause:** 
Lỗi nằm ở logic điều phối trong `graph.py`. Tôi giả định rằng Retrieval luôn chạy trước, nhưng với cấu trúc Graph linh hoạt, Supervisor có thể chọn bất kỳ node nào là điểm bắt đầu tùy vào mapping logic.

**Cách sửa:**
Tôi đã cập nhật hàm `run` trong `build_graph()` để thêm một cơ chế kiểm tra điều kiện (Guardrail): Nếu một Worker cần context (như Agent Chính sách) mà chưa thấy dữ liệu trong `AgentState`, hệ thống sẽ tự động gọi `retrieval_worker_node` trước khi thực thi Worker đó.

**Bằng chứng trước/sau:**
- **Trước:** Trace báo lỗi `KeyError: 'retrieved_chunks'` hoặc `policy_applies=True` (sai vì không có bằng chứng để chặn).
- **Sau (ở graph.py):**
```python
elif route == "policy_tool_worker":
    state = policy_tool_worker_node(state)
    # Nếu policy worker chưa có chunks, buộc phải retrieve bổ sung
    if not state["retrieved_chunks"]:
        state = retrieval_worker_node(state)
```
Sau khi sửa, trace cho thấy `workers_called` bao gồm cả `retrieval_worker` dù Supervisor ban đầu route sang Policy.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được một hệ thống Worker vô cùng **stateless** và tuân thủ chặt chẽ **Worker Contract**. Việc tách biệt logic Code và logic Data (qua YAML contract) giúp việc debug từng phần trở nên cực kỳ dễ dàng. Tôi cũng tự hào về phần prompt Engineering cho `policy_tool_worker` vì nó xử lý rất tốt các tình huống lắt léo về thời gian (Temporal scoping - ví dụ chính sách v3 vs v4).

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Phần routing logic trong `supervisor_node` hiện tại vẫn chủ yếu dựa trên **keyword-matching**. Nếu người dùng đặt câu hỏi quá lắt léo hoặc dùng từ đồng nghĩa không có trong list, Supervisor có thể route sai. Đáng lẽ tôi nên dùng một lớp LLM Classifier mỏng để routing thông minh hơn.

**Nhóm phụ thuộc vào tôi ở đâu?** 
Toàn bộ hệ thống sẽ bị block nếu tôi không hoàn thành `AgentState` và các Node wrapper, vì đây là khung xương để các thành viên khác tích hợp Trace và MCP Tools.

**Phần tôi phụ thuộc vào thành viên khác:** 
Tôi cần bộ dữ liệu Document đã được Index hoàn chỉnh từ thành viên **Documentation Owner** để kiểm tra tính chính xác của Retrieval.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tập trung hiện thực hóa **Human-in-the-loop (HITL)** thực thụ. Hiện tại, `human_review_node` mới chỉ là một placeholder tự động approve. Nếu có thêm thời gian, tôi sẽ tích hợp tính năng dừng Graph (breakpoint) khi `risk_high=True` hoặc `confidence < 0.4`, cho phép chuyên viên IT can thiệp vào câu trả lời trước khi gửi tới người dùng. Điều này sẽ giúp giảm thiểu tối đa rủi ro trong các tình huống "khẩn cấp" (emergency) mà trace của các câu hỏi P1 hiện đang cho thấy độ rủi ro cao.

---
*Lưu file này với tên: `reports/individual/thai_minh_kien.md`*
