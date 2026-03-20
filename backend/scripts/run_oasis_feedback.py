"""
OASIS Feedback Runner
Simplified OASIS social media simulation for testing population reaction
to a COA decision from MDMP deliberation.

Features:
- Fewer rounds (default 30 vs 144+)
- All agents active from the start (no hour-gating)
- Initial posts seeded from COA conversion
- No IPC/interview mode
- Output: oasis_feedback/traces.db + oasis_feedback/summary.json

Usage:
    python run_oasis_feedback.py --simulation-dir /path/to/sim --graph-id <graph_id>
"""

import argparse
import asyncio
import json
import os
import sys
import sqlite3
import signal
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent paths for imports
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)

from app.config import Config
from app.utils.logger import get_logger
from app.services.coa_to_oasis_converter import COAToOASISConverter
from app.services.social_reaction_summarizer import SocialReactionSummarizer

logger = get_logger('mirofish.oasis_feedback')

_shutdown = False


class OASISFeedbackRunner:
    """
    Simplified OASIS runner for COA feedback simulation.

    Runs a Reddit-style forum simulation where agents (generated from graph entities)
    react to the selected COA through posts and comments.
    """

    def __init__(
        self,
        simulation_dir: str,
        graph_id: str,
        rounds: int = 30,
        platform: str = "reddit",
    ):
        self.simulation_dir = simulation_dir
        self.graph_id = graph_id
        self.rounds = rounds
        self.platform = platform

        self.output_dir = os.path.join(simulation_dir, "oasis_feedback")
        os.makedirs(self.output_dir, exist_ok=True)

        self.traces_db = os.path.join(self.output_dir, "traces.db")

        cfg = Config()
        self.llm_model = cfg.LLM_MODEL_NAME

    def run(self):
        """Execute the full feedback pipeline."""
        global _shutdown

        logger.info(f"Starting OASIS feedback simulation: {self.simulation_dir}")

        # Step 1: Load COA decision
        coa_path = os.path.join(self.simulation_dir, "deliberation", "coa_decision.json")
        if not os.path.exists(coa_path):
            logger.error(f"COA decision not found: {coa_path}")
            return

        with open(coa_path, "r", encoding="utf-8") as f:
            coa_decision = json.load(f)

        logger.info(f"Loaded COA decision: COA-{coa_decision.get('selected_coa', {}).get('coa_id')}")

        # Step 2: Convert COA to OASIS events
        logger.info("Converting COA to OASIS events...")
        converter = COAToOASISConverter()
        conversion = converter.convert(coa_decision)

        conversion_path = os.path.join(self.output_dir, "coa_conversion.json")
        COAToOASISConverter.save_conversion(conversion, conversion_path)

        # Step 3: Load agent profiles
        agents_path = os.path.join(self.simulation_dir, "agents.json")
        if not os.path.exists(agents_path):
            logger.error(f"Agents file not found: {agents_path}")
            return

        with open(agents_path, "r", encoding="utf-8") as f:
            agents_data = json.load(f)

        all_agents = agents_data.get("agents", [])

        # Use all agents (staff get civilian observer personas, SMEs keep their personas)
        logger.info(f"Loaded {len(all_agents)} agents for social simulation")

        # Step 4: Initialize traces DB
        self._init_traces_db()

        # Step 5: Seed initial posts
        for post in conversion.get("initial_posts", []):
            self._write_post(post)

        logger.info(f"Seeded {len(conversion.get('initial_posts', []))} initial posts")

        # Step 6: Run simulation rounds
        try:
            self._check_oasis_available()
            self._run_oasis_simulation(all_agents, conversion)
        except ImportError:
            logger.warning("OASIS/CAMEL not available — running lightweight LLM-based simulation")
            asyncio.run(self._run_lightweight_simulation(all_agents, conversion))

        if _shutdown:
            logger.info("Shutdown requested — stopping simulation")
            return

        # Step 7: Summarize results
        logger.info("Generating social reaction summary...")
        summarizer = SocialReactionSummarizer()
        summary = summarizer.summarize(self.traces_db)

        summary_path = os.path.join(self.output_dir, "summary.json")
        SocialReactionSummarizer.save_summary(summary, summary_path)

        logger.info(f"OASIS feedback complete: {summary.get('total_posts', 0)} posts, "
                     f"summary saved to {summary_path}")

    def _check_oasis_available(self):
        """Check if the OASIS/CAMEL framework is importable."""
        import importlib
        importlib.import_module("oasis")

    def _run_oasis_simulation(self, agents: List[dict], conversion: Dict[str, Any]):
        """Run full OASIS simulation (requires oasis package)."""
        # This would integrate with the actual OASIS framework
        # For now, falls through to lightweight simulation
        raise ImportError("Full OASIS integration pending")

    async def _run_lightweight_simulation(
        self,
        agents: List[dict],
        conversion: Dict[str, Any],
    ):
        """Lightweight LLM-based forum simulation (fallback when OASIS not available)."""
        global _shutdown
        from openai import AsyncOpenAI

        cfg = Config()
        client = AsyncOpenAI(api_key=cfg.LLM_API_KEY, base_url=cfg.LLM_BASE_URL)
        semaphore = asyncio.Semaphore(cfg.LLM_MAX_CONCURRENT)

        scenario = conversion.get("scenario_injection", "")
        topics = conversion.get("key_topics", [])
        initial_posts = conversion.get("initial_posts", [])

        # Build post history for context
        post_history = [p.get("content", "")[:200] for p in initial_posts]

        for round_num in range(1, self.rounds + 1):
            if _shutdown:
                break

            logger.info(f"  Feedback round {round_num}/{self.rounds}")

            # Select 3-5 random agents per round
            import random
            active = random.sample(agents, min(5, len(agents)))

            tasks = []
            for agent in active:
                tasks.append(self._agent_post(
                    client, semaphore, agent, scenario, topics, post_history, round_num
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Agent post failed: {result}")
                elif result:
                    self._write_post(result)
                    post_history.append(result.get("content", "")[:200])
                    # Keep history manageable
                    if len(post_history) > 50:
                        post_history = post_history[-30:]

        logger.info(f"Lightweight simulation complete: {round_num} rounds")

    async def _agent_post(
        self,
        client,
        semaphore: asyncio.Semaphore,
        agent: dict,
        scenario: str,
        topics: List[str],
        post_history: List[str],
        round_num: int,
    ) -> Optional[Dict[str, Any]]:
        """Generate a single forum post from an agent."""
        name = agent.get("name", "Anonymous")
        persona = agent.get("persona", "A local resident.")[:1000]
        is_sme = agent.get("is_sme", False)

        role_hint = "a local resident" if is_sme else "an observer"

        system = (
            f"You are {name}, {role_hint} posting on a local online forum.\n"
            f"{persona}\n\n"
            f"Context: {scenario}\n\n"
            f"Write a short forum post (50-150 words) reacting to the situation. "
            f"Be natural, opinionated, and specific. You may agree, disagree, ask questions, "
            f"share personal experience, or express concerns."
        )

        recent = "\n".join(post_history[-10:]) if post_history else "(No posts yet)"

        user = (
            f"Recent forum posts:\n{recent}\n\n"
            f"Topics being discussed: {', '.join(topics)}\n\n"
            f"Write your forum post. Respond with JSON: "
            f'{{"title": "post title", "content": "your post"}}'
        )

        async with semaphore:
            try:
                response = await client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.9,
                    max_tokens=500,
                )

                content = response.choices[0].message.content.strip()

                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                if content.startswith("json"):
                    content = content[4:]

                data = json.loads(content)

                return {
                    "author": name,
                    "title": data.get("title", "Untitled"),
                    "content": data.get("content", ""),
                    "round": round_num,
                    "agent_id": agent.get("agent_id", 0),
                    "is_sme": is_sme,
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                logger.debug(f"Post generation failed for {name}: {e}")
                return None

    def _init_traces_db(self):
        """Initialize the SQLite traces database."""
        conn = sqlite3.connect(self.traces_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS post (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT,
                title TEXT,
                content TEXT,
                round INTEGER DEFAULT 0,
                agent_id INTEGER DEFAULT 0,
                is_sme BOOLEAN DEFAULT 0,
                post_type TEXT DEFAULT 'user',
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _write_post(self, post: Dict[str, Any]):
        """Write a post to the traces database."""
        conn = sqlite3.connect(self.traces_db)
        conn.execute(
            "INSERT INTO post (author, title, content, round, agent_id, is_sme, post_type, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                post.get("author", "unknown"),
                post.get("title", ""),
                post.get("content", ""),
                post.get("round", 0),
                post.get("agent_id", 0),
                post.get("is_sme", False),
                post.get("post_type", "user"),
                post.get("timestamp", datetime.now().isoformat()),
            ),
        )
        conn.commit()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run OASIS feedback simulation")
    parser.add_argument("--simulation-dir", required=True, help="Path to simulation data directory")
    parser.add_argument("--graph-id", required=True, help="Graph ID")
    parser.add_argument("--rounds", type=int, default=None, help="Number of simulation rounds")
    parser.add_argument("--platform", default=None, help="Platform type (reddit/twitter)")
    args = parser.parse_args()

    cfg = Config()
    rounds = args.rounds or cfg.OASIS_FEEDBACK_ROUNDS
    platform = args.platform or cfg.OASIS_FEEDBACK_PLATFORM

    runner = OASISFeedbackRunner(
        simulation_dir=args.simulation_dir,
        graph_id=args.graph_id,
        rounds=rounds,
        platform=platform,
    )

    def signal_handler(sig, frame):
        global _shutdown
        logger.info("Shutdown signal received")
        _shutdown = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    runner.run()


if __name__ == "__main__":
    main()
