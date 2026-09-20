from benchmark import BenchmarkCase, BENCHMARK_CASES, chunk_documents, evaluate_cases, load_policy_documents
from src import Document, EmbeddingStore, HeadingSectionChunker, _mock_embed


class StaticAgent:
    def __init__(self, answer: str) -> None:
        self.answer_text = answer

    def answer(self, question: str, top_k: int = 3, metadata_filter: dict | None = None) -> str:
        return self.answer_text


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
            content=(
                "## Quy trình FBT\nNhà Bán cần rút hàng trong 32 ngày làm việc "
                "kể từ khi phiếu được tạo."
            ),
            metadata={
                "doc_id": "warranty-seller-fbt-tiki",
                "audience": "seller",
                "fulfillment_model": "fbt",
            },
        )
    ]
    store = EmbeddingStore(collection_name="benchmark", embedding_fn=_mock_embed)
    store.add_documents(documents)

    result = evaluate_cases(store, [BENCHMARK_CASES[2]])[0]

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
        gold_answer="20 ngày",
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
        gold_answer="Hoàn tiền và đổi mới",
        expected_doc_id="sd",
        expected_evidence=("hoàn tiền", "đổi mới"),
    )

    result = evaluate_cases(store, [case])[0]

    assert result.relevant_in_top_three is False


def test_evaluate_cases_awards_two_points_for_top_one_and_correct_agent_answer():
    vectors = {
        "Câu hỏi FBT": [1.0],
        "Gold evidence 32 ngày làm việc": [2.0],
    }
    store = EmbeddingStore(collection_name="score_top_one", embedding_fn=lambda text: vectors[text])
    store.add_documents(
        [
            Document(
                "gold",
                "Gold evidence 32 ngày làm việc",
                {"doc_id": "gold", "audience": "seller", "fulfillment_model": "fbt"},
            )
        ]
    )
    case = BenchmarkCase(
        number=3,
        query="Câu hỏi FBT",
        gold_answer="32 ngày làm việc",
        expected_doc_id="gold",
        expected_evidence="32 ngày làm việc",
        metadata_filter={"audience": "seller", "fulfillment_model": "fbt"},
        answer_requirements=(("32 ngày làm việc",),),
    )

    result = evaluate_cases(store, [case], agent=StaticAgent("Nhà Bán có 32 ngày làm việc."))[0]

    assert result.gold_rank == 1
    assert result.agent_answer_correct is True
    assert result.points == 2


def test_evaluate_cases_awards_one_point_for_gold_at_rank_two():
    vectors = {
        "Câu hỏi": [1.0],
        "Nội dung nhiễu": [2.0],
        "Gold evidence 02 ngày làm việc": [1.0],
    }
    store = EmbeddingStore(collection_name="score_rank_two", embedding_fn=lambda text: vectors[text])
    store.add_documents(
        [
            Document("noise", "Nội dung nhiễu", {"doc_id": "noise", "audience": "seller"}),
            Document(
                "gold",
                "Gold evidence 02 ngày làm việc",
                {"doc_id": "gold", "audience": "seller"},
            ),
        ]
    )
    case = BenchmarkCase(
        number=2,
        query="Câu hỏi",
        gold_answer="02 ngày làm việc",
        expected_doc_id="gold",
        expected_evidence="02 ngày làm việc",
        metadata_filter={"audience": "seller"},
        answer_requirements=(("02 ngày làm việc", "2 ngày làm việc"),),
    )

    result = evaluate_cases(store, [case], agent=StaticAgent("Thời hạn là 2 ngày làm việc."))[0]

    assert result.gold_rank == 2
    assert result.agent_answer_correct is True
    assert result.points == 1
