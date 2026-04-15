# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** D1-C401
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.84 | 0.59 | -0.25 | Multi-agent đánh giá khắt khe hơn. |
| Avg latency (ms) | 1250 | 4262 | +3012 | Chậm hơn do nạp mô hình và qua nhiều node. |
| Abstain rate (%) | 0% | 13% | +13% | Biết từ chối khi không có context (ví dụ q01, q09). |
| Multi-hop accuracy | 60% | 85% | +25% | Xử lý tốt nhờ sự phối hợp giữa các worker. |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Dễ dàng biết tại sao ra quyết định. |
| Debug time (estimate) | 20 phút | 5 phút | -15 phút | Trace log giúp khoanh vùng lỗi cực nhanh. |
| MCP Tool Interaction | 0 | 7 / 15 | +46% | Có khả năng truy vấn hệ thống bên ngoài. |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao | Rất Cao |
| Latency | Rất nhanh | Bình thường |
| Observation | Dễ dàng trả lời từ 1 file | Đôi khi routing tốn thêm thời gian không cần thiết. |

**Kết luận:** Multi-agent không cải thiện nhiều về độ chính xác cho câu hỏi dễ nhưng giúp hệ thống "chuyên nghiệp" hơn trong cách trình bày.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Trung bình | Cao |
| Routing visible? | ✗ | ✓ |
| Observation | Dễ bị sót ý giữa các file | Supervisor biết chia nhỏ Task để Workers thu thập đủ ý. |

**Kết luận:** Multi-agent vượt trội trong việc tổng hợp thông tin từ nhiều nguồn tài liệu khác nhau (Cross-domain).

### 2.3 Câu hỏi cần abstain 

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | Thấp | Cao |
| Hallucination cases | Dễ bị "bịa" | Đã giảm đáng kể |
| Observation | Luôn cố gắng trả lời dù thiếu dữ liệu | Biết dùng cờ abstain từ Supervisor. |

**Kết luận:** Multi-agent an toàn hơn, tránh tình trạng Agent trả lời sai kiến thức nghiêm trọng.

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 20 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 5 phút
```

**Câu cụ thể nhóm đã debug:** Lỗi lệch Dimension của Embedding (384 vs 1536). Nhờ Trace log báo lỗi ngay tại Retrieval Worker, nhóm chỉ mất 2 phút để xác định nguyên nhân và sửa lại mô hình.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:** Kiến trúc Multi-Agent theo kiểu "Plug-and-play" giúp việc mở rộng hệ thống sau này cực kỳ dễ dàng.

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 2 LLM calls |
| Complex query | 1 LLM call | 3-4 LLM calls |
| MCP tool call | N/A | 1-2 calls |

**Nhận xét về cost-benefit:** Chi phí LLM cho Day 09 cao hơn gấp 2-3 lần, nhưng đổi lại là sự an toàn, khả năng kiểm soát và tính linh hoạt cao hơn hẳn.

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở điểm nào?**
1. Khả năng sử dụng các công cụ thực tế (Jira, Database) qua MCP.
2. Quy trình kiểm soát an toàn (HITL) và khả năng tự động từ chối khi thiếu dữ liệu.

**Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**
1. Tốc độ phản hồi chậm hơn đáng kể do qua nhiều tầng xử lý.

**Khi nào KHÔNG nên dùng multi-agent?**
Khi bài toán cực kỳ đơn giản, chỉ cần tìm kiếm trên một tập tài liệu nhỏ và yêu cầu tốc độ phản hồi tính bằng mili giây.

**Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
Thêm Memory cho Supervisor để nhớ lịch sử trao đổi của người dùng và tối ưu hóa việc gọi song song (parallel) các Workers để giảm Latency.
