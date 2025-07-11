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
        # History of the conversation exchanged with the agents
        self._conversation_history: List[dict[str, str]] = []
        # Last selected sequence of agents and the index of the last agent used
        self._agent_sequence: List[Any] = [self.story_query_agent]
        self._last_agent_index = 0

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
            return [self.story_query_agent]

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
            names = ["StoryQueryAgent"]

        selected = [mapping[name] for name in names if name in mapping]
        return selected or [self.story_query_agent]

    async def reset(self) -> None:
        """Reset conversation state."""
        self._current_agent = self.story_query_agent
        self._conversation_history.clear()
        self._agent_sequence = [self.story_query_agent]
        self._last_agent_index = 0

    def _follow_up_requested(self, text: str) -> bool:
        """Check if the assistant output asks the user for further processing."""
        prompts = [
            "would you like",
            "need more",
            "should i continue",
            "continue with",
            "more detail",
        ]
        lower = text.lower()
        return any(p in lower for p in prompts)

    def _user_declined(self, text: str) -> bool:
        """Determine if the user declined additional processing."""
        declines = ["no", "no thanks", "stop", "that's all", "cancel", "don't"]
        lower = text.lower()
        return any(d in lower for d in declines)

    async def send(self, message: str, *, context: Any | None = None, max_turns: int = 8) -> str:
        """Send a user message through the workflow and return the assistant reply."""
        self._conversation_history.append({"role": "user", "content": message})

        follow_up = False
        if len(self._conversation_history) >= 2:
            last_assistant = next(
                (m for m in reversed(self._conversation_history[:-1]) if m["role"] == "assistant"),
                None,
            )
            if last_assistant and self._follow_up_requested(last_assistant["content"]):
                if self._user_declined(message):
                    return "Okay, let me know if you need anything else."
                follow_up = True

        if follow_up:
            start_index = min(self._last_agent_index + 1, len(self._agent_sequence) - 1)
        else:
            agents = await self.choose_agents(message)
            if agents:
                self._agent_sequence = agents
            start_index = 0
            self._last_agent_index = 0

        self._build_handoffs(self._agent_sequence[start_index:])
        self._current_agent = self._agent_sequence[start_index]

        remaining_turns = max_turns
        result = None
        while remaining_turns > 0:
            result = await Runner.run(
                starting_agent=self._current_agent,
                input=self._conversation_history,
                context=context,
                max_turns=1,
            )
            remaining_turns -= 1
            self._current_agent = result.last_agent
            self._conversation_history = result.to_input_list()
            output = result.final_output_as(str)
            self._last_agent_index = self._agent_sequence.index(self._current_agent)
            if not self._follow_up_requested(output):
                break
            # Wait for the user to respond on the next send() call
            break

        self._clear_handoffs()
        return output if result else ""
