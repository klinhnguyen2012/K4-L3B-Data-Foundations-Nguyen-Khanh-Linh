from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self._store = store
        self._llm_fn = llm_fn

    def answer(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> str:
        results = (
            self._store.search_with_filter(
                question,
                top_k=top_k,
                metadata_filter=metadata_filter,
            )
            if metadata_filter
            else self._store.search(question, top_k=top_k)
        )
        if not results:
            return "I could not find relevant information in the knowledge base."

        context_blocks = []
        for index, result in enumerate(results, start=1):
            source = result["metadata"].get("source", result["metadata"].get("doc_id", result["id"]))
            context_blocks.append(f"[{index}] Source: {source}\n{result['content']}")

        prompt = (
            "Answer the question using only the context below. "
            "If the answer is not in the context, say that you could not find it. "
            "Cite the supporting context number(s), for example [1].\n\n"
            f"Context:\n{'\n\n'.join(context_blocks)}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return self._llm_fn(prompt)
