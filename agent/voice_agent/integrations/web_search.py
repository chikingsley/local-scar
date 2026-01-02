"""Web search tool with DuckDuckGo + Ollama summarization.

Provides a voice-friendly web search capability that:
1. Searches DuckDuckGo (free, no API key)
2. Summarizes results with Ollama for concise voice output
3. Returns 1-3 sentence answers instead of raw search results
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import ollama

from ..config import config

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """Summarize the following search results in 1-3 sentences for voice output.
Be concise and conversational. Do not include URLs, markdown, or bullet points.
Focus on directly answering what the user would want to know.

Search query: {query}

Results:
{results}

Summary:"""


class WebSearchTool:
    """Web search via DuckDuckGo with Ollama summarization.

    Attributes:
        max_results: Maximum number of search results to fetch
        timeout: Search timeout in seconds
        model: Ollama model for summarization
    """

    def __init__(
        self,
        max_results: int = 5,
        timeout: float = 10.0,
        model: str | None = None,
    ):
        self.max_results = max_results
        self.timeout = timeout
        self.model = model or config.ollama_model

    async def search(self, query: str) -> str:
        """Search the web and return a summarized response.

        Args:
            query: Search query

        Returns:
            Voice-friendly summarized response
        """
        logger.info(f"web_search: {query}")

        try:
            raw_results = await asyncio.wait_for(
                self._do_search(query),
                timeout=self.timeout,
            )

            if not raw_results:
                return "I couldn't find any results for that search."

            return await self._summarize_results(query, raw_results)

        except asyncio.TimeoutError:
            logger.warning(f"Web search timed out for query: {query}")
            return "The search took too long. Please try a simpler query."
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return "I had trouble searching the web. Please try again."

    async def _do_search(self, query: str) -> list[dict[str, Any]]:
        """Execute DuckDuckGo search in thread pool (blocking API)."""
        from duckduckgo_search import DDGS

        def _search():
            with DDGS(timeout=self.timeout) as ddgs:
                return list(
                    ddgs.text(
                        query,
                        max_results=self.max_results,
                        safesearch="moderate",
                    )
                )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _search)

    async def _summarize_results(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> str:
        """Summarize search results with Ollama for voice-friendly output."""
        # Truncate to avoid exceeding context limits
        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")[:100]
            body = r.get("body", "")[:200]
            formatted.append(f"{i}. {title}: {body}")

        results_text = "\n".join(formatted)
        prompt = SUMMARIZE_PROMPT.format(query=query, results=results_text)

        try:
            response = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3},
                stream=False,
            )
            summary = response.get("message", {}).get("content", "").strip()
            return summary or "I found some results but couldn't summarize them."

        except Exception as e:
            logger.error(f"Summarization error: {e}")
            if results:
                return results[0].get("body", "No description available.")
            return "I had trouble processing the search results."
