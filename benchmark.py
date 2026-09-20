from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src import (
    EMBEDDING_PROVIDER_ENV,
    NVIDIA_EMBEDDING_MODEL,
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    HeadingSectionChunker,
    NvidiaEmbedder,
    RecursiveChunker,
)


@dataclass(frozen=True)
class BenchmarkCase:
    number: int
    query: str
    expected_doc_id: str
    expected_evidence: str | tuple[str, ...]
    metadata_filter: dict[str, str] | None = None


@dataclass
class BenchmarkResult:
    case: BenchmarkCase
    results: list[dict]
    unfiltered_results: list[dict] | None
    unfiltered_relevant_in_top_three: bool | None
    relevant_in_top_three: bool


BENCHMARK_CASES = (
    BenchmarkCase(
        number=1,
        query="Thời gian bảo hành là bao lâu?",
        expected_doc_id="warranty-buyer-shopee",
        expected_evidence="20 đến 45 ngày làm việc",
        metadata_filter={"audience": "buyer"},
    ),
    BenchmarkCase(
        number=2,
        query="Trong mô hình FBT, nếu hàng lỗi không đủ điều kiện nhập kho, Nhà Bán có bao lâu để rút hàng?",
        expected_doc_id="warranty-seller-fbt-tiki",
        expected_evidence="32 ngày làm việc",
    ),
    BenchmarkCase(
        number=3,
        query="Theo mô hình Dropship, khi từ chối xử lý bảo hành, Nhà Bán phải cung cấp bằng chứng trong bao lâu?",
        expected_doc_id="warranty-seller-dropship-tiki",
        expected_evidence="02 ngày làm việc",
    ),
    BenchmarkCase(
        number=4,
        query="Nhà Bán cần lưu video đóng gói hàng hóa tối thiểu bao lâu?",
        expected_doc_id="warranty-seller-general-tiki",
        expected_evidence="45 ngày",
    ),
    BenchmarkCase(
        number=5,
        query="Theo mô hình SD, Tiki có thể xử lý những phương án nào sau khi có kết quả xác minh?",
        expected_doc_id="warranty-seller-sd-tiki",
        expected_evidence=(
            "Đồng ý yêu cầu hoàn tiền",
            "Đồng ý yêu cầu đổi mới",
            "Đồng ý yêu cầu bảo hành",
            "Từ chối yêu cầu của khách hàng",
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


def evaluate_cases(store: EmbeddingStore, cases: list[BenchmarkCase] | tuple[BenchmarkCase, ...]) -> list[BenchmarkResult]:
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
        evaluations.append(
            BenchmarkResult(
                case=case,
                results=results,
                unfiltered_results=unfiltered_results,
                unfiltered_relevant_in_top_three=unfiltered_relevant,
                relevant_in_top_three=relevant,
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
        for index, result in enumerate(evaluation.results, start=1):
            preview = result["content"].replace("\n", " ")[:160]
            print(
                f"    {index}. {result['metadata'].get('doc_id')} "
                f"score={result['score']:.3f} | {preview}"
            )
        print(f"  Có evidence đúng trong top-3: {'Có' if evaluation.relevant_in_top_three else 'Không'}")


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
    store = EmbeddingStore(collection_name=f"warranty_{args.strategy}", embedding_fn=embedder)
    store.add_documents(chunks)

    print(f"Strategy: {args.strategy}; documents: {len(documents)}; chunks: {len(chunks)}")
    _print_results(evaluate_cases(store, BENCHMARK_CASES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
