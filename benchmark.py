from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src import (
    EMBEDDING_PROVIDER_ENV,
    NVIDIA_EMBEDDING_MODEL,
    NVIDIA_LLM_MODEL,
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    HeadingSectionChunker,
    KnowledgeBaseAgent,
    NvidiaChatLLM,
    NvidiaEmbedder,
    RecursiveChunker,
)


@dataclass(frozen=True)
class BenchmarkCase:
    number: int
    query: str
    gold_answer: str
    expected_doc_id: str
    expected_evidence: str | tuple[str, ...]
    metadata_filter: dict[str, str] | None = None
    answer_requirements: tuple[tuple[str, ...], ...] = ()


@dataclass
class BenchmarkResult:
    case: BenchmarkCase
    results: list[dict]
    unfiltered_results: list[dict] | None
    unfiltered_relevant_in_top_three: bool | None
    relevant_in_top_three: bool
    gold_rank: int | None
    agent_answer: str
    agent_answer_correct: bool
    points: int


BENCHMARK_CASES = (
    BenchmarkCase(
        number=1,
        query="Người mua cần chuẩn bị giấy tờ gì để được bảo hành miễn phí trên Shopee?",
        gold_answer=(
            "Có hóa đơn điện tử hoặc mã đơn hàng; đối với đồ điện gia dụng cần "
            "phiếu/tem bảo hành còn nguyên vẹn."
        ),
        expected_doc_id="warranty-buyer-shopee",
        expected_evidence=(
            "Có hóa đơn điện tử",
            "mã đơn hàng",
            "phiếu/tem bảo hành",
            "còn nguyên vẹn",
        ),
        metadata_filter={"audience": "buyer"},
        answer_requirements=(
            ("hóa đơn điện tử",),
            ("mã đơn hàng", "id đơn hàng"),
            ("phiếu/tem bảo hành", "phiếu bảo hành", "tem bảo hành"),
            ("nguyên vẹn",),
        ),
    ),
    BenchmarkCase(
        number=2,
        query="Nhà Bán Tiki không xác nhận phương án xử lý trong 02 ngày làm việc thì sao?",
        gold_answer=(
            "Tiki có thể xử lý theo yêu cầu khách hàng và từ chối tiếp nhận khiếu nại "
            "của Nhà Bán phát sinh sau thời hạn."
        ),
        expected_doc_id="warranty-seller-general-tiki",
        expected_evidence=(
            "02 ngày làm việc",
            "Tiki sẽ chủ động xử lý theo yêu cầu",
            "từ chối tiếp nhận các khiếu nại",
        ),
        metadata_filter={"audience": "seller"},
        answer_requirements=(
            ("xử lý theo yêu cầu", "chủ động xử lý"),
            ("từ chối tiếp nhận",),
            ("khiếu nại",),
        ),
    ),
    BenchmarkCase(
        number=3,
        query="Trong mô hình FBT, Nhà Bán phải rút hàng lỗi không đủ điều kiện nhập kho trong bao lâu?",
        gold_answer="Nhà Bán phải sắp xếp rút hàng trong 32 ngày làm việc kể từ khi phiếu trả hàng được tạo.",
        expected_doc_id="warranty-seller-fbt-tiki",
        expected_evidence=("32 ngày làm việc", "kể từ khi phiếu được tạo"),
        metadata_filter={"audience": "seller", "fulfillment_model": "fbt"},
        answer_requirements=(("32 ngày làm việc",), ("phiếu trả hàng", "phiếu được tạo")),
    ),
    BenchmarkCase(
        number=4,
        query=(
            "Ở mô hình Dropship, nếu Nhà Bán từ chối xử lý đổi trả bảo hành thì phải "
            "cung cấp bằng chứng hợp lệ trong bao lâu?"
        ),
        gold_answer=(
            "Trong 02 ngày làm việc kể từ khi nhận yêu cầu hoàn tiền hoặc nhận sản phẩm "
            "từ đối tác vận chuyển."
        ),
        expected_doc_id="warranty-seller-dropship-tiki",
        expected_evidence=(
            "bằng chứng hợp lệ",
            "02 ngày làm việc",
            "nhận được yêu cầu hoàn tiền",
            "nhận được sản phẩm từ đối tác vận chuyển",
        ),
        metadata_filter={"audience": "seller", "fulfillment_model": "dropship"},
        answer_requirements=(
            ("02 ngày làm việc", "2 ngày làm việc"),
            ("yêu cầu hoàn tiền",),
            ("nhận được sản phẩm", "nhận sản phẩm"),
        ),
    ),
    BenchmarkCase(
        number=5,
        query="Trong mô hình SD, Tiki xử lý và quyết định khiếu nại trong thời gian bao lâu?",
        gold_answer="Tiki kiểm tra, xác minh và đưa ra quyết định trong 02–07 ngày làm việc.",
        expected_doc_id="warranty-seller-sd-tiki",
        expected_evidence=("xác minh chứng cứ", "02–07 ngày làm việc"),
        metadata_filter={"audience": "seller", "fulfillment_model": "sd"},
        answer_requirements=(
            ("02-07 ngày làm việc", "2-7 ngày làm việc", "02–07 ngày làm việc", "2–7 ngày làm việc"),
        ),
    ),
)


def _parse_front_matter(raw_text: str) -> tuple[dict[str, str], str]:
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw_text.strip()

    metadata: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return metadata, "\n".join(lines[index + 1 :]).strip()
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    raise ValueError("YAML front matter is missing its closing '---' line.")


def load_policy_documents(data_dir: str | Path) -> list[Document]:
    """Read Markdown policies and their front-matter metadata."""
    documents: list[Document] = []
    required_metadata = {"doc_id", "source_url", "retrieved_at", "document_version", "audience"}

    for path in sorted(Path(data_dir).glob("*.md")):
        metadata, content = _parse_front_matter(path.read_text(encoding="utf-8"))
        missing = required_metadata - metadata.keys()
        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise ValueError(f"{path} is missing required metadata: {missing_fields}")
        documents.append(Document(id=metadata["doc_id"], content=content, metadata=metadata))
    return documents


def chunk_documents(documents: list[Document], chunker: object) -> list[Document]:
    """Apply a chunker and copy source metadata onto every resulting chunk."""
    chunks: list[Document] = []
    for document in documents:
        for chunk_index, content in enumerate(chunker.chunk(document.content)):
            metadata = dict(document.metadata)
            metadata["doc_id"] = document.id
            metadata["chunk_index"] = chunk_index
            chunks.append(
                Document(
                    id=f"{document.id}-chunk-{chunk_index}",
                    content=content,
                    metadata=metadata,
                )
            )
    return chunks


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("–", "-").replace("—", "-").split())


def evaluate_cases(
    store: EmbeddingStore,
    cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...],
    agent: KnowledgeBaseAgent | None = None,
) -> list[BenchmarkResult]:
    """Retrieve top-3 chunks and check whether expected evidence is present."""
    evaluations: list[BenchmarkResult] = []
    for case in cases:
        unfiltered_results = store.search(case.query, top_k=3) if case.metadata_filter else None
        results = (
            store.search_with_filter(case.query, top_k=3, metadata_filter=case.metadata_filter)
            if case.metadata_filter
            else store.search(case.query, top_k=3)
        )

        def contains_expected_evidence(search_results: list[dict]) -> bool:
            required_evidence = (
                (case.expected_evidence,)
                if isinstance(case.expected_evidence, str)
                else case.expected_evidence
            )
            return any(
                result["metadata"].get("doc_id") == case.expected_doc_id
                and all(evidence in result["content"] for evidence in required_evidence)
                for result in search_results
            )

        unfiltered_relevant = (
            contains_expected_evidence(unfiltered_results) if unfiltered_results is not None else None
        )
        relevant = contains_expected_evidence(results)
        gold_rank = next(
            (
                index
                for index, result in enumerate(results, start=1)
                if result["metadata"].get("doc_id") == case.expected_doc_id
                and all(
                    evidence in result["content"]
                    for evidence in (
                        (case.expected_evidence,)
                        if isinstance(case.expected_evidence, str)
                        else case.expected_evidence
                    )
                )
            ),
            None,
        )
        agent_answer = (
            agent.answer(
                case.query,
                top_k=3,
                metadata_filter=case.metadata_filter,
            )
            if agent is not None
            else ""
        )
        normalized_answer = _normalize_text(agent_answer)
        answer_correct = bool(agent_answer) and all(
            any(_normalize_text(option) in normalized_answer for option in alternatives)
            for alternatives in case.answer_requirements
        )
        points = 2 if gold_rank == 1 and answer_correct else 1 if gold_rank in (2, 3) and answer_correct else 0
        evaluations.append(
            BenchmarkResult(
                case=case,
                results=results,
                unfiltered_results=unfiltered_results,
                unfiltered_relevant_in_top_three=unfiltered_relevant,
                relevant_in_top_three=relevant,
                gold_rank=gold_rank,
                agent_answer=agent_answer,
                agent_answer_correct=answer_correct,
                points=points,
            )
        )
    return evaluations


def _build_chunker(strategy: str) -> object:
    if strategy == "fixed":
        return FixedSizeChunker(chunk_size=500, overlap=120)
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=500)
    return HeadingSectionChunker(chunk_size=500)


def _print_results(results: list[BenchmarkResult]) -> None:
    for evaluation in results:
        case = evaluation.case
        print(f"\n[{case.number}] {case.query}")
        if evaluation.unfiltered_results is not None:
            print("  Không filter:")
            for index, result in enumerate(evaluation.unfiltered_results, start=1):
                print(
                    f"    {index}. {result['metadata'].get('doc_id')} "
                    f"score={result['score']:.3f}"
                )
            status = "Có" if evaluation.unfiltered_relevant_in_top_three else "Không"
            print(f"  Không filter có evidence đúng trong top-3: {status}")
        if case.metadata_filter:
            print(f"  Filter: {case.metadata_filter}")
        if evaluation.results:
            top_result = evaluation.results[0]
            preview = top_result["content"].replace("\n", " ")[:220]
            print(
                f"  Top-1: {top_result['metadata'].get('doc_id')} "
                f"score={top_result['score']:.3f} | {preview}"
            )
        gold_position = f"top-{evaluation.gold_rank}" if evaluation.gold_rank else "không có trong top-3"
        print(f"  Gold chunk: {gold_position}")
        print(f"  Gold answer: {case.gold_answer}")
        print(f"  Agent answer: {evaluation.agent_answer}")
        print(f"  Agent trả lời đúng: {'Có' if evaluation.agent_answer_correct else 'Không'}")
        print(f"  Điểm: {evaluation.points}/2")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark retrieval for warranty-policy documents.")
    parser.add_argument(
        "--strategy",
        choices=("fixed", "recursive", "heading"),
        default="heading",
        help="Chunking strategy to evaluate (default: heading).",
    )
    args = parser.parse_args()

    load_dotenv(override=False)
    load_dotenv(dotenv_path=Path(".env.nvidia"), override=False)
    if os.getenv(EMBEDDING_PROVIDER_ENV, "nvidia").strip().lower() != "nvidia":
        raise ValueError("Set EMBEDDING_PROVIDER=nvidia to run the real embedding benchmark.")

    documents = load_policy_documents("data/warranty-policy")
    chunks = chunk_documents(documents, _build_chunker(args.strategy))
    embedder = NvidiaEmbedder(model_name=os.getenv("NVIDIA_EMBEDDING_MODEL", NVIDIA_EMBEDDING_MODEL))
    llm = NvidiaChatLLM(model_name=os.getenv("NVIDIA_LLM_MODEL", NVIDIA_LLM_MODEL))
    store = EmbeddingStore(collection_name=f"warranty_{args.strategy}", embedding_fn=embedder)
    store.add_documents(chunks)
    agent = KnowledgeBaseAgent(store=store, llm_fn=llm)

    print(f"Strategy: {args.strategy}; documents: {len(documents)}; chunks: {len(chunks)}")
    print(f"Embedding model: {embedder.model_name}")
    print(f"LLM model: {llm.model_name}")
    evaluations = evaluate_cases(store, BENCHMARK_CASES, agent=agent)
    _print_results(evaluations)
    print(f"\nTổng điểm: {sum(result.points for result in evaluations)}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
