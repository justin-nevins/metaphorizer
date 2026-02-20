from pydantic import BaseModel


class LLMRequest(BaseModel):
    system: str = ""
    prompt: str
    max_tokens: int = 4096
    temperature: float = 0.3


class LLMResponse(BaseModel):
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
