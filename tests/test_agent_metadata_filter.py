from src import Document, EmbeddingStore, KnowledgeBaseAgent, _mock_embed


def test_agent_answer_uses_metadata_filter_before_building_context():
    store = EmbeddingStore(collection_name="agent_filter", embedding_fn=_mock_embed)
    store.add_documents(
        [
            Document(
                "buyer-policy",
                "BUYER_CONTEXT: Người mua cần mã đơn hàng.",
                {"audience": "buyer"},
            ),
            Document(
                "seller-policy",
                "SELLER_CONTEXT: Nhà Bán cần phản hồi trên Seller Center.",
                {"audience": "seller"},
            ),
        ]
    )
    captured_prompt = ""

    def capture_prompt(prompt: str) -> str:
        nonlocal captured_prompt
        captured_prompt = prompt
        return "Câu trả lời"

    agent = KnowledgeBaseAgent(store=store, llm_fn=capture_prompt)

    answer = agent.answer(
        "Cần chuẩn bị gì?",
        top_k=3,
        metadata_filter={"audience": "buyer"},
    )

    assert answer == "Câu trả lời"
    assert "BUYER_CONTEXT" in captured_prompt
    assert "SELLER_CONTEXT" not in captured_prompt
