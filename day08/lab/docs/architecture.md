# Architecture — RAG Pipeline (Day 08 Lab)

<<<<<<< HEAD
=======
> Template: Điền vào các mục này khi hoàn thành từng sprint.
> Deliverable của Documentation Owner.

>>>>>>> upstream/main
## 1. Tổng quan kiến trúc

```
[Raw Docs]
    ↓
[index.py: Preprocess → Chunk → Embed → Store]
    ↓
[ChromaDB Vector Store]
    ↓
[rag_answer.py: Query → Retrieve → Rerank → Generate]
    ↓
[Grounded Answer + Citation]
```

**Mô tả ngắn gọn:**
<<<<<<< HEAD
Hệ thống RAG (Retrieval-Augmented Generation) hỗ trợ giải đáp thắc mắc về các chính sách nội bộ và quy trình kỹ thuật cho nhân viên. Hệ thống giúp tra cứu nhanh thông tin từ các tài liệu PDF/Markdown về HR, IT, SLA và Refund, đảm bảo câu trả lời luôn có dẫn chứng (citation) và giảm thiểu tình trạng ảo giác của AI.
=======
> TODO: Mô tả hệ thống trong 2-3 câu. Nhóm xây gì? Cho ai dùng? Giải quyết vấn đề gì?
>>>>>>> upstream/main

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
<<<<<<< HEAD
| `policy_refund_v4.txt` | policy/refund-v4.pdf | Customer Service | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT Support | 7 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 6 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT Support | 6 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 10 |
=======
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | TODO |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | TODO |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | TODO |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | TODO |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | TODO |
>>>>>>> upstream/main

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
<<<<<<< HEAD
| Chunk size | 300 tokens (1200 chars) | Cân bằng giữa việc giữ đủ ngữ cảnh và tối ưu độ tập trung cho LLM. |
| Overlap | 50 tokens (200 chars) | Đảm bảo không mất thông tin tại các điểm cắt giữa các chunk. |
| Chunking strategy | Section + Paragraph based | Ưu tiên cắt theo heading (===) để giữ toàn vẹn điều khoản, sau đó mới chia nhỏ theo paragraph. |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, kiểm tra độ tươi mới của thông tin và trích dẫn nguồn. |

### Embedding model
- **Model**: Local (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Vector store**: ChromaDB (PersistentClient)
- **Similarity metric**: Cosine Similarity
=======
| Chunk size | TODO tokens | TODO |
| Overlap | TODO tokens | TODO |
| Chunking strategy | Heading-based / paragraph-based | TODO |
| Metadata fields | source, section, effective_date, department, access | Phục vụ filter, freshness, citation |

### Embedding model
- **Model**: TODO (OpenAI text-embedding-3-small / paraphrase-multilingual-MiniLM-L12-v2)
- **Vector store**: ChromaDB (PersistentClient)
- **Similarity metric**: Cosine
>>>>>>> upstream/main

---

## 3. Retrieval Pipeline (Sprint 2 + 3)

### Baseline (Sprint 2)
| Tham số | Giá trị |
|---------|---------|
<<<<<<< HEAD
| Strategy | Dense (Embedding similarity) |
=======
| Strategy | Dense (embedding similarity) |
>>>>>>> upstream/main
| Top-k search | 10 |
| Top-k select | 3 |
| Rerank | Không |

### Variant (Sprint 3)
| Tham số | Giá trị | Thay đổi so với baseline |
|---------|---------|------------------------|
<<<<<<< HEAD
| Strategy | Hybrid (Dense + Sparse/BM25) | Kết hợp nghĩa ngữ nghĩa và từ khóa chính xác. |
| Top-k search | 10 | Giữ nguyên độ rộng tìm kiếm. |
| Top-k select | 5 | Tăng số chunk đưa vào prompt để tăng độ đầy đủ (Completeness). |
| Rerank | True | Lọc bỏ các chunk nhiễu khi tăng k_select lên 5. |

**Lý do chọn variant này:**
Sử dụng Hybrid để bắt được các từ khóa chuyên ngành (như mã lỗi ERR-403) mà tìm kiếm semantic đôi khi bỏ lỡ. Kết hợp với Rerank giúp hệ thống có thể tăng số lượng chunk cung cấp cho LLM (k=5) để câu trả lời đầy đủ hơn mà không lo bị nhiễu thông tin, từ đó cải thiện cả điểm Faithfulness và Completeness.
=======
| Strategy | TODO (hybrid / dense) | TODO |
| Top-k search | TODO | TODO |
| Top-k select | TODO | TODO |
| Rerank | TODO (cross-encoder / MMR) | TODO |
| Query transform | TODO (expansion / HyDE / decomposition) | TODO |

**Lý do chọn variant này:**
> TODO: Giải thích tại sao chọn biến này để tune.
> Ví dụ: "Chọn hybrid vì corpus có cả câu tự nhiên (policy) lẫn mã lỗi và tên chuyên ngành (SLA ticket P1, ERR-403)."
>>>>>>> upstream/main

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
<<<<<<< HEAD
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.
=======
If the context is insufficient, say you do not know.
Cite the source field when possible.
Keep your answer short, clear, and factual.
>>>>>>> upstream/main

Question: {query}

Context:
<<<<<<< HEAD
{context_block}
=======
[1] {source} | {section} | score={score}
{chunk_text}

[2] ...
>>>>>>> upstream/main

Answer:
```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
<<<<<<< HEAD
| Model | OpenAI `gpt-4o-mini` |
| Temperature | 0 (đảm bảo tính nhất quán cho evaluation) |
| Max tokens | 1024 |
=======
| Model | TODO (gpt-4o-mini / gemini-1.5-flash) |
| Temperature | 0 (để output ổn định cho eval) |
| Max tokens | 512 |
>>>>>>> upstream/main

---

## 5. Failure Mode Checklist

<<<<<<< HEAD
| Failure Mode | Triệu chứng | Cách kiểm tra | Ví dụ thực tế |
|-------------|-------------|---------------|---------------|
| **Missing Detail (Low Completeness)** | Câu trả lời đúng nhưng thiếu ý phụ quan trọng. | `score_completeness()` thấp (Ví dụ: 2/5). | Câu **q01**: Baseline chỉ lấy được Resolution time nhưng thiếu Response time do `k_select` quá nhỏ. |
| **Noise Overload (Hallucination/Abstain)** | AI trả lời "Tôi không biết" dù dữ liệu có trong context. | Điểm `Relevance` tụt khi tăng `k`. | Câu **q07**: Khi tăng `k=5` mà không Rerank, AI bị nhiễu và không bắt được thông tin về việc đổi tên tài liệu. |
| **Alias Mismatch** | Retrieval không tìm thấy tài liệu chứa từ khóa viết tắt/tên cũ. | `Context Recall` thấp hoặc 0. | Truy vấn "Approval Matrix" không tìm thấy "Access Control SOP" nếu chỉ dùng Dense Retrieval. |
| **Chunk Fragmentation** | Thông tin bị cắt đôi giữa 2 chunk khiến AI mất liên kết. | Đọc `list_chunks()` kiểm tra đoạn cắt. | Các bảng biểu hoặc danh sách gạch đầu dòng dài bị chia nhỏ quá mức. |
| **Token Overload** | Câu trả lời bị cắt ngang hoặc AI bị "lú" (Lost in the middle). | Kiểm tra `max_tokens` và độ dài context. | Khi nhồi nhét 10+ chunk vào prompt mà không có chiến thuật rerank/priority. |

---

## 6. Diagram

```mermaid
graph LR
    A[User Query] --> B[Dense + Sparse Search]
    B --> C[Hybrid Fusion (RRF)]
    C --> D[Top-10 Candidates]
    D --> E[Cross-Encoder Rerank]
    E --> F[Top-5 Selection]
    F --> G[Build Context Block]
    G --> H[Grounded Prompt]
    H --> I[LLM: gpt-4o-mini]
    I --> J[Answer]
=======
> Dùng khi debug — kiểm tra lần lượt: index → retrieval → generation

| Failure Mode | Triệu chứng | Cách kiểm tra |
|-------------|-------------|---------------|
| Index lỗi | Retrieve về docs cũ / sai version | `inspect_metadata_coverage()` trong index.py |
| Chunking tệ | Chunk cắt giữa điều khoản | `list_chunks()` và đọc text preview |
| Retrieval lỗi | Không tìm được expected source | `score_context_recall()` trong eval.py |
| Generation lỗi | Answer không grounded / bịa | `score_faithfulness()` trong eval.py |
| Token overload | Context quá dài → lost in the middle | Kiểm tra độ dài context_block |

---

## 6. Diagram (tùy chọn)

> TODO: Vẽ sơ đồ pipeline nếu có thời gian. Có thể dùng Mermaid hoặc drawio.

```mermaid
graph LR
    A[User Query] --> B[Query Embedding]
    B --> C[ChromaDB Vector Search]
    C --> D[Top-10 Candidates]
    D --> E{Rerank?}
    E -->|Yes| F[Cross-Encoder]
    E -->|No| G[Top-3 Select]
    F --> G
    G --> H[Build Context Block]
    H --> I[Grounded Prompt]
    I --> J[LLM]
    J --> K[Answer + Citation]
>>>>>>> upstream/main
```
