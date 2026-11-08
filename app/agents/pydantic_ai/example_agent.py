"""Example Pydantic AI agent with typed output and one tool."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.pydantic_ai.config import build_model


class WordStats(BaseModel):
    """Result of the ``word_stats`` tool."""

    words: int
    characters: int


class ArticleSummary(BaseModel):
    """Typed output of the example agent."""

    headline: str = Field(description="One-line headline for the article.")
    summary: str = Field(description="Two or three sentence summary.")
    key_points: list[str] = Field(
        min_length=1, description="The most important points, one per item."
    )


_agent: Agent[None, ArticleSummary] | None = None


def _count_words(text: str) -> WordStats:
    return WordStats(words=len(text.split()), characters=len(text))


def get_agent() -> Agent[None, ArticleSummary]:
    """Build the example agent on first use and reuse it afterwards."""
    global _agent
    if _agent is not None:
        return _agent

    agent: Agent[None, ArticleSummary] = Agent(
        build_model(),
        output_type=ArticleSummary,
        instructions=(
            "Summarize the article the user sends. Call word_stats on the "
            "article first, then return a headline, a short summary and key points."
        ),
    )

    @agent.tool_plain
    def word_stats(text: str) -> WordStats:
        """Count the words and characters in the article."""
        return _count_words(text)

    _agent = agent
    return agent
