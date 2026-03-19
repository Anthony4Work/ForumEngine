"""Graphiti client factory — singleton for Neo4j-backed knowledge graph.

Uses a dedicated background event loop so the Neo4j async driver always
runs on the same loop (avoids 'Future attached to a different loop' errors).
"""
import asyncio
import threading
from typing import Any, Coroutine

from graphiti_core import Graphiti
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

from ..config import Config

_graphiti_instance: Graphiti | None = None
_lock = threading.Lock()

# Persistent event loop running in a daemon thread.
# All async Graphiti/Neo4j calls are dispatched here so they share one loop.
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Start the background event loop (once)."""
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return _loop

    _loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=_run, daemon=True, name="graphiti-loop")
    _loop_thread.start()
    return _loop


def run_async(coro: Coroutine) -> Any:
    """Execute an async coroutine on the shared Graphiti event loop.

    Safe to call from any thread (main, Flask request, background workers).
    Blocks the caller until the coroutine completes.
    """
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def get_graphiti() -> Graphiti:
    """Return a lazy-initialised singleton Graphiti client."""
    global _graphiti_instance
    if _graphiti_instance is not None:
        return _graphiti_instance

    with _lock:
        if _graphiti_instance is not None:
            return _graphiti_instance

        llm_config = LLMConfig(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            model=Config.LLM_MODEL_NAME,
        )
        llm_client = OpenAIClient(config=llm_config)

        embedder_config = OpenAIEmbedderConfig(
            api_key=Config.EMBEDDING_API_KEY,
            base_url=Config.EMBEDDING_BASE_URL,
            embedding_model=Config.EMBEDDING_MODEL,
        )
        embedder = OpenAIEmbedder(config=embedder_config)

        # Reranker needs a valid LLMConfig to avoid defaulting to OPENAI_API_KEY
        reranker = OpenAIRerankerClient(config=llm_config)

        client = Graphiti(
            uri=Config.NEO4J_URI,
            user=Config.NEO4J_USER,
            password=Config.NEO4J_PASSWORD,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=reranker,
        )
        run_async(client.build_indices_and_constraints())
        _graphiti_instance = client

    return _graphiti_instance
