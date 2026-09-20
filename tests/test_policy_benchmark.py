from benchmark import BenchmarkCase, BENCHMARK_CASES, chunk_documents, evaluate_cases, load_policy_documents
from src import Document, EmbeddingStore, HeadingSectionChunker, _mock_embed


def test_load_policy_documents_reads_all_required_metadata():
    documents = load_policy_documents("data/warranty-policy")

    assert len(documents) == 5
    assert {document.metadata["audience"] for document in documents} == {"buyer", "seller"}
    for document in documents:
        assert document.metadata["source_url"]
        assert document.metadata["retrieved_at"]
        assert document.metadata["document_version"]


def test_chunk_documents_keeps_policy_metadata_on_every_chunk():
    document = Document(
        id="policy",
        content="# Chính sách\n\n## Điều kiện\nSản phẩm phải còn trong thời hạn bảo hành.",
        metadata={"doc_id": "policy", "audience": "buyer"},
    )

    chunks = chunk_documents([document], HeadingSectionChunker(chunk_size=500))

    assert len(chunks) == 1
    assert chunks[0].metadata["doc_id"] == "policy"
    assert chunks[0].metadata["audience"] == "buyer"
    assert chunks[0].metadata["chunk_index"] == 0
    assert "## Điều kiện" in chunks[0].content


def test_evaluate_cases_marks_expected_evidence_in_top_three_as_relevant():
    documents = [
        Document(
            id="fbt-0",
            content="## Quy trình FBT\nNhà Bán cần rút hàng trong 32 ngày làm việc.",
            metadata={"doc_id": "warranty-seller-fbt-tiki", "audience": "seller"},
        )
    ]
    store = EmbeddingStore(collection_name="benchmark", embedding_fn=_mock_embed)
    store.add_documents(documents)

    result = evaluate_cases(store, [BENCHMARK_CASES[1]])[0]

    assert result.relevant_in_top_three is True


def test_evaluate_cases_shows_when_a_metadata_filter_recovers_missing_evidence():
    vectors = {
        "Câu hỏi thời hạn": [1.0],
        "seller one": [4.0],
        "seller two": [3.0],
        "seller three": [2.0],
        "buyer evidence 20 ngày": [1.0],
    }
    store = EmbeddingStore(
        collection_name="filter_benchmark",
        embedding_fn=lambda text: vectors[text],
    )
    store.add_documents(
        [
            Document(f"seller-{index}", text, {"doc_id": f"seller-{index}", "audience": "seller"})
            for index, text in enumerate(("seller one", "seller two", "seller three"), start=1)
        ]
        + [
            Document(
                "buyer-1",
                "buyer evidence 20 ngày",
                {"doc_id": "buyer-1", "audience": "buyer"},
            )
        ]
    )
    case = BenchmarkCase(
        number=1,
        query="Câu hỏi thời hạn",
        expected_doc_id="buyer-1",
        expected_evidence="20 ngày",
        metadata_filter={"audience": "buyer"},
    )

    result = evaluate_cases(store, [case])[0]

    assert result.unfiltered_relevant_in_top_three is False
    assert result.relevant_in_top_three is True


def test_evaluate_cases_requires_all_evidence_for_a_list_answer():
    store = EmbeddingStore(collection_name="list_benchmark", embedding_fn=_mock_embed)
    store.add_documents(
        [
            Document(
                "sd-0",
                "Tiki đồng ý yêu cầu hoàn tiền cho khách hàng.",
                {"doc_id": "sd", "audience": "seller"},
            )
        ]
    )
    case = BenchmarkCase(
        number=5,
        query="Các phương án xử lý là gì?",
        expected_doc_id="sd",
        expected_evidence=("hoàn tiền", "đổi mới"),
    )

    result = evaluate_cases(store, [case])[0]

    assert result.relevant_in_top_three is False
