"""
app/rag/retriever.py
Semantic retrieval over ChromaDB.
Called before every LangGraph analysis node.
"""
import time
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.rag.embedder import get_collection
from app.config import get_settings
from app.utils.logger import get_logger

log = get_logger(__name__)
settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
def _embed_query(text: str) -> list[float]:
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


def retrieve(
    company: str,
    query: str,
    k: int = 8,
    source: str | None = None,
    min_score: float = 0.3,
) -> list[dict]:
    """
    Retrieve top-k semantically relevant chunks for a query.

    Args:
        company:    Company name (used to select ChromaDB collection)
        query:      Natural language query
        k:          Max chunks to return
        source:     Filter by source type ('blog', 'github', etc.)
        min_score:  Minimum cosine similarity (0–1)

    Returns:
        List of {text, url, title, source, score} sorted by relevance
    """
    collection = get_collection(company)
    count = collection.count()

    if count == 0:
        log.warning("Empty collection for %s — no data to retrieve", company)
        return []

    # Embed query
    try:
        query_vec = _embed_query(query)
    except Exception as e:
        log.error("Query embedding failed: %s", e)
        return []

    # Build where filter
    where_filter = None
    if source:
        where_filter = {"source": source}

    # Query ChromaDB
    try:
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=min(k * 2, count),  # get more then filter by score
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        log.error("ChromaDB query failed: %s", e)
        return []

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = round(1 - dist, 3)
        if score < min_score:
            continue
        chunks.append({
            "text":   doc,
            "url":    meta.get("url", ""),
            "title":  meta.get("title", ""),
            "source": meta.get("source", ""),
            "score":  score,
        })

    # Sort by score descending, cap at k
    chunks.sort(key=lambda x: x["score"], reverse=True)
    return chunks[:k]


def retrieve_multi(
    company: str,
    queries: list[str],
    k_per_query: int = 5,
) -> list[dict]:
    """
    Run multiple queries and deduplicate results.
    Useful for broad analysis nodes that need coverage across topics.
    """
    seen_texts: set[str] = set()
    all_chunks = []

    for query in queries:
        chunks = retrieve(company, query, k=k_per_query)
        for chunk in chunks:
            key = chunk["text"][:80]
            if key not in seen_texts:
                seen_texts.add(key)
                all_chunks.append(chunk)
        time.sleep(0.5)  # gentle rate limiting

    return all_chunks
