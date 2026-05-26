from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.ai.schemas import ChatRequest, ChatResponse, StructuredRequest, StructuredResponse
from app.api.auth.dependencies import CurrentUser
from app.core.rate_limit import limiter
from app.services.ai.anthropic_client import AnthropicService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    _: CurrentUser,
) -> ChatResponse:
    try:
        messages = [{"role": m.role, "content": m.content} for m in body.messages]
        content = await AnthropicService.chat_async(
            messages=messages,
            model=body.model,
            max_tokens=body.max_tokens,
            system=body.system,
        )
        return ChatResponse(content=content, model=body.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/structured", response_model=StructuredResponse)
@limiter.limit("10/minute")
async def structured_chat(
    request: Request,
    body: StructuredRequest,
    _: CurrentUser,
) -> StructuredResponse:
    """Chat with structured JSON output validated against a provided JSON Schema."""
    from pydantic import create_model

    try:
        # Build a dynamic Pydantic model from the provided schema so we can
        # validate the output without callers needing to register their own types.
        DynamicModel = _schema_to_model(body.output_schema)
        messages = [{"role": m.role, "content": m.content} for m in body.messages]
        result = await AnthropicService.structured_output(
            messages=messages,
            output_schema=DynamicModel,
            model=body.model,
            max_tokens=body.max_tokens,
            system=body.system,
        )
        return StructuredResponse(result=result.model_dump(), model=body.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/stream")
@limiter.limit("10/minute")
async def stream_chat(
    request: Request,
    body: ChatRequest,
    _: CurrentUser,
) -> StreamingResponse:
    """Stream chat completion as Server-Sent Events."""

    async def event_generator():
        try:
            messages = [{"role": m.role, "content": m.content} for m in body.messages]
            async for chunk in AnthropicService.stream_async(
                messages=messages,
                model=body.model,
                max_tokens=body.max_tokens,
                system=body.system,
            ):
                yield f"data: {chunk}\n\n"
        except RuntimeError as exc:
            yield f"event: error\ndata: {exc}\n\n"
        finally:
            yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _schema_to_model(schema: dict):
    """Create a minimal Pydantic model from a JSON Schema dict for output validation."""
    from pydantic import create_model as pydantic_create_model

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_definitions: dict = {}
    for name, prop in properties.items():
        python_type = _json_type_to_python(prop.get("type", "string"))
        if name in required:
            field_definitions[name] = (python_type, ...)
        else:
            field_definitions[name] = (python_type | None, None)

    return pydantic_create_model("DynamicOutput", **field_definitions)


def _json_type_to_python(json_type: str):
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, str)
