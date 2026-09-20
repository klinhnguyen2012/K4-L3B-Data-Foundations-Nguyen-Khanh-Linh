from types import SimpleNamespace

from src.llm import NvidiaChatLLM


class FakeChatCompletions:
    def __init__(self) -> None:
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Câu trả lời từ context [1]."))]
        )


class FakeNvidiaChatClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeChatCompletions())


def test_nvidia_chat_llm_sends_prompt_to_configured_model():
    client = FakeNvidiaChatClient()
    llm = NvidiaChatLLM(model_name="openai/gpt-oss-20b", client=client)

    answer = llm("Context và câu hỏi")

    assert answer == "Câu trả lời từ context [1]."
    assert client.chat.completions.request == {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": "Context và câu hỏi"}],
        "temperature": 0.0,
        "max_tokens": 1024,
        "reasoning_effort": "low",
    }
