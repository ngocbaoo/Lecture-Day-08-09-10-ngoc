"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

RRF_K = 60

# Runtime caches để tránh load lại model/index nhiều lần.
_BM25_INDEX = None
_BM25_CHUNKS: List[Dict[str, Any]] = []
_CROSS_ENCODER_MODEL = None
_LOCAL_EMBEDDING_MODEL = None


def _normalize_key(value: str) -> str:
    return value.strip().lower()


def _tokenize(text: str) -> List[str]:
    """Tokenize đơn giản cho BM25 (unicode-aware)."""
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        normalized = _normalize_key(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(item.strip())
    return out


def _chunk_identity(chunk: Dict[str, Any]) -> str:
    """Identity key để merge/dedupe chunk giữa nhiều retrievers."""
    meta = chunk.get("metadata", {})
    source = str(meta.get("source", ""))
    section = str(meta.get("section", ""))
    text = str(chunk.get("text", ""))
    return f"{source}::{section}::{text}"


def _valid_env_value(name: str) -> Optional[str]:
    value = (os.getenv(name) or "").strip()
    if not value:
        return None
    # Bỏ qua placeholder trong .env.example
    if value.endswith("...") or value in {"sk-...", "..."}:
        return None
    return value


def _gemini_embed_content(genai_module, model_name: str, text: str, task_type: str) -> List[float]:
    """Embed text với Gemini, fallback về model ổn định nếu model cấu hình không khả dụng."""
    try:
        response = genai_module.embed_content(
            model=model_name,
            content=text,
            task_type=task_type,
        )
    except Exception:
        fallback_model = "models/gemini-embedding-2-preview"
        if model_name == fallback_model:
            raise
        response = genai_module.embed_content(
            model=fallback_model,
            content=text,
            task_type=task_type,
        )

    embedding = response.get("embedding") if isinstance(response, dict) else None
    if not embedding:
        raise RuntimeError("Gemini embedding trả về rỗng.")
    return embedding


def _get_collection():
    import chromadb
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    return client.get_collection("rag_lab")


def _get_query_embedding(text: str) -> List[float]:
    """
    Sinh query embedding theo EMBEDDING_PROVIDER.

    Khuyến nghị cho Gemini-only:
    - EMBEDDING_PROVIDER=gemini
    - GOOGLE_API_KEY=<your_key>
    """
    embedding_provider = (os.getenv("EMBEDDING_PROVIDER") or "gemini").strip().lower()

    if embedding_provider in {"index", "auto"}:
        try:
            from index import get_embedding
            return get_embedding(text)
        except NotImplementedError:
            if embedding_provider == "index":
                raise RuntimeError(
                    "EMBEDDING_PROVIDER=index nhưng index.py chưa implement get_embedding()."
                )

    if embedding_provider == "local":
        from sentence_transformers import SentenceTransformer

        global _LOCAL_EMBEDDING_MODEL
        model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        if _LOCAL_EMBEDDING_MODEL is None:
            _LOCAL_EMBEDDING_MODEL = SentenceTransformer(model_name)
        return _LOCAL_EMBEDDING_MODEL.encode(text).tolist()

    if embedding_provider == "gemini":
        gemini_key = _valid_env_value("GOOGLE_API_KEY")
        if not gemini_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=gemini nhưng thiếu GOOGLE_API_KEY hợp lệ trong .env"
            )

        import google.generativeai as genai

        genai.configure(api_key=gemini_key)
        return _gemini_embed_content(
            genai_module=genai,
            model_name=EMBEDDING_MODEL,
            text=text,
            task_type="retrieval_query",
        )

    raise RuntimeError(
        "EMBEDDING_PROVIDER không hợp lệ. Dùng 'gemini' (khuyến nghị), hoặc 'local' / 'index'."
    )


def _get_bm25_index() -> Tuple[Any, List[Dict[str, Any]]]:
    """Load toàn bộ chunks từ Chroma và build BM25 index (cache in-memory)."""
    global _BM25_INDEX, _BM25_CHUNKS

    if _BM25_INDEX is not None and _BM25_CHUNKS:
        return _BM25_INDEX, _BM25_CHUNKS

    from rank_bm25 import BM25Okapi

    collection = _get_collection()
    results = collection.get(include=["documents", "metadatas"])

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []

    chunks: List[Dict[str, Any]] = []
    tokenized_corpus: List[List[str]] = []

    for doc, meta in zip(documents, metadatas):
        text = (doc or "").strip()
        chunk = {
            "text": text,
            "metadata": meta or {},
            "score": 0.0,
        }
        chunks.append(chunk)

        tokens = _tokenize(text)
        tokenized_corpus.append(tokens if tokens else ["_"])

    if not tokenized_corpus:
        _BM25_INDEX = None
        _BM25_CHUNKS = []
        return None, []

    _BM25_INDEX = BM25Okapi(tokenized_corpus)
    _BM25_CHUNKS = chunks
    return _BM25_INDEX, _BM25_CHUNKS


def _retrieve_by_mode(mode: str, query: str, top_k: int) -> List[Dict[str, Any]]:
    if mode == "dense":
        return retrieve_dense(query, top_k=top_k)
    if mode == "sparse":
        return retrieve_sparse(query, top_k=top_k)
    if mode == "hybrid":
        return retrieve_hybrid(query, top_k=top_k)
    raise ValueError(f"retrieval_mode không hợp lệ: {mode}")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.

    Args:
        query: Câu hỏi của người dùng
        top_k: Số chunk tối đa trả về

    Returns:
        List các dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata (source, section, effective_date, ...)
          - "score": cosine similarity score

    TODO Sprint 2:
    1. Embed query bằng cùng model đã dùng khi index (xem index.py)
    2. Query ChromaDB với embedding đó
    3. Trả về kết quả kèm score

    Gợi ý:
        import chromadb
        from index import get_embedding, CHROMA_DB_DIR

        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")

        query_embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        # Lưu ý: distances trong ChromaDB cosine = 1 - similarity
        # Score = 1 - distance
    """
    collection = _get_collection()
    query_embedding = _get_query_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    dense_chunks: List[Dict[str, Any]] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        distance_val = float(distance) if distance is not None else 1.0
        dense_chunks.append({
            "text": doc or "",
            "metadata": meta or {},
            "score": 1.0 - distance_val,
        })

    dense_chunks.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return dense_chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    TODO Sprint 3 (nếu chọn hybrid):
    1. Cài rank_bm25: pip install rank-bm25
    2. Load tất cả chunks từ ChromaDB (hoặc rebuild từ docs)
    3. Tokenize và tạo BM25Index
    4. Query và trả về top_k kết quả

    Gợi ý:
        from rank_bm25 import BM25Okapi
        corpus = [chunk["text"] for chunk in all_chunks]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    """
    bm25, all_chunks = _get_bm25_index()
    if bm25 is None or not all_chunks:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda idx: float(scores[idx]),
        reverse=True,
    )

    sparse_chunks: List[Dict[str, Any]] = []
    for idx in ranked_indices:
        score = float(scores[idx])
        if score <= 0:
            continue
        chunk = all_chunks[idx]
        sparse_chunks.append({
            "text": chunk.get("text", ""),
            "metadata": chunk.get("metadata", {}),
            "score": score,
        })
        if len(sparse_chunks) >= top_k:
            break

    return sparse_chunks


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).

    Mạnh ở: giữ được cả nghĩa (dense) lẫn keyword chính xác (sparse)
    Phù hợp khi: corpus lẫn lộn ngôn ngữ tự nhiên và tên riêng/mã lỗi/điều khoản

    Args:
        dense_weight: Trọng số cho dense score (0-1)
        sparse_weight: Trọng số cho sparse score (0-1)

    TODO Sprint 3 (nếu chọn hybrid):
    1. Chạy retrieve_dense() → dense_results
    2. Chạy retrieve_sparse() → sparse_results
    3. Merge bằng RRF:
       RRF_score(doc) = dense_weight * (1 / (60 + dense_rank)) +
                        sparse_weight * (1 / (60 + sparse_rank))
       60 là hằng số RRF tiêu chuẩn
    4. Sort theo RRF score giảm dần, trả về top_k

    Khi nào dùng hybrid (từ slide):
    - Corpus có cả câu tự nhiên VÀ tên riêng, mã lỗi, điều khoản
    - Query như "Approval Matrix" khi doc đổi tên thành "Access Control SOP"
    """
    dense_results: List[Dict[str, Any]] = []
    sparse_results: List[Dict[str, Any]] = []

    dense_error = None
    sparse_error = None

    try:
        dense_results = retrieve_dense(query, top_k=top_k)
    except Exception as e:
        dense_error = e

    try:
        sparse_results = retrieve_sparse(query, top_k=top_k)
    except Exception as e:
        sparse_error = e

    if not dense_results and not sparse_results:
        if dense_error:
            raise dense_error
        if sparse_error:
            raise sparse_error
        return []

    fused_map: Dict[str, Dict[str, Any]] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        key = _chunk_identity(chunk)
        if key not in fused_map:
            fused_map[key] = {
                "chunk": {
                    "text": chunk.get("text", ""),
                    "metadata": chunk.get("metadata", {}),
                    "score": 0.0,
                },
                "dense_rank": None,
                "sparse_rank": None,
            }
        fused_map[key]["dense_rank"] = rank
        fused_map[key]["chunk"]["score"] += dense_weight * (1.0 / (RRF_K + rank))

    for rank, chunk in enumerate(sparse_results, start=1):
        key = _chunk_identity(chunk)
        if key not in fused_map:
            fused_map[key] = {
                "chunk": {
                    "text": chunk.get("text", ""),
                    "metadata": chunk.get("metadata", {}),
                    "score": 0.0,
                },
                "dense_rank": None,
                "sparse_rank": None,
            }
        fused_map[key]["sparse_rank"] = rank
        fused_map[key]["chunk"]["score"] += sparse_weight * (1.0 / (RRF_K + rank))

    fused_results: List[Dict[str, Any]] = []
    for item in fused_map.values():
        chunk = item["chunk"]
        chunk["dense_rank"] = item["dense_rank"]
        chunk["sparse_rank"] = item["sparse_rank"]
        fused_results.append(chunk)

    fused_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return fused_results[:top_k]


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng cross-encoder.

    Cross-encoder: chấm lại "chunk nào thực sự trả lời câu hỏi này?"
    MMR (Maximal Marginal Relevance): giữ relevance nhưng giảm trùng lặp

    Funnel logic (từ slide):
      Search rộng (top-20) → Rerank (top-6) → Select (top-3)

    TODO Sprint 3 (nếu chọn rerank):
    Option A — Cross-encoder:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [[query, chunk["text"]] for chunk in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in ranked[:top_k]]

    Option B — Rerank bằng LLM (đơn giản hơn nhưng tốn token):
        Gửi list chunks cho LLM, yêu cầu chọn top_k relevant nhất

    Khi nào dùng rerank:
    - Dense/hybrid trả về nhiều chunk nhưng có noise
    - Muốn chắc chắn chỉ 3-5 chunk tốt nhất vào prompt
    """
    if not candidates:
        return []

    effective_top_k = max(0, min(top_k, len(candidates)))
    if effective_top_k == 0:
        return []

    try:
        from sentence_transformers import CrossEncoder

        global _CROSS_ENCODER_MODEL
        if _CROSS_ENCODER_MODEL is None:
            _CROSS_ENCODER_MODEL = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        pairs = [[query, chunk.get("text", "")] for chunk in candidates]
        scores = _CROSS_ENCODER_MODEL.predict(pairs)

        ranked_pairs = sorted(
            zip(candidates, scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        reranked = []
        for chunk, score in ranked_pairs[:effective_top_k]:
            reranked.append({
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
                "score": float(score),
            })
        return reranked

    except Exception as e:
        # Fallback nhẹ nếu chưa cài model/package rerank.
        print(f"[rerank] Không thể dùng cross-encoder ({e}). Fallback lexical rerank.")

        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return candidates[:effective_top_k]

        def lexical_score(chunk: Dict[str, Any]) -> float:
            chunk_tokens = set(_tokenize(chunk.get("text", "")))
            overlap = len(query_tokens.intersection(chunk_tokens))
            return overlap / max(1, len(query_tokens))

        ranked = sorted(candidates, key=lexical_score, reverse=True)
        return ranked[:effective_top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả (hypothetical document) để embed thay query

    TODO Sprint 3 (nếu chọn query transformation):
    Gọi LLM với prompt phù hợp với từng strategy.

    Ví dụ expansion prompt:
        "Given the query: '{query}'
         Generate 2-3 alternative phrasings or related terms in Vietnamese.
         Output as JSON array of strings."

    Ví dụ decomposition:
        "Break down this complex query into 2-3 simpler sub-queries: '{query}'
         Output as JSON array."

    Khi nào dùng:
    - Expansion: query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    - Decomposition: query hỏi nhiều thứ một lúc
    - HyDE: query mơ hồ, search theo nghĩa không hiệu quả
    """
    query = query.strip()
    if not query:
        return []

    strategy = (strategy or "expansion").strip().lower()

    if strategy == "decomposition":
        parts = re.split(
            r"\s+(?:và|and|hoặc|or|then|sau đó)\s+|[;?]",
            query,
            flags=re.IGNORECASE,
        )
        parts = [p.strip() for p in parts if len(p.strip()) >= 5]
        return _dedupe_keep_order([query] + parts)[:4]

    if strategy == "hyde":
        hypothetical = (
            f"Tài liệu nội bộ mô tả chi tiết về: {query}. "
            "Nêu rõ điều kiện áp dụng, thời hạn xử lý, và bộ phận chịu trách nhiệm."
        )
        return _dedupe_keep_order([query, hypothetical])

    # Default: expansion
    expansions = [query]
    lower_query = query.lower()

    expansion_map = {
        "approval matrix": ["access control sop", "system access"],
        "cấp quyền": ["access control", "phê duyệt quyền"],
        "hoàn tiền": ["refund", "refund request"],
        "p1": ["critical", "incident", "sla"],
        "ticket": ["jira", "it-support"],
        "err-403-auth": ["authentication", "authorization", "login failed"],
    }

    for trigger, terms in expansion_map.items():
        if trigger in lower_query:
            for term in terms:
                expansions.append(f"{query} {term}")

    # Alias từ data/docs: Approval Matrix -> Access Control SOP
    if "approval matrix" in lower_query:
        expansions.append(re.sub(r"approval matrix", "Access Control SOP", query, flags=re.IGNORECASE))

    return _dedupe_keep_order(expansions)[:5]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.

    TODO Sprint 2:
    Gemini-only (cần GOOGLE_API_KEY):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text

    Lưu ý: Dùng temperature=0 hoặc thấp để output ổn định cho evaluation.
    """
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    gemini_key = _valid_env_value("GOOGLE_API_KEY")
    openai_key = _valid_env_value("OPENAI_API_KEY")

    if provider in {"", "auto"}:
        provider = "openai"

    if provider == "openai":
        if not openai_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai nhưng thiếu OPENAI_API_KEY hợp lệ trong .env"
            )
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    if provider == "gemini":
        if not gemini_key:
            raise RuntimeError(
                "LLM_PROVIDER=gemini nhưng thiếu GOOGLE_API_KEY hợp lệ trong .env"
            )

        import google.generativeai as genai

        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash") # Fallback to stable gemini if needed, but the user asked for openai
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0},
        )
        answer = (getattr(response, "text", "") or "").strip()
        return answer or "Không đủ dữ liệu trong tài liệu được truy xuất."

    raise ValueError(f"LLM_PROVIDER không hợp lệ: {provider}. Chỉ hỗ trợ 'openai' và 'gemini'.")


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    query_transform_strategy = (os.getenv("QUERY_TRANSFORM_STRATEGY") or "none").strip().lower()
    config["query_transform_strategy"] = query_transform_strategy

    retrieval_queries = [query]
    if query_transform_strategy and query_transform_strategy != "none":
        retrieval_queries = transform_query(query, strategy=query_transform_strategy)

    # --- Bước 1: Retrieve ---
    merged_candidates: Dict[str, Dict[str, Any]] = {}
    for query_variant in retrieval_queries:
        current_candidates = _retrieve_by_mode(retrieval_mode, query_variant, top_k=top_k_search)
        for chunk in current_candidates:
            key = _chunk_identity(chunk)
            chunk_score = float(chunk.get("score", 0.0))
            if key not in merged_candidates or chunk_score > float(merged_candidates[key].get("score", 0.0)):
                merged_candidates[key] = {
                    "text": chunk.get("text", ""),
                    "metadata": chunk.get("metadata", {}),
                    "score": chunk_score,
                    "retrieved_with_query": query_variant,
                }

    candidates = sorted(
        merged_candidates.values(),
        key=lambda x: x.get("score", 0.0),
        reverse=True,
    )[:top_k_search]

    if verbose:
        print(f"\n[RAG] Query: {query}")
        if len(retrieval_queries) > 1:
            print(f"[RAG] Query variants: {retrieval_queries}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    if not candidates:
        abstain = "Không đủ dữ liệu trong tài liệu để trả lời câu hỏi này."
        return {
            "query": query,
            "answer": abstain,
            "sources": [],
            "chunks_used": [],
            "config": config,
        }

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "sparse", "hybrid"]

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    # print("\n--- Sprint 3: So sánh strategies ---")
    # compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    # compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Implement retrieve_dense() — query ChromaDB")
    print("  2. Implement call_llm() — gọi Gemini")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
