"""Minimal RAG pipeline: load -> chunk -> embed -> retrieve -> answer.

LLM_PROVIDER=ollama (default, fully local) or gemini (hosted, needs GEMINI_API_KEY). Set in .env.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import numpy as np
from pypdf import PdfReader


def _load_dotenv(path: Path = Path(__file__).parent / ".env") -> None:
    """Tiny .env reader (KEY=VALUE lines) so no extra dependency is needed. Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
if PROVIDER == "gemini":
    EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")
else:
    EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")

_gemini_client = None


def _gemini():
    global _gemini_client
    if _gemini_client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env")
        from google import genai
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


def _retry_delay(exc: Exception, attempt: int):
    """Seconds to wait before retrying a Gemini error, or None if the error is not retryable."""
    code = getattr(exc, "code", None)
    if code == 429:   # free-tier rate limit is per minute
        return 20 * (attempt + 1)
    if code in (500, 503):  # temporary overload
        return 2 ** (attempt + 1)
    return None


def _gemini_call(fn, retries: int = 4):
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            delay = _retry_delay(e, attempt)
            if delay is None or attempt == retries:
                raise
            time.sleep(delay)


SYSTEM_PROMPT = (
    "You are a document assistant. Answer ONLY using the provided context. "
    "If the answer is not in the context, reply exactly: \"I don't know based on the document.\" "
    "Cite sources like [1], [2] matching the numbered context passages."
)


@dataclass
class Chunk:
    text: str
    source: str
    page: int


def load_pdf(file, name: str) -> List[tuple]:
    """Return [(page_number, text)] for a path or file-like object."""
    reader = PdfReader(file)
    return [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]


def chunk_text(text: str, size: int = 800, overlap: int = 150) -> List[str]:
    """Fixed-size character windows with overlap so sentences cut at a boundary survive in the next chunk."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]


def embed(texts: Iterable[str]) -> np.ndarray:
    """Embed texts and L2-normalise so a dot product equals cosine similarity."""
    texts = list(texts)
    if PROVIDER == "gemini":
        resp = _gemini_call(lambda: _gemini().models.embed_content(model=EMBED_MODEL, contents=texts))
        raw = [e.values for e in resp.embeddings]
    else:
        import ollama
        raw = ollama.embed(model=EMBED_MODEL, input=texts)["embeddings"]
    vecs = np.array(raw, dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def _chat_stream(messages: List[dict]) -> Iterable[str]:
    """Yield answer text pieces from the configured provider. messages[0] is the system prompt."""
    if PROVIDER == "gemini":
        from google.genai import types
        contents = [
            types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
            for m in messages[1:]
        ]
        config = types.GenerateContentConfig(system_instruction=messages[0]["content"], temperature=0.1)
        # Retry only until the first piece arrives; after that the answer is already streaming to the user.
        for attempt in range(5):
            started = False
            try:
                for part in _gemini().models.generate_content_stream(model=CHAT_MODEL, contents=contents, config=config):
                    if part.text:
                        started = True
                        yield part.text
                return
            except Exception as e:
                delay = _retry_delay(e, attempt)
                if started or delay is None or attempt == 4:
                    raise
                time.sleep(delay)
    else:
        import ollama
        for part in ollama.chat(model=CHAT_MODEL, messages=messages, stream=True, options={"temperature": 0.1}):
            yield part["message"]["content"]


class VectorStore:
    def __init__(self):
        self.chunks: List[Chunk] = []
        self.matrix = np.empty((0, 0), dtype=np.float32)

    def add_document(self, file, name: str, size: int = 800, overlap: int = 150, batch: int = 32):
        new: List[Chunk] = []
        for page, text in load_pdf(file, name):
            new += [Chunk(c, name, page) for c in chunk_text(text, size, overlap)]
        if not new:
            raise ValueError(f"No extractable text in {name} (scanned PDF?)")
        vecs = np.vstack([embed(c.text for c in new[i:i + batch]) for i in range(0, len(new), batch)])
        self.matrix = vecs if self.matrix.size == 0 else np.vstack([self.matrix, vecs])
        self.chunks += new
        return len(new)

    def search(self, query: str, k: int = 4):
        scores = self.matrix @ embed([query])[0]
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


def answer(store: VectorStore, question: str, k: int = 4, history: List[dict] | None = None):
    hits = store.search(question, k)
    context = "\n\n".join(f"[{i+1}] ({c.source}, p.{c.page}) {c.text}" for i, (c, _) in enumerate(hits))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history or []
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})
    return hits, _chat_stream(messages)
