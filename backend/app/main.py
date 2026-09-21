"""FastAPI backend for the Privacy Compliance RAG assistant."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
log = logging.getLogger("rag_api")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
CONFIG_PATH = Path(os.getenv("PIPELINE_CONFIG", str(BASE_DIR / "data" / "pipeline_config.json")))
VECTOR_DIR = Path(os.getenv("VECTOR_STORE", str(BASE_DIR / "data" / "vector_store")))

_config: dict[str, Any] = {}
_embedder: SentenceTransformer | None = None
_collection: Any | None = None
_gemini_api_key = os.getenv("GEMINI_API_KEY")
_gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _embedder, _collection

    if CONFIG_PATH.exists():
        _config = json.loads(CONFIG_PATH.read_text())
        log.info("Loaded pipeline_config.json from %s", CONFIG_PATH)
    else:
        _config = {
            "collection_name": "privacy_regulations",
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "query_prefix": "Represent this sentence for searching relevant passages: ",
            "retrieval_top_k": 5,
            "max_distance": 1.05,
            "llm_model": _gemini_model,
            "llm_provider": "gemini",
            "llm_temperature": 0.0,
        }
        log.warning("pipeline_config.json not found; using defaults.")

    _config["llm_model"] = _gemini_model
    _config["llm_provider"] = "gemini"
    log.info("Loading embedding model: %s", _config["embedding_model"])
    _embedder = SentenceTransformer(_config["embedding_model"])

    if VECTOR_DIR.exists():
        chroma = chromadb.PersistentClient(path=str(VECTOR_DIR), settings=Settings(anonymized_telemetry=False))
        collection_name = _config.get("collection_name", "privacy_regulations")
        try:
            _collection = chroma.get_collection(collection_name)
            log.info("Chroma collection loaded; %d vectors.", _collection.count())
        except Exception as exc:
            log.warning("Chroma collection '%s' not found: %s", collection_name, exc)
    else:
        log.warning("Chroma vector store not found at %s. Run the notebook first.", VECTOR_DIR)

    if _gemini_api_key:
        log.info("Gemini configured: %s", _gemini_model)
    else:
        log.warning("GEMINI_API_KEY is not set.")

    yield
    log.info("Shutting down.")


app = FastAPI(
    title="Privacy Compliance RAG API",
    version="1.1.0",
    description="RAG assistant using Chroma for vector search and Gemini for generation.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SourceChunk(BaseModel):
    text: str
    source: str
    page: int | None = None
    distance: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    model: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    index_ready: bool
    index_size: int | None
    ollama_ready: bool
    model: str


class CorpusInfo(BaseModel):
    index_size: int
    embedding_model: str
    llm_model: str
    config: dict[str, Any]


RAG_SYSTEM = """You are a precise legal-compliance assistant specialising in data-protection law.
Answer ONLY from the retrieved context below.
If the context does not contain enough information, say so clearly — do NOT fabricate.
Always cite the source article or section number when available.
Be concise but complete. Use plain language where possible."""
RAG_TEMPLATE = """### CONTEXT
{context}

### QUESTION
{question}

### ANSWER
"""


def _retrieve(question: str, top_k: int) -> list[dict]:
    if _collection is None:
        raise HTTPException(503, "Vector store not available. Run the notebook first.")
    if _embedder is None:
        raise HTTPException(503, "Embedding model not loaded.")

    embedding = _embedder.encode([_config.get("query_prefix", "") + question], normalize_embeddings=True).tolist()
    result = _collection.query(query_embeddings=embedding, n_results=top_k, include=["documents", "metadatas", "distances"])
    max_distance = _config.get("max_distance", 1.05)
    return [
        {"document": document, "metadata": metadata, "distance": float(distance)}
        for document, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])
        if distance <= max_distance
    ]


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        source = metadata.get("source_file", metadata.get("source", "unknown"))
        page = metadata.get("page", "?")
        parts.append(f"[{index}] (source: {source}, page: {page})\n{chunk['document']}")
    return "\n\n".join(parts)


def _generate(question: str, context: str) -> str:
    if not _gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY is not configured.")
    payload = json.dumps({
        "contents": [{"parts": [{"text": f"{RAG_SYSTEM}\n\n{RAG_TEMPLATE.format(context=context, question=question)}"}]}],
        "generationConfig": {"temperature": _config.get("llm_temperature", 0.0)},
    }).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{_gemini_model}:generateContent?key={_gemini_api_key}"
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(502, f"Gemini error: {detail}") from exc
    except Exception as exc:
        raise HTTPException(502, f"Gemini error: {exc}") from exc


@app.get("/health", response_model=HealthResponse)
async def health():
    ollama_ready = bool(_gemini_api_key)
    return HealthResponse(status="ok", index_ready=_collection is not None, index_size=_collection.count() if _collection else None, ollama_ready=ollama_ready, model=_config.get("llm_model", "unknown"))


@app.get("/corpus", response_model=CorpusInfo)
async def corpus_info():
    if _collection is None:
        raise HTTPException(503, "Vector store not available.")
    return CorpusInfo(index_size=_collection.count(), embedding_model=_config.get("embedding_model", "unknown"), llm_model=_config.get("llm_model", "unknown"), config=_config)


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    started = time.perf_counter()
    chunks = _retrieve(request.question, request.top_k)
    if not chunks:
        answer = "I could not find relevant sections in the corpus for your question. Please rephrase or ask about GDPR, EDPB guidelines, or Egypt PDPL 151/2020."
        return QueryResponse(answer=answer, sources=[], model=_config.get("llm_model", "unknown"), latency_ms=round((time.perf_counter() - started) * 1000, 1))

    answer = _generate(request.question, _build_context(chunks))
    sources = [
        SourceChunk(
            text=chunk["document"][:400],
            source=chunk["metadata"].get("source_file", chunk["metadata"].get("source", "unknown")),
            page=chunk["metadata"].get("page"),
            distance=round(chunk["distance"], 4),
        )
        for chunk in chunks
    ]
    return QueryResponse(answer=answer, sources=sources, model=_config.get("llm_model", "unknown"), latency_ms=round((time.perf_counter() - started) * 1000, 1))
