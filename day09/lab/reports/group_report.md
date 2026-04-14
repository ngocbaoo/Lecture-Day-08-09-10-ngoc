# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** D1-C401
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Lê Minh Hoàng | Supervisor Owner | phamhaihau1976@gmail.com |
| Thái Minh Kiên | Worker Owner | minhkien242003@gmail.com |
| Tạ Bảo Ngọc | MCP Owner | ngoctabao@gmail.com |
| Nguyễn Xuân Hải | Trace & Docs Owner | haicr7@gmail.com |

**Ngày nộp:** 14/04/2026
**Repo:** https://github.com/ngocbaoo/Lecture-Day-08-09-10/tree/main/day09/lab
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**
Nhóm triển khai hệ thống Multi-Agent theo mô hình **Supervisor-Worker**. Hệ thống bao gồm 3 Worker chuyên trách: `retrieval_worker` để truy xuất tri thức, `policy_tool_worker` để phân tích chính sách và gọi Tool, `synthesis_worker` để tổng hợp câu trả lời. Supervisor đóng vai trò điều phối luồng State thông qua `graph.py`, đảm bảo tính minh bạch và có thể trace log cho từng bước xử lý.

**Routing logic cốt lõi:**
> Mô tả logic supervisor dùng để quyết định route (keyword matching, LLM classifier, rule-based, v.v.)

Supervisor sử dụng cơ chế **Hybrid Routing** (Kết hợp từ khóa và phân tích rủi ro). Hệ thống quét tìm các từ khóa đặc thù như "hoàn tiền", "cấp quyền" để đẩy sang Policy Worker. Đồng thời, Supervisor cũng nhận diện các ca rủi ro cao hoặc mã lỗi chưa xác định (ERR-XXX) để kích hoạt Human-in-the-loop (HITL), đảm bảo an toàn trước khi hành động.

**MCP tools đã tích hợp:**
> Liệt kê tools đã implement và 1 ví dụ trace có gọi MCP tool.

- `search_kb`: Công cụ tìm kiếm tri thức nội bộ từ file PDF/Markdown.
- `get_ticket_info`: Truy vấn thông tin ticket từ hệ thống Jira giả lập.
- `check_access_permission`: Kiểm tra quyền hạn và trả về danh sách người phê duyệt cần thiết.
Ví dụ: Trong trace câu hỏi về cấp quyền Level 3, hệ thống đã gọi tool `check_access_permission` và trả về kết quả `can_grant: true` cùng danh sách 3 người phê duyệt (Line Manager, IT Admin, Security).

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Sử dụng SentenceTransformer cục bộ thay vì OpenAI Embeddings kết hợp với cơ chế **Singleton Model Cache**.

**Bối cảnh vấn đề:**
Trong Sprint 2, nhóm gặp lỗi **"Dimension mismatch"** do Database cũ từ Day 08 dùng 384 chiều trong khi mặc định mới là 1536 chiều. Ngoài ra, việc nạp mô hình Embedding mỗi khi chạy query mất tới 10-15 giây, gây ra trải nghiệm người dùng cực kỳ chậm chạp.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Dùng OpenAI API | Nhanh, không cần code nạp mô hình | Tốn phí, không khớp với DB 384 chiều đã có |
| **Model Caching (Local)** | **Khớp 384 chiều, miễn phí, cực nhanh sau lần nạp đầu** | Tốn RAM để giữ mô hình trong bộ nhớ |

**Phương án đã chọn và lý do:**
Nhóm chọn **Model Caching**. Lý do là để đảm bảo tương thích 100% với dữ liệu vector đã xây dựng từ Day 08 mà không phải index lại toàn bộ. Đồng thời, cơ chế Singleton giúp tiết kiệm thời gian nạp mô hình, giảm latency từ 30s xuống còn ~5s cho các lượt truy vấn tiếp theo.

**Bằng chứng từ trace/code:**
> Dẫn chứng cụ thể (VD: route_reason trong trace, đoạn code, v.v.)

```python
_MODEL_CACHE = None
def _get_embedding_fn():
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = SentenceTransformer("all-MiniLM-L6-v2")
    return lambda text: _MODEL_CACHE.encode([text])[0].tolist()
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 88 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: `gq10` — Lý do tốt: Hệ thống nhận diện chính xác ngoại lệ Flash Sale không được hoàn tiền dựa trên logic của Policy Worker, không bị "ảo tưởng" (hallucination) như các mô hình RAG thuần túy.

**Câu pipeline fail hoặc partial:**
- ID: `gq01` — Fail ở đâu: Retrieval tìm thấy file SLA nhưng Synthesis chưa trích xuất được con số deadline chính xác cho khung giờ 22:47.
  Root cause: Do chunking size của tài liệu SLA từ Day 08 hơi nhỏ khiến mất ngữ cảnh về bảng escalate thời gian.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Agent đã xử lý đúng chuẩn bằng cách trả về "Không đủ thông tin trong tài liệu nội bộ" vì chính sách không quy định mức phạt tài chính cụ thể, tránh được lỗi trả lời sai kiến thức.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Có. Trace ghi nhận sự phối hợp giữa `policy_tool_worker` (kiểm tra quyền) và `retrieval_worker` (tra cứu bước notification). Kết quả trả về đầy đủ cả 2 yêu cầu của câu hỏi.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**
Thời gian phản hồi (Latency) tăng từ ~1.2s lên ~4s nhưng tính **minh bạch (Traceability)** tăng từ 0% lên 100%. Nhóm biết chính xác Supervisor đã nghĩ gì qua `route_reason` (ví dụ: "task contains policy/access keywords").

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Sự mạnh mẽ của **Human-in-the-loop (HITL)**. Khi chạy thử ca cấp cứu lúc 2am, việc hệ thống tự động dừng lại chờ Approve thay vì tự ý trả lời thông tin kỹ thuật sai lệch mang lại sự an tâm rất lớn về mặt an toàn hệ thống.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Đối với các câu hỏi tra cứu kiến thức tĩnh đơn giản, việc phải đi qua Supervisor Node làm chậm tốc độ phản hồi gấp 3 lần mà không mang lại giá trị gia tăng về độ chính xác.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Lê Minh Hoàng | Graph Orchestration & Supervisor Logic | 1  |
| Thái Minh Kiên | Worker Implementation & Optimization | 2 |
| Tạ Bảo Ngọc | MCP Server & Tool Integration | 3 |
| Nguyễn Xuân Hải | Evaluation, Trace & Documentation | 4 |

**Điều nhóm làm tốt:**
Phối hợp đồng bộ thông qua Git, giải quyết tốt các xung đột file khi merge code từ các nhánh khác nhau. Nhóm thống nhất được contract `AgentState` từ rất sớm nên việc ghép code diễn ra thuận lợi.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Việc quản lý đường dẫn file (Path handling) ban đầu bị lỗi do mỗi thành viên đứng ở thư mục khác nhau để chạy script.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Sẽ quy định chặt chẽ việc dùng đường dẫn tuyệt đối (Absolute Paths) ngay từ đầu Sprint 1 để tránh lỗi `FileNotFoundError`.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

> 1–2 cải tiến cụ thể với lý do có bằng chứng từ trace/scorecard.

Nhóm sẽ triển khai cơ chế **Parallel Worker Execution**. Dựa trên trace của các câu hỏi phức tạp (như gq09), hiện tại hệ thống gọi các worker tuần tự khiến tốn nhiều thời gian. Nếu gọi song song Retrieval và Policy Tool, chúng ta có thể giảm latency xuống ít nhất 40%.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
