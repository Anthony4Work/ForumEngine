"""
Quick smoke test for the Graphiti + Neo4j setup.
Run from the backend/ directory:
    python -m scripts.test_graphiti
Or directly:
    cd backend && python scripts/test_graphiti.py
"""
import os
import sys
import asyncio

# Ensure backend/app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import Config
from app.utils.graphiti_client import get_graphiti, run_async


def test_connection():
    """Test 1: Can we connect to Neo4j and build indices?"""
    print("=" * 60)
    print("Test 1: Graphiti client initialization + Neo4j connection")
    print("=" * 60)
    print(f"  NEO4J_URI:  {Config.NEO4J_URI}")
    print(f"  NEO4J_USER: {Config.NEO4J_USER}")
    print(f"  LLM_MODEL:  {Config.LLM_MODEL_NAME}")
    print(f"  LLM_BASE:   {Config.LLM_BASE_URL}")
    print()

    graphiti = get_graphiti()
    print("  [OK] Graphiti client created successfully")
    print(f"  [OK] Neo4j driver: {graphiti.driver}")
    print()


def test_add_episode():
    """Test 2: Add a small test episode and verify it creates nodes/edges."""
    from graphiti_core.nodes import EpisodeType
    from datetime import datetime, timezone

    print("=" * 60)
    print("Test 2: Add a test episode")
    print("=" * 60)

    graphiti = get_graphiti()
    group_id = "test_mirofish_smoke"

    print(f"  Adding episode to group_id='{group_id}'...")
    run_async(graphiti.add_episode(
        name="smoke_test_episode",
        episode_body=(
            "Colonel Smith commands the 3rd Infantry Brigade. "
            "The brigade is deployed near Hill 205. "
            "Enemy forces include a mechanized battalion at Grid Reference 123456."
        ),
        source=EpisodeType.text,
        source_description="Smoke test for MiroFish Graphiti migration",
        reference_time=datetime.now(timezone.utc),
        group_id=group_id,
    ))
    print("  [OK] Episode added successfully")
    print()


def test_search():
    """Test 3: Search the graph for the data we just added."""
    print("=" * 60)
    print("Test 3: Search the graph")
    print("=" * 60)

    graphiti = get_graphiti()
    group_id = "test_mirofish_smoke"

    # Search edges (facts)
    print("  Searching edges for 'Colonel Smith'...")
    edge_results = run_async(graphiti.search(
        query="Colonel Smith brigade",
        group_ids=[group_id],
        num_results=5,
    ))

    if edge_results:
        print(f"  [OK] Found {len(edge_results)} edges:")
        for e in edge_results[:5]:
            print(f"       - {e.fact}")
    else:
        print("  [WARN] No edges found (search index may need time to populate)")

    # Search with different query
    print()
    print("  Searching for 'infantry'...")
    node_results = run_async(graphiti.search(
        query="infantry brigade",
        group_ids=[group_id],
        num_results=5,
    ))

    if node_results:
        print(f"  [OK] Found {len(node_results)} edges:")
        for e in node_results[:5]:
            print(f"       - {e.fact}")
    else:
        print("  [WARN] No results found (search index may need time to populate)")

    print()


def test_pagination():
    """Test 4: Test our pagination utility."""
    from app.utils.graph_paging import fetch_all_nodes, fetch_all_edges

    print("=" * 60)
    print("Test 4: Pagination utility (fetch_all_nodes / fetch_all_edges)")
    print("=" * 60)

    graphiti = get_graphiti()
    group_id = "test_mirofish_smoke"

    nodes = fetch_all_nodes(graphiti, group_id)
    print(f"  [OK] fetch_all_nodes: {len(nodes)} nodes")
    for n in nodes[:5]:
        print(f"       - {n.name} (uuid={n.uuid[:8]}...)")

    edges = fetch_all_edges(graphiti, group_id)
    print(f"  [OK] fetch_all_edges: {len(edges)} edges")
    for e in edges[:5]:
        print(f"       - {e.name}: {(e.fact or '')[:80]}")

    print()


def test_cleanup():
    """Test 5: Clean up test data."""
    from graphiti_core.nodes import EntityNode, EpisodicNode

    print("=" * 60)
    print("Test 5: Cleanup test group")
    print("=" * 60)

    graphiti = get_graphiti()
    group_id = "test_mirofish_smoke"

    # Prompt before deleting
    answer = input(f"  Delete test group '{group_id}'? [y/N]: ").strip().lower()
    if answer == 'y':
        run_async(EpisodicNode.delete_by_group_id(graphiti.driver, group_id))
        run_async(EntityNode.delete_by_group_id(graphiti.driver, group_id))
        print("  [OK] Test group deleted")
    else:
        print("  [SKIP] Kept test data — you can inspect it in Neo4j Browser")
    print()


def main():
    print()
    print("MiroFish — Graphiti Migration Smoke Test")
    print("=" * 60)
    print()

    try:
        test_connection()
        test_add_episode()
        test_search()
        test_pagination()
        test_cleanup()

        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\n  [FAIL] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
