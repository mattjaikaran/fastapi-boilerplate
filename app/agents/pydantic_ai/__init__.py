"""Pydantic AI agents, served by the ``agents`` extra."""

from app.agents.pydantic_ai.config import build_model
from app.agents.pydantic_ai.example_agent import ArticleSummary, get_agent

__all__ = ["ArticleSummary", "build_model", "get_agent"]
