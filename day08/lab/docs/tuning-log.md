# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

<<<<<<< HEAD
**Ngày:** 13/04/2026
**Config:**
```
retrieval_mode = "dense"
chunk_size = 300 tokens
overlap = 50 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
=======
**Ngày:** ___________  
**Config:**
```
retrieval_mode = "dense"
chunk_size = _____ tokens
overlap = _____ tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = _____
>>>>>>> upstream/main
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
<<<<<<< HEAD
| Faithfulness | 3.82 /5 |
| Answer Relevance | 3.91 /5 |
| Context Recall | 5 /5 |
| Completeness | 3.00 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> q09 (ERR-403-AUTH)
- Recall: None
- Reason: query dạng error code → dense retrieval chưa tối ưu keyword matching
> q10 (VIP refund case)
- Mọi thứ trừ Recall: 1/5
- Reason: thiếu điều kiện ngoại lệ VIP trong policy context
=======
| Faithfulness | ? /5 |
| Answer Relevance | ? /5 |
| Context Recall | ? /5 |
| Completeness | ? /5 |

**Câu hỏi yếu nhất (điểm thấp):**
> TODO: Liệt kê 2-3 câu hỏi có điểm thấp nhất và lý do tại sao.
> Ví dụ: "q07 (Approval Matrix) - context recall = 1/5 vì dense bỏ lỡ alias."
>>>>>>> upstream/main

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
<<<<<<< HEAD
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias
- [x] Retrieval: Top-k quá ít → thiếu evidence
=======
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [ ] Retrieval: Top-k quá ít → thiếu evidence
>>>>>>> upstream/main
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

<<<<<<< HEAD
**Ngày:** 13/04/2026  
**Biến thay đổi:** retrieval_mode = "hybrid", top_k_select = 5
**Lý do chọn biến này:**
> Baseline quá ít top_k_select(3) nên thiếu evidence.
> Đổi sang retrieval_mode = "hybrid" để lấy được đúng điều khoản và nội dung bằng cách kết hợp keyword và semantic.


**Config thay đổi:**
```
retrieval_mode = "hybrid"
top_k_select = 5
Các tham số còn lại giữ nguyên như baseline
=======
**Ngày:** ___________  
**Biến thay đổi:** ___________  
**Lý do chọn biến này:**
> TODO: Giải thích theo evidence từ baseline results.
> Ví dụ: "Chọn hybrid vì q07 (alias query) và q09 (mã lỗi ERR-403) đều thất bại với dense.
> Corpus có cả ngôn ngữ tự nhiên (policy) lẫn tên riêng/mã lỗi (ticket code, SLA label)."

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # hoặc biến khác
# Các tham số còn lại giữ nguyên như baseline
>>>>>>> upstream/main
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
<<<<<<< HEAD
| Faithfulness | 3.82/5 | 3.64/5 | - |
| Answer Relevance | 3.91/5 | 3.55/5 | - |
| Context Recall | 5/5 | 5.0/5 | +/- |
| Completeness | 3.00/5 | 3.45/5 | + |

**Nhận xét:**
> TODO: Variant 1 cải thiện ở câu nào? Tại sao?
- Cải thiện completeness của q01 và q08
- q10 faithfulness
- Lí do: Nâng top k select lên 5 thì nhận được nhiều context hơn từ nhiều phần khác nhau từ tài liệu 
> Có câu nào kém hơn không? Tại sao?
- Câu 7 kém hơn
- Lí do: Dù hệ thống báo context_recall là 1/1 (đã tìm thấy tài liệu đúng), nhưng với top_k_select=5, lượng thông tin đổ vào prompt có thể chứa nhiều đoạn văn từ các tài liệu khác gây nhiễu. Có vẻ như GPT-4o-mini khi thấy 5 đoạn văn mà thông tin về "tên cũ" quá nhỏ lẻ, nó sẽ ưu tiên sự an toàn và trả lời "Không biết" thay vì diễn giải như Baseline.

**Kết luận:**
> TODO: Variant 1 có tốt hơn baseline không?
- Kém hơn nhưng Completeness được cải thiện.
> Bằng chứng là gì? (điểm số, câu hỏi cụ thể)
- Điểm số tổng.Cụ thể là câu 10 và câu 8 Completeness được cải thiện.
=======
| Faithfulness | ?/5 | ?/5 | +/- |
| Answer Relevance | ?/5 | ?/5 | +/- |
| Context Recall | ?/5 | ?/5 | +/- |
| Completeness | ?/5 | ?/5 | +/- |

**Nhận xét:**
> TODO: Variant 1 cải thiện ở câu nào? Tại sao?
> Có câu nào kém hơn không? Tại sao?

**Kết luận:**
> TODO: Variant 1 có tốt hơn baseline không?
> Bằng chứng là gì? (điểm số, câu hỏi cụ thể)

>>>>>>> upstream/main
---

## Variant 2 (nếu có thời gian)

<<<<<<< HEAD
**Biến thay đổi:** use_rerank = True
=======
**Biến thay đổi:** ___________  
>>>>>>> upstream/main
**Config:**
```
# TODO
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
<<<<<<< HEAD
| Faithfulness | 3.82/5 | 3.64/5 | 3.90/5 | variance2 |
| Answer Relevance | 3.91/5 | 3.55/5 | 3.90/5 | variance2 |
| Context Recall | 5/5 | 5/5 | 5/5 | variance2 |
| Completeness | 3.00/5 | 3.45/5 | 3.6/5 | variance2 |
=======
| Faithfulness | ? | ? | ? | ? |
| Answer Relevance | ? | ? | ? | ? |
| Context Recall | ? | ? | ? | ? |
| Completeness | ? | ? | ? | ? |
>>>>>>> upstream/main

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
<<<<<<< HEAD
   > Lỗi "Nhiễu thông tin khi tăng ngữ cảnh" (Noise-to-Signal Ratio). Chi tiết: Qua Variant 1, chúng ta thấy khi tăng top_k_select từ 3 lên 5 để cải thiện độ đầy đủ (Completeness), hệ thống lại gặp hiện tượng giảm điểm Faithfulness và Answer Relevance (như ở câu q07). Điều này cho thấy LLM dễ bị phân tâm hoặc ưu tiên sự "an toàn" (trả lời không biết) khi có quá nhiều đoạn văn bản không liên quan trực tiếp được nạp vào prompt.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Biến used_rerank có tác động lớn tới chất lượng

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Thử kết hợp used_rerank với các tham số khác, hoặc thay đổi chunking strategy.
   > Thử nghiệm query transformation để giải quyết triệt để câu q07.
=======
   > _____________

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > _____________

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > _____________
>>>>>>> upstream/main
