"""Example LangGraph: draft an answer, review it, retry when needed.

``build_graph`` compiles the graph; nothing is compiled at import time, so
importing this module needs no API key and no database connection.
"""

from typing import Annotated, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

MAX_DRAFTS = 2


class ExampleState(TypedDict):
    """State carried between the graph's nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    drafts: int
    approved: bool


def _model() -> ChatAnthropic:
    """Build the chat model per call so import stays key-free."""
    from app.config.settings import settings

    return ChatAnthropic(
        model=settings.AGENT_DEFAULT_MODEL,
        timeout=settings.AGENT_TIMEOUT_SECONDS,
    )


async def draft(state: ExampleState) -> dict[str, object]:
    """Ask Claude for a draft (or a revision) of the answer."""
    response = await _model().ainvoke(state["messages"])
    return {"messages": [response], "drafts": state["drafts"] + 1}


def review(state: ExampleState) -> dict[str, object]:
    """Approve a draft with content once the review budget is spent."""
    text = state["messages"][-1].text
    approved = bool(text.strip()) and (len(text) >= 40 or state["drafts"] >= MAX_DRAFTS)
    return {"approved": approved}


def route(state: ExampleState) -> Literal["draft", "end"]:
    """Send the run back to drafting or finish it."""
    if state["approved"] or state["drafts"] >= MAX_DRAFTS:
        return "end"
    return "draft"


def build_graph(
    checkpointer: BaseCheckpointSaver[str] | None = None,
) -> CompiledStateGraph[ExampleState, None, ExampleState, ExampleState]:
    """Compile the example graph.

    Pass a checkpointer (see ``config.postgres_checkpointer``) to persist
    state per ``thread_id``.
    """
    graph = StateGraph(ExampleState)
    graph.add_node("draft", draft)
    graph.add_node("review", review)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "review")
    graph.add_conditional_edges("review", route, {"draft": "draft", "end": END})
    return graph.compile(checkpointer=checkpointer)
