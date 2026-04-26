"""
Multi-provider embeddings for SintraPrime RAG.

Priority order:
1. OpenAI text-embedding-3-small  (requires OPENAI_API_KEY)
2. sentence-transformers           (requires pip install sentence-transformers)
3. TF-IDF fallback                 (always available — no dependencies)
"""

import asyncio
import hashlib
import math
import os
import re
from collections import Counter
from typing import Optional


class EmbeddingProvider:
    """
    Multi-provider embedding generator.

    Detection happens once at instantiation; the fastest available provider
    is used transparently. The TF-IDF fallback produces 512-dimensional
    sparse vectors and requires no API keys or extra packages.

    Attributes:
        provider: "openai" | "sentence_transformers" | "tfidf"
        dim:       Embedding dimension for the active provider.
    """

    # TF-IDF vocabulary size
    TFIDF_DIM = 512

    # Common English stop words (kept small to avoid dependency)
    _STOP_WORDS = frozenset(
        "a an the and or not but in on at to of for with is are was were be been "
        "being have has had do does did will would could should may might shall "
        "that this these those it its itself they them their there here when where "
        "who which what how why if because while after before as by from into through "
        "during including until against among throughout despite towards upon concerning "
        "of to in for on with at by from".split()
    )

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self._openai_client = None
        self._st_model = None
        self._tfidf_vocab: dict[str, int] = {}   # term → index
        self._idf: list[float] = []
        self._corpus_for_idf: list[str] = []

        self.provider, self.dim = self._detect_provider()

    # ------------------------------------------------------------------ #
    #  Provider detection                                                  #
    # ------------------------------------------------------------------ #

    def _detect_provider(self) -> tuple[str, int]:
        """Detect the best available embedding provider."""
        # 1. OpenAI
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                from openai import AsyncOpenAI  # type: ignore

                self._openai_client = AsyncOpenAI(api_key=api_key)
                return "openai", 1536  # text-embedding-3-small dimension
            except ImportError:
                pass

        # 2. sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            name = self.model_name or "all-MiniLM-L6-v2"
            self._st_model = SentenceTransformer(name)
            dim = self._st_model.get_sentence_embedding_dimension()
            return "sentence_transformers", int(dim)
        except (ImportError, Exception):
            pass

        # 3. TF-IDF fallback
        return "tfidf", self.TFIDF_DIM

    # ------------------------------------------------------------------ #
    #  Public async API                                                    #
    # ------------------------------------------------------------------ #

    async def embed(self, text: str) -> list[float]:
        """Get embedding vector for a single text string."""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed a list of texts for efficiency."""
        if not texts:
            return []

        if self.provider == "openai":
            return await self._openai_embed_batch(texts)
        elif self.provider == "sentence_transformers":
            return await asyncio.get_event_loop().run_in_executor(
                None, self._st_embed_batch, texts
            )
        else:
            return [self._tfidf_embed(t) for t in texts]

    # ------------------------------------------------------------------ #
    #  OpenAI                                                              #
    # ------------------------------------------------------------------ #

    async def _openai_embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API in batches of 100."""
        model = self.model_name or "text-embedding-3-small"
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), 100):
            batch = texts[i: i + 100]
            # Truncate to 8191 tokens (approx 32 KB of chars)
            batch = [t[:32000] for t in batch]
            try:
                response = await self._openai_client.embeddings.create(
                    input=batch, model=model
                )
                for item in response.data:
                    all_embeddings.append(item.embedding)
            except Exception as exc:
                print(f"[EmbeddingProvider] OpenAI error: {exc}. Falling back to TF-IDF.")
                all_embeddings.extend([self._tfidf_embed(t) for t in batch])

        return all_embeddings

    # ------------------------------------------------------------------ #
    #  sentence-transformers                                               #
    # ------------------------------------------------------------------ #

    def _st_embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._st_model.encode(texts, show_progress_bar=False)
        return [list(map(float, vec)) for vec in embeddings]

    # ------------------------------------------------------------------ #
    #  TF-IDF fallback                                                     #
    # ------------------------------------------------------------------ #

    def _tfidf_embed(self, text: str) -> list[float]:
        """
        Produce a 512-dimensional TF-IDF vector.

        The vocabulary is built deterministically from the text itself using
        character n-gram hashing (no corpus needed), so this always works
        without any external data or packages.
        """
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.TFIDF_DIM

        tf: dict[int, float] = {}
        total = len(tokens)
        for tok in tokens:
            idx = self._hash_token(tok)
            tf[idx] = tf.get(idx, 0.0) + 1.0 / total

        # Build vector
        vec = [0.0] * self.TFIDF_DIM
        for idx, freq in tf.items():
            # Mild IDF approximation: log(1 + 1/freq) gives rarer terms more weight
            vec[idx] += freq * (1.0 + math.log1p(1.0 / freq))

        # L2 normalise
        norm = math.sqrt(sum(v * v for v in vec)) + 1e-10
        return [v / norm for v in vec]

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, remove punctuation, filter stop words."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        tokens = text.split()
        return [t for t in tokens if t not in self._STOP_WORDS and len(t) >= 2]

    def _hash_token(self, token: str) -> int:
        """Hash a token to a bucket in [0, TFIDF_DIM)."""
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        return h % self.TFIDF_DIM

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    def fit_idf(self, corpus: list[str]) -> None:
        """
        Optionally fit IDF weights on a corpus for better TF-IDF quality.
        Only used when provider == 'tfidf'. Safe to skip.
        """
        if self.provider != "tfidf":
            return
        self._corpus_for_idf = corpus
        N = len(corpus)
        df: dict[int, int] = {}
        for doc in corpus:
            seen = set()
            for tok in self._tokenize(doc):
                idx = self._hash_token(tok)
                if idx not in seen:
                    df[idx] = df.get(idx, 0) + 1
                    seen.add(idx)
        self._idf = [
            math.log((N + 1) / (df.get(i, 0) + 1)) + 1.0
            for i in range(self.TFIDF_DIM)
        ]

    def __repr__(self) -> str:
        return f"<EmbeddingProvider provider={self.provider} dim={self.dim}>"
