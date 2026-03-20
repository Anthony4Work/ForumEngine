"""
Social Reaction Summarizer
Reads the OASIS SQLite traces database and produces a structured summary
of social reactions for Phase 8 feedback.

Output format:
{
    "total_posts": 145,
    "sentiment_distribution": {"positive": 30, "neutral": 45, "negative": 25},
    "key_concerns": [...],
    "opposition_themes": [...],
    "support_themes": [...],
    "narrative_summary": "LLM-generated 500-word summary"
}
"""

import json
import os
import sqlite3
from typing import Dict, Any, List, Optional

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.social_summarizer')


NARRATIVE_PROMPT = """You are analyzing social media posts from a simulated population reacting to a military operation.

## Posts (sample of {sample_size} from {total} total):

{posts_text}

## Task
Write a structured analysis (400-500 words) covering:
1. **Overall Sentiment**: What is the dominant mood? How divided is public opinion?
2. **Key Concerns**: What specific issues worry people most?
3. **Support Themes**: What arguments do supporters use?
4. **Opposition Themes**: What arguments do critics use?
5. **Information Gaps**: What do people say they don't know or want to know?
6. **Escalation Risks**: Are there signs of potential unrest, protests, or violence?

Also extract structured data as JSON:
{{
    "sentiment_distribution": {{"positive": <pct>, "neutral": <pct>, "negative": <pct>}},
    "key_concerns": ["concern1", "concern2", ...],
    "opposition_themes": ["theme1", "theme2", ...],
    "support_themes": ["theme1", "theme2", ...],
    "escalation_risk": "low|medium|high",
    "narrative_summary": "<your 400-500 word analysis>"
}}

Respond with valid JSON only."""


class SocialReactionSummarizer:
    """Analyzes OASIS simulation output and produces a structured summary."""

    def __init__(self, openai_client: Optional[OpenAI] = None):
        config = Config()
        self.openai_client = openai_client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.llm_model = config.LLM_MODEL_NAME

    def summarize(
        self,
        traces_db_path: str,
        max_sample: int = 100,
    ) -> Dict[str, Any]:
        """
        Read OASIS traces DB and generate a structured summary.

        Args:
            traces_db_path: Path to the SQLite traces.db file.
            max_sample: Max posts to sample for LLM analysis.

        Returns:
            Structured summary dict.
        """
        if not os.path.exists(traces_db_path):
            logger.warning(f"Traces DB not found: {traces_db_path}")
            return self._empty_summary()

        posts = self._read_posts(traces_db_path)
        if not posts:
            logger.warning("No posts found in traces DB")
            return self._empty_summary()

        logger.info(f"Read {len(posts)} posts from OASIS traces")

        # Sample posts for LLM
        import random
        sample = posts if len(posts) <= max_sample else random.sample(posts, max_sample)

        # Format for LLM
        posts_text = "\n---\n".join([
            f"[{p.get('author', 'anon')}] {p.get('title', '')}\n{p.get('content', '')[:300]}"
            for p in sample
        ])

        try:
            prompt = NARRATIVE_PROMPT.format(
                sample_size=len(sample),
                total=len(posts),
                posts_text=posts_text[:8000],
            )

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a social media analyst specializing in civil-military relations. Analyze population reactions objectively. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content.strip()

            # Strip markdown fences
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            if content.startswith("json"):
                content = content[4:]

            data = json.loads(content)

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            data = {
                "sentiment_distribution": {"positive": 33, "neutral": 34, "negative": 33},
                "key_concerns": ["Unable to analyze — LLM call failed"],
                "opposition_themes": [],
                "support_themes": [],
                "escalation_risk": "unknown",
                "narrative_summary": f"Analysis failed: {str(e)[:200]}",
            }

        result = {
            "total_posts": len(posts),
            "sample_size": len(sample),
            "sentiment_distribution": data.get("sentiment_distribution", {}),
            "key_concerns": data.get("key_concerns", []),
            "opposition_themes": data.get("opposition_themes", []),
            "support_themes": data.get("support_themes", []),
            "escalation_risk": data.get("escalation_risk", "unknown"),
            "narrative_summary": data.get("narrative_summary", ""),
        }

        logger.info(f"Social summary: {result['total_posts']} posts, "
                     f"sentiment={result['sentiment_distribution']}")
        return result

    def _read_posts(self, db_path: str) -> List[Dict[str, Any]]:
        """Read posts from OASIS SQLite database."""
        posts = []
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Try common OASIS table names
            for table in ("post", "posts", "reddit_post", "tweet"):
                try:
                    cursor.execute(f"SELECT * FROM {table} ORDER BY rowid")
                    rows = cursor.fetchall()
                    if rows:
                        posts = [dict(row) for row in rows]
                        break
                except sqlite3.OperationalError:
                    continue

            conn.close()
        except Exception as e:
            logger.error(f"Failed to read traces DB: {e}")

        return posts

    @staticmethod
    def _empty_summary() -> Dict[str, Any]:
        return {
            "total_posts": 0,
            "sample_size": 0,
            "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "key_concerns": [],
            "opposition_themes": [],
            "support_themes": [],
            "escalation_risk": "unknown",
            "narrative_summary": "No social simulation data available.",
        }

    @staticmethod
    def save_summary(summary: Dict[str, Any], output_path: str):
        """Save summary to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"Social reaction summary saved to {output_path}")
