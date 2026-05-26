from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    system: str | None = None
    model: str = "claude-sonnet-4-6"
    max_tokens: int = Field(default=1024, ge=1, le=8192)


class ChatResponse(BaseModel):
    content: str
    model: str


class StructuredRequest(BaseModel):
    messages: list[ChatMessage]
    system: str | None = None
    model: str = "claude-sonnet-4-6"
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    output_schema: dict = Field(..., description="JSON Schema for the expected output")


class StructuredResponse(BaseModel):
    result: dict
    model: str
