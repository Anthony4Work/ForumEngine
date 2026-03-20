"""
COA to OASIS Converter
Transforms a military COA decision into public-facing events and initial posts
for the OASIS social simulation feedback loop.

Uses an LLM call to:
1. Transform the COA into a public announcement/event
2. Generate 2-3 initial posts from different perspectives
3. Generate a scenario_injection for each OASIS agent persona
"""

import json
from typing import Dict, Any, List, Optional

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.coa_converter')


COA_CONVERSION_PROMPT = """You are converting a military Course of Action (COA) decision into public-facing events for a social media simulation.

The simulation will model how local populations react to military operations on social media (Reddit-style forum).

## COA Decision
{coa_description}

## Commander's Intent
{commander_intent}

## Mission Statement
{mission_statement}

## Phase Summaries
{phase_summaries}

Generate a JSON response with:

1. "public_announcement": A press release / official announcement about the operation (200-300 words). Should be written as a government/military public affairs release — factual, measured tone.

2. "news_article": A short news article reporting on the announcement (150-200 words). Should read like a wire service dispatch — neutral but includes context.

3. "rumor_post": A social media post from a concerned local citizen who has heard rumors about what's happening (100-150 words). Should be informal, worried, speculative.

4. "scenario_injection": A 2-3 sentence summary that will be injected into every agent's persona to give them awareness of the situation. Write in second person ("You have heard that...").

5. "key_topics": List of 3-5 topic tags that agents might discuss (e.g., "humanitarian corridor", "military checkpoint", "civilian displacement")

Respond with valid JSON only."""


class COAToOASISConverter:
    """Converts a COA decision into OASIS simulation seed content."""

    def __init__(self, openai_client: Optional[OpenAI] = None):
        config = Config()
        self.openai_client = openai_client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.llm_model = config.LLM_MODEL_NAME

    def convert(self, coa_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a COA decision (from coa_decision.json) into OASIS seed content.

        Args:
            coa_decision: Dict with selected_coa, commander_intent, phase_summaries, etc.

        Returns:
            Dict with public_announcement, news_article, rumor_post, scenario_injection, key_topics,
            and initial_posts (formatted for OASIS).
        """
        selected = coa_decision.get("selected_coa", {})
        phase_sums = coa_decision.get("phase_summaries", {})

        # Format phase summaries
        phase_text = "\n".join([
            f"Phase {pid}: {ps.get('phase_name', '')}: {ps.get('summary', '')[:300]}"
            for pid, ps in sorted(phase_sums.items())
        ])

        try:
            prompt = COA_CONVERSION_PROMPT.format(
                coa_description=selected.get("description", "No description")[:1000],
                commander_intent=coa_decision.get("commander_intent", "")[:500],
                mission_statement=coa_decision.get("mission_statement", "")[:500],
                phase_summaries=phase_text[:3000],
            )

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a military-civilian communications expert. Convert military plans into realistic public-facing content. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
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
            logger.error(f"COA conversion failed: {e}")
            data = self._fallback_conversion(selected)

        # Format initial posts for OASIS
        initial_posts = []

        if data.get("public_announcement"):
            initial_posts.append({
                "author": "OfficialMilitary_PA",
                "title": "Official Statement: Military Operations Update",
                "content": data["public_announcement"],
                "post_type": "official",
            })

        if data.get("news_article"):
            initial_posts.append({
                "author": "LocalNewsWire",
                "title": "Breaking: Military announces new operations in region",
                "content": data["news_article"],
                "post_type": "news",
            })

        if data.get("rumor_post"):
            initial_posts.append({
                "author": "concerned_local_42",
                "title": "Has anyone heard about what's happening?",
                "content": data["rumor_post"],
                "post_type": "rumor",
            })

        result = {
            "public_announcement": data.get("public_announcement", ""),
            "news_article": data.get("news_article", ""),
            "rumor_post": data.get("rumor_post", ""),
            "scenario_injection": data.get("scenario_injection", ""),
            "key_topics": data.get("key_topics", []),
            "initial_posts": initial_posts,
            "source_coa": {
                "coa_id": selected.get("coa_id"),
                "coa_name": selected.get("coa_name"),
            },
        }

        logger.info(f"COA converted: {len(initial_posts)} initial posts, "
                     f"{len(result['key_topics'])} topics")
        return result

    @staticmethod
    def _fallback_conversion(selected: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback if LLM conversion fails."""
        desc = selected.get("description", "Military operation in progress")[:500]
        return {
            "public_announcement": f"Official statement: A military operation has been planned. Details: {desc}",
            "news_article": f"Military sources confirm new operations: {desc}",
            "rumor_post": "I heard the military is doing something big in our area. Anyone know what's going on?",
            "scenario_injection": "You have heard that the military is conducting new operations in your area. People are talking about it.",
            "key_topics": ["military operations", "local impact", "civilian safety"],
        }

    @staticmethod
    def save_conversion(result: Dict[str, Any], output_path: str):
        """Save conversion result to JSON."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"COA conversion saved to {output_path}")
