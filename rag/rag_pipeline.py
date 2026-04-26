"""
RAG Pipeline — End-to-end Retrieval-Augmented Generation for SintraPrime.

Flow:
  User question → retrieve relevant passages → build prompt → LLM → grounded answer
"""

import asyncio
import json
import os
import re
import time
from typing import Optional

from .embedder import EmbeddingProvider
from .retriever import LegalRetriever
from .vector_store import VectorStore


class RAGPipeline:
    """
    End-to-end RAG pipeline.

    LLM backends (priority order):
    1. OpenAI GPT-4o / GPT-4-turbo (if OPENAI_API_KEY set)
    2. Local Ollama (if OLLAMA_URL env var set, e.g. http://localhost:11434)
    3. Template-based answer (always available — no dependencies)
    """

    MAX_CONTEXT_PASSAGES = 8
    MAX_PASSAGE_CHARS = 1500
    MIN_CONFIDENCE = 0.10

    def __init__(
        self,
        retriever: LegalRetriever,
        embedder: EmbeddingProvider,
        llm_model: Optional[str] = None,
    ):
        self.retriever = retriever
        self.embedder = embedder
        self.llm_model = llm_model
        self._openai_client = None
        self._llm_backend = self._detect_llm_backend()

    # ------------------------------------------------------------------ #
    #  LLM backend detection                                              #
    # ------------------------------------------------------------------ #

    def _detect_llm_backend(self) -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                from openai import AsyncOpenAI  # type: ignore
                self._openai_client = AsyncOpenAI(api_key=api_key)
                return "openai"
            except ImportError:
                pass

        if os.environ.get("OLLAMA_URL"):
            return "ollama"

        return "template"

    # ------------------------------------------------------------------ #
    #  Main public API                                                     #
    # ------------------------------------------------------------------ #

    async def ask(
        self,
        question: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 8,
    ) -> dict:
        """
        Ask any legal question and receive a grounded answer.

        Returns:
        {
          "answer": "...",
          "confidence": 0.87,
          "citations": [{"source": "...", "passage": "..."}],
          "follow_up_questions": ["...", "..."],
          "jurisdiction": "federal",
          "retrieval_count": 5,
          "llm_backend": "openai"
        }
        """
        start = time.perf_counter()

        # 1. Retrieve relevant passages
        passages = await self.retriever.retrieve(
            question, top_k=top_k, jurisdiction=jurisdiction
        )

        # 2. Compute overall confidence
        confidence = self._compute_confidence(passages)

        # 3. Build prompt
        prompt = await self.build_context_prompt(question, passages)

        # 4. Generate answer
        raw_answer = await self._generate_answer(prompt, question)

        # 5. Extract citations
        citations = self._extract_citations(passages)

        # 6. Generate follow-up questions
        follow_ups = self._generate_follow_ups(question, passages)

        # 7. Detect jurisdiction if not provided
        detected_jurisdiction = jurisdiction or self._detect_jurisdiction(passages)

        elapsed = round(time.perf_counter() - start, 3)

        return {
            "answer": raw_answer,
            "confidence": round(confidence, 3),
            "citations": citations,
            "follow_up_questions": follow_ups,
            "jurisdiction": detected_jurisdiction,
            "retrieval_count": len(passages),
            "llm_backend": self._llm_backend,
            "elapsed_seconds": elapsed,
        }

    async def ask_trust_law(self, question: str) -> dict:
        """Specialised trust law Q&A with domain-boosted retrieval."""
        passages = await self.retriever.retrieve_for_trust_law(question)
        confidence = self._compute_confidence(passages)
        prompt = await self.build_context_prompt(
            question, passages,
            system_hint=(
                "You are a trust law specialist. Focus your answer on fiduciary duties, "
                "trust administration, beneficiary rights, and applicable state/federal law."
            ),
        )
        raw_answer = await self._generate_answer(prompt, question)
        citations = self._extract_citations(passages)
        follow_ups = self._generate_follow_ups(question, passages)

        return {
            "answer": raw_answer,
            "confidence": round(confidence, 3),
            "citations": citations,
            "follow_up_questions": follow_ups,
            "jurisdiction": self._detect_jurisdiction(passages) or "varies_by_state",
            "domain": "trust_law",
            "retrieval_count": len(passages),
            "llm_backend": self._llm_backend,
        }

    async def analyze_document(self, document_text: str) -> dict:
        """
        Analyze a legal document: identify type, risks, parties, obligations.
        """
        question = (
            "Analyze this legal document. Identify: document type, parties involved, "
            "key obligations, potential risks, and any unusual clauses."
        )

        # Use the document itself as context
        synthetic_passages = [
            {
                "content": document_text[:8000],
                "score": 1.0,
                "source": "submitted_document",
                "metadata": {"category": "user_document"},
                "entry_id": "submitted",
            }
        ]

        # Also retrieve supporting context
        supporting = await self.retriever.retrieve(question, top_k=4)

        all_passages = synthetic_passages + supporting
        prompt = await self.build_context_prompt(question, all_passages,
            system_hint=(
                "You are a legal document analyst. Provide structured analysis with sections: "
                "Document Type, Parties, Key Obligations, Risk Factors, Notable Clauses."
            ))

        raw_answer = await self._generate_answer(prompt, question)
        citations = self._extract_citations(supporting)

        return {
            "analysis": raw_answer,
            "document_length_chars": len(document_text),
            "supporting_citations": citations,
            "llm_backend": self._llm_backend,
        }

    async def find_precedents(self, case_facts: str) -> dict:
        """Find relevant case law for given facts."""
        passages = await self.retriever.retrieve_precedents(case_facts)
        question = (
            f"Given these case facts: {case_facts[:500]}\n\n"
            "What are the most relevant legal precedents and how do they apply?"
        )
        prompt = await self.build_context_prompt(question, passages,
            system_hint=(
                "You are a legal researcher specialising in case law. "
                "Cite specific cases, explain their holdings, and apply them to the given facts."
            ))

        raw_answer = await self._generate_answer(prompt, question)
        citations = self._extract_citations(passages)

        return {
            "precedents_summary": raw_answer,
            "case_citations": citations,
            "cases_found": len(passages),
            "llm_backend": self._llm_backend,
        }

    async def build_context_prompt(
        self,
        question: str,
        passages: list[dict],
        system_hint: str = "",
    ) -> str:
        """Build LLM prompt with retrieved context and inline citations."""
        # Select and truncate passages
        selected = passages[: self.MAX_CONTEXT_PASSAGES]

        context_blocks: list[str] = []
        for i, p in enumerate(selected, 1):
            source = p.get("source", "unknown")
            score = p.get("score", 0.0)
            content = p.get("content", "")[:self.MAX_PASSAGE_CHARS]
            context_blocks.append(
                f"[PASSAGE {i}] Source: {source} (relevance: {score:.2f})\n{content}"
            )

        context_text = "\n\n---\n\n".join(context_blocks)

        domain_hint = system_hint or (
            "You are SintraPrime, an expert AI legal assistant. "
            "Answer questions accurately using the provided legal context. "
            "Always cite relevant passages. If uncertain, say so clearly. "
            "Do not invent case citations or statutes not in the context."
        )

        prompt = (
            f"{domain_hint}\n\n"
            f"=== RETRIEVED LEGAL CONTEXT ===\n\n"
            f"{context_text}\n\n"
            f"=== END CONTEXT ===\n\n"
            f"USER QUESTION: {question}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Answer the question using the context above.\n"
            f"2. Cite specific passages by number (e.g., [PASSAGE 1]).\n"
            f"3. Note the jurisdiction that applies.\n"
            f"4. If the context is insufficient, clearly state what additional "
            f"information would be needed.\n\n"
            f"ANSWER:"
        )

        return prompt

    # ------------------------------------------------------------------ #
    #  LLM generation                                                      #
    # ------------------------------------------------------------------ #

    async def _generate_answer(self, prompt: str, question: str) -> str:
        """Route to the detected LLM backend."""
        if self._llm_backend == "openai":
            return await self._openai_generate(prompt)
        elif self._llm_backend == "ollama":
            return await self._ollama_generate(prompt)
        else:
            return self._template_generate(prompt, question)

    async def _openai_generate(self, prompt: str) -> str:
        model = self.llm_model or "gpt-4o"
        try:
            response = await self._openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            return f"[LLM Error: {exc}] Falling back to template response.\n\n{self._template_generate(prompt, '')}"

    async def _ollama_generate(self, prompt: str) -> str:
        import urllib.request

        url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        model = self.llm_model or "mistral"
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()

        loop = asyncio.get_event_loop()

        def _call():
            req = urllib.request.Request(
                f"{url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            return data.get("response", "")

        try:
            return await loop.run_in_executor(None, _call)
        except Exception as exc:
            return f"[Ollama Error: {exc}]"

    def _template_generate(self, prompt: str, question: str) -> str:
        """
        Template-based answer when no LLM is available.
        Extracts key passages from the context and formats them as an answer.
        """
        # Pull context passages from the prompt
        passage_blocks = re.findall(
            r"\[PASSAGE (\d+)\] Source: ([^\n]+)\n(.+?)(?=\n\n---|=== END|$)",
            prompt,
            re.DOTALL,
        )

        if not passage_blocks:
            return (
                "Based on SintraPrime's legal knowledge base, I was unable to find "
                "sufficiently relevant passages to answer your question with confidence. "
                "Please rephrase or provide more context."
            )

        lines = [
            "Based on SintraPrime's legal knowledge base, here is what I found:\n"
        ]

        for idx, source, content in passage_blocks[:4]:
            snippet = content.strip()[:400]
            lines.append(f"**[PASSAGE {idx}] — {source.strip()}**\n{snippet}\n")

        lines.append(
            "\n⚠️ *This response was generated using SintraPrime's template engine "
            "(no LLM API key detected). For more detailed analysis, configure "
            "OPENAI_API_KEY or OLLAMA_URL.*"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Helper methods                                                      #
    # ------------------------------------------------------------------ #

    def _compute_confidence(self, passages: list[dict]) -> float:
        """Compute overall confidence from passage scores."""
        if not passages:
            return 0.0
        scores = [p.get("score", 0.0) for p in passages[:5]]
        # Weighted average — top passage gets more weight
        weights = [1.0 / (i + 1) for i in range(len(scores))]
        total_w = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return min(1.0, weighted_sum / total_w)

    def _extract_citations(self, passages: list[dict]) -> list[dict]:
        """Format citations for the response."""
        citations = []
        seen: set[str] = set()
        for p in passages:
            source = p.get("source", "unknown")
            if source in seen:
                continue
            seen.add(source)
            citations.append(
                {
                    "source": source,
                    "passage": p.get("content", "")[:300],
                    "score": p.get("score", 0.0),
                    "metadata": {
                        k: v
                        for k, v in p.get("metadata", {}).items()
                        if k in ("category", "jurisdiction", "case_name", "date_filed")
                    },
                }
            )
        return citations[:8]

    def _generate_follow_ups(self, question: str, passages: list[dict]) -> list[str]:
        """Generate contextually relevant follow-up questions."""
        # Base follow-ups derived from domain
        categories = {p.get("metadata", {}).get("category", "") for p in passages}
        follow_ups: list[str] = []

        if "trust_law" in categories:
            follow_ups += [
                "What are the fiduciary duties of a trustee in this situation?",
                "How does the applicable state's Uniform Trust Code apply?",
                "What are the beneficiary's rights to information?",
            ]
        if "case_law" in categories:
            follow_ups += [
                "Are there any circuit splits on this legal issue?",
                "How has this area of law evolved over the past 10 years?",
            ]
        if "federal_agencies" in categories:
            follow_ups += [
                "What are the applicable regulatory filing requirements?",
                "Are there any pending rulemaking changes in this area?",
            ]

        # Generic follow-ups
        generic = [
            f"What are the defenses available in this situation?",
            f"What statutes of limitation apply to this type of claim?",
            f"What documentation is typically required?",
        ]

        all_follow_ups = follow_ups[:2] + generic[:1]
        # Deduplicate
        seen: set[str] = set()
        result: list[str] = []
        for q in all_follow_ups:
            if q not in seen:
                seen.add(q)
                result.append(q)

        return result[:3]

    def _detect_jurisdiction(self, passages: list[dict]) -> str:
        """Detect the most common jurisdiction from retrieved passages."""
        counts: dict[str, int] = {}
        for p in passages:
            jur = p.get("metadata", {}).get("jurisdiction", "")
            if jur and jur != "unknown":
                counts[jur] = counts.get(jur, 0) + 1
        if not counts:
            return "unknown"
        return max(counts, key=lambda k: counts[k])
