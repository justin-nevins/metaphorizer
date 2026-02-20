from typing import Protocol, runtime_checkable

from app.schemas.llm import LLMRequest, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    async def complete_structured(
        self,
        request: LLMRequest,
        tool_name: str,
        tool_schema: dict,
    ) -> dict: ...


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        from app.services.claude_provider import ClaudeProvider
        _provider = ClaudeProvider()
    return _provider
