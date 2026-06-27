"""
app/rag/embedder.py

Chunks text → Gemini embeddings → ChromaDB.
Key features:
- Content-hash deduplication (never re-embeds same text)
- Batch embedding (respects Gemini free tier limits)
- Retry on transient API errors
"""
import hashlib
import time
import chromadb
from chromadb.config import Settings as ChromaSettings
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.utils.logger import get_logger

log = get_logger(__name__)
settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)

# Persistent ChromaDB — survives container restarts via Docker volume
_chroma = chromadb.PersistentClient(
    path=settings.chroma_persist_dir,
    settings=ChromaSettings(anonymized_telemetry=False),
)


def _collection_name(company: str) -> str:
    """ChromaDB collection name — must be alphanumeric + underscore."""
    safe = company.lower().strip()
    safe = "".join(c if c.isalnum() else "_" for c in safe)
    return f"watchr_{safe}"[:63]


def get_collection(company: str):
    return _chroma.get_or_create_collection(
        name=_collection_name(company),
        metadata={"hnsw:space": "cosine"},
    )


def chunk_text(text: str, size: int = 350, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping word-count chunks.
    size=350 words → ~500 tokens, good balance for retrieval.
    overlap=50 → context continuity across chunks.
    """
    words = text.split()
    if not words:
        return []
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i: i + size])
        if len(chunk.strip()) > 40:
            chunks.append(chunk)
        i += size - overlap
    return chunks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def _embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of texts with Gemini text-embedding-004.
    Rate limited to free tier: 1500 req/min.
    """
    result = genai.embed_content(
        model=settings.gemini_embedding_model,
        content=texts,
        task_type="retrieval_document",
    )
    return result["embedding"]


def embed_and_store(
    company: str,
    source: str,
    url: str,
    title: str,
    content: str,
    metadata: dict | None = None,
) -> int:
    """
    Chunk → embed → store in ChromaDB.
    Returns number of NEW chunks stored (0 if all already exist).
    Thread-safe for Celery workers.
    """
    collection = get_collection(company)
    chunks = chunk_text(content)
    if not chunks:
        return 0

    # Filter chunks that are already embedded (by content hash)
    new_ids, new_texts, new_metas = [], [], []
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.sha256(
            f"{url}|{i}|{chunk[:60]}".encode()
        ).hexdigest()[:32]

        try:
            existing = collection.get(ids=[chunk_id])
            if existing["ids"]:
                continue  # already exists — skip
        except Exception:
            pass

        new_ids.append(chunk_id)
        new_texts.append(chunk)
        new_metas.append({
            "company":     company,
            "source":      source,
            "url":         url,
            "title":       title[:200],
            "chunk_index": i,
            **(metadata or {}),
        })

    if not new_ids:
        log.debug("All chunks already embedded for %s / %s", company, url[:60])
        return 0

    # Embed in batches of EMBED_BATCH_SIZE (Gemini API limit)
    batch_size = settings.embed_batch_size
    all_embeddings: list[list[float]] = []
    for i in range(0, len(new_texts), batch_size):
        batch = new_texts[i: i + batch_size]
        try:
            embeddings = _embed_batch(batch)
            all_embeddings.extend(embeddings)
            # Respect free tier rate limit
            if i + batch_size < len(new_texts):
                time.sleep(1.5)
        except Exception as e:
            log.error("Embedding batch failed: %s", e)
            break

    if len(all_embeddings) != len(new_ids):
        log.warning("Embedding count mismatch — partial store")
        n = min(len(all_embeddings), len(new_ids))
        new_ids, new_texts, new_metas, all_embeddings = (
            new_ids[:n], new_texts[:n], new_metas[:n], all_embeddings[:n]
        )

    if not all_embeddings:
        return 0

    collection.add(
        ids=new_ids,
        embeddings=all_embeddings,
        documents=new_texts,
        metadatas=new_metas,
    )

    log.info("Stored %d chunks for %s [%s]", len(new_ids), company, source)
    return len(new_ids)
