import json

import anthropic

from app.config import settings
from app.schemas.llm import LLMRequest, LLMResponse


class ClaudeProvider:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system:
            kwargs["system"] = request.system

        response = await self.client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )

    async def complete_structured(
        self,
        request: LLMRequest,
        tool_name: str,
        tool_schema: dict,
    ) -> dict:
        tools = [{
            "name": tool_name,
            "description": f"Record the {tool_name} results",
            "input_schema": tool_schema,
        }]

        kwargs = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}],
            "tools": tools,
            "tool_choice": {"type": "tool", "name": tool_name},
        }
        if request.system:
            kwargs["system"] = request.system

        response = await self.client.messages.create(**kwargs)

        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input

        raise ValueError(f"No tool use block found for {tool_name}")
