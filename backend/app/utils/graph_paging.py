"""Graphiti Graph pagination utilities.

Graphiti's EntityNode/EntityEdge classes provide get_by_group_ids()
with UUID cursor pagination — same pattern as Zep Cloud.
This module wraps those calls with retry logic and async-to-sync bridging.
"""

from __future__ import annotations

import time
from typing import Any

from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge

from .graphiti_client import run_async
from .logger import get_logger

logger = get_logger('mirofish.graph_paging')

_DEFAULT_PAGE_SIZE = 100
_MAX_NODES = 2000
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY = 2.0  # seconds, doubles each retry


def _with_retry(
    func,
    *args,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY,
    description: str = "operation",
    **kwargs,
) -> Any:
    """Execute an async function with exponential backoff retry."""
    last_exception: Exception | None = None
    delay = retry_delay

    for attempt in range(max_retries):
        try:
            return run_async(func(*args, **kwargs))
        except (ConnectionError, TimeoutError, OSError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(
                    f"{description} attempt {attempt + 1} failed: {str(e)[:100]}, retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(f"{description} failed after {max_retries} attempts: {str(e)}")

    assert last_exception is not None
    raise last_exception


def fetch_all_nodes(
    graphiti: Graphiti,
    group_id: str,
    page_size: int = _DEFAULT_PAGE_SIZE,
    max_items: int = _MAX_NODES,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY,
) -> list[EntityNode]:
    """Fetch all entity nodes for a group_id with cursor-based pagination."""
    all_nodes: list[EntityNode] = []
    cursor: str | None = None
    page_num = 0

    while True:
        kwargs: dict[str, Any] = {"limit": page_size}
        if cursor is not None:
            kwargs["uuid_cursor"] = cursor

        page_num += 1
        batch = _with_retry(
            EntityNode.get_by_group_ids,
            graphiti.driver,
            [group_id],
            max_retries=max_retries,
            retry_delay=retry_delay,
            description=f"fetch nodes page {page_num} (group={group_id})",
            **kwargs,
        )
        if not batch:
            break

        all_nodes.extend(batch)
        if len(all_nodes) >= max_items:
            all_nodes = all_nodes[:max_items]
            logger.warning(f"Node count reached limit ({max_items}), stopping pagination for group {group_id}")
            break
        if len(batch) < page_size:
            break

        cursor = batch[-1].uuid
        if cursor is None:
            logger.warning(f"Node missing uuid field, stopping pagination at {len(all_nodes)} nodes")
            break

    return all_nodes


def fetch_all_edges(
    graphiti: Graphiti,
    group_id: str,
    page_size: int = _DEFAULT_PAGE_SIZE,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY,
) -> list[EntityEdge]:
    """Fetch all entity edges for a group_id with cursor-based pagination."""
    all_edges: list[EntityEdge] = []
    cursor: str | None = None
    page_num = 0

    while True:
        kwargs: dict[str, Any] = {"limit": page_size}
        if cursor is not None:
            kwargs["uuid_cursor"] = cursor

        page_num += 1
        batch = _with_retry(
            EntityEdge.get_by_group_ids,
            graphiti.driver,
            [group_id],
            max_retries=max_retries,
            retry_delay=retry_delay,
            description=f"fetch edges page {page_num} (group={group_id})",
            **kwargs,
        )
        if not batch:
            break

        all_edges.extend(batch)
        if len(batch) < page_size:
            break

        cursor = batch[-1].uuid
        if cursor is None:
            logger.warning(f"Edge missing uuid field, stopping pagination at {len(all_edges)} edges")
            break

    return all_edges
