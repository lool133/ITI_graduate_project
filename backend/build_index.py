from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
BACKEND_DATA = ROOT / "backend" / "data"
VECTOR_DIR = BACKEND_DATA / "vector_store"
CONFIG_PATH = BACKEND_DATA / "pipeline_config.json"
COLLECTION_NAME = "privacy_regulations"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def chunks_from_page(text: str, page: int, source: str) -> list[dict]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    words = cleaned.split()
    chunks = []
    step = 360
    size = 450
    for start in range(0, len(words), step):
        words_chunk = words[start:start + size]
        if len(words_chunk) < 40:
            continue
        chunks.append({
            "text": " ".join(words_chunk),
            "metadata": {"source_file": source, "page": page, "citation": f"{source}, page {page}"},
        })
    return chunks


def main() -> None:
    pdf_paths = sorted(RAW_DIR.glob("**/*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in {RAW_DIR}")

    chunks = []
    for pdf_path in pdf_paths:
        reader = PdfReader(str(pdf_path))
        for page_number, page in enumerate(reader.pages, 1):
            chunks.extend(chunks_from_page(page.extract_text() or "", page_number, pdf_path.name))

    if not chunks:
        raise RuntimeError("The PDFs contain no extractable text.")

    print(f"Embedding {len(chunks)} chunks...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(
        [QUERY_PREFIX + item["text"] for item in chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    BACKEND_DATA.mkdir(parents=True, exist_ok=True)
    if VECTOR_DIR.exists():
        shutil.rmtree(VECTOR_DIR)
    client = chromadb.PersistentClient(path=str(VECTOR_DIR), settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(name=COLLECTION_NAME, configuration={"hnsw": {"space": "cosine"}})
    collection.add(
        ids=[f"chunk-{index}" for index in range(len(chunks))],
        documents=[item["text"] for item in chunks],
        metadatas=[item["metadata"] for item in chunks],
        embeddings=embeddings,
    )

    CONFIG_PATH.write_text(json.dumps({
        "collection_name": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "query_prefix": QUERY_PREFIX,
        "retrieval_top_k": 5,
        "max_distance": 1.05,
        "llm_model": "gemini-2.5-flash",
        "llm_provider": "gemini",
        "llm_temperature": 0.0,
        "n_chunks": collection.count(),
        "n_source_files": len(pdf_paths),
    }, indent=2), encoding="utf-8")
    print(f"Index ready: {collection.count()} chunks from {len(pdf_paths)} PDF(s)")


if __name__ == "__main__":
    main()
