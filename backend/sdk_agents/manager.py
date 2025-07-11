"""Agent workflow manager for CineGraph SDK agents."""
from __future__ import annotations

import json
import os
from typing import Any, List

from openai import AsyncOpenAI

from agents import Runner, handoff

from .story_query_agent import StoryQueryAgent
from .inconsistency_explainer_agent import InconsistencyExplainerAgent
from .story_debugging_agent import StoryDebuggingAgent
from .results_interpreter_agent import ResultsInterpreterAgent
from .character_analysis_agent import CharacterAnalysisAgent
from .story_input_agent import StoryInputAgent
from .rpg_maker_agent import RPGMakerAgent
from .tutorial_agent import TutorialAgent


class SDKAgentManager:
    """Coordinate specialized agents with conversation handoffs."""

    def __init__(self) -> None:
        # Instantiate agents
        self.story_query_agent = StoryQueryAgent()
        self.inconsistency_explainer_agent = InconsistencyExplainerAgent()
        self.story_debugging_agent = StoryDebuggingAgent()
        self.results_interpreter_agent = ResultsInterpreterAgent()
        self.character_analysis_agent = CharacterAnalysisAgent()
        self.story_input_agent = StoryInputAgent()
        self.rpg_maker_agent = RPGMakerAgent()
        self.tutorial_agent = TutorialAgent()

        # Optional OpenAI client for routing
        api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

        # Conversation state
        self._current_agent = self.story_query_agent
        self._input_items: List[dict[str, str]] = []

    def _clear_handoffs(self) -> None:
        for agent in [
            self.story_query_agent,
            self.inconsistency_explainer_agent,
            self.story_debugging_agent,
            self.results_interpreter_agent,
            self.character_analysis_agent,
            self.story_input_agent,
            self.rpg_maker_agent,
            self.tutorial_agent,
        ]:
            agent.handoffs.clear()

    def _build_handoffs(self, agents: List[Any]) -> None:
        self._clear_handoffs()
        for current, nxt in zip(agents, agents[1:]):
            current.handoffs.append(handoff(nxt))

    async def choose_agents(self, message: str) -> List[Any]:
        """Use an LLM to select the agent sequence for a message."""
        mapping = {
            "StoryQueryAgent": self.story_query_agent,
            "InconsistencyExplainerAgent": self.inconsistency_explainer_agent,
            "StoryDebuggingAgent": self.story_debugging_agent,
            "ResultsInterpreterAgent": self.results_interpreter_agent,
            "CharacterAnalysisAgent": self.character_analysis_agent,
            "StoryInputAgent": self.story_input_agent,
            "RPGMakerAgent": self.rpg_maker_agent,
            "TutorialAgent": self.tutorial_agent,
        }

        if self.openai_client is None:
            return [
                self.story_query_agent,
                self.inconsistency_explainer_agent,
                self.story_debugging_agent,
                self.results_interpreter_agent,
            ]

        system = (
            "You are the SDK agent router. Given a user message, decide which "
            "of the following agents should handle the request and in what "
            "order: " + ", ".join(mapping.keys()) + ". Return a JSON array of "
            "agent class names in execution order."
        )
        resp = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": message}],
            max_tokens=64,
            temperature=0,
        )
        content = resp.choices[0].message.content.strip()
        try:
            names = json.loads(content)
        except Exception:
            names = ["StoryQueryAgent", "ResultsInterpreterAgent"]

        selected = [mapping[name] for name in names if name in mapping]
        return selected or [self.story_query_agent]

    async def reset(self) -> None:
        """Reset conversation state."""
        self._current_agent = self.story_query_agent
        self._input_items.clear()

    async def send(self, message: str, *, context: Any | None = None, max_turns: int = 8) -> str:
        """Send a user message through the workflow and return the assistant reply."""
        self._input_items.append({"role": "user", "content": message})
        agents = await self.choose_agents(message)
        if agents:
            self._build_handoffs(agents)
            self._current_agent = agents[0]
        result = await Runner.run(
            starting_agent=self._current_agent,
            input=self._input_items,
            context=context,
            max_turns=max_turns,
        )
        self._current_agent = result.last_agent
        self._input_items = result.to_input_list()
        self._clear_handoffs()
        return result.final_output_as(str)
