from types import SimpleNamespace

from src.embeddings import NvidiaEmbedder


class FakeEmbeddingsClient:
    def __init__(self) -> None:
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.25, -0.75])])


class FakeNvidiaClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsClient()


def test_nvidia_embedder_uses_configured_model_and_returns_float_vector():
    client = FakeNvidiaClient()
    embedder = NvidiaEmbedder(
        model_name="nvidia/nemotron-3-embed-1b",
        api_key="test-key",
        client=client,
    )

    result = embedder("bảo hành sản phẩm")

    assert result == [0.25, -0.75]
    assert client.embeddings.request == {
        "model": "nvidia/nemotron-3-embed-1b",
        "input": "bảo hành sản phẩm",
        "encoding_format": "float",
    }
