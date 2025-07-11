"""Agent workflow manager for CineGraph SDK agents."""
from __future__ import annotations

from typing import Any, List

from agents import Runner, handoff

from .story_query_agent import StoryQueryAgent
from .inconsistency_explainer_agent import InconsistencyExplainerAgent
from .story_debugging_agent import StoryDebuggingAgent
from .results_interpreter_agent import ResultsInterpreterAgent


class SDKAgentManager:
    """Coordinate specialized agents with conversation handoffs."""

    def __init__(self) -> None:
        # Instantiate agents
        self.story_query_agent = StoryQueryAgent()
        self.inconsistency_explainer_agent = InconsistencyExplainerAgent()
        self.story_debugging_agent = StoryDebuggingAgent()
        self.results_interpreter_agent = ResultsInterpreterAgent()

        # Setup the handoff workflow
        self._configure_handoffs()

        # Conversation state
        self._current_agent = self.story_query_agent
        self._input_items: List[dict[str, str]] = []

    def _configure_handoffs(self) -> None:
        """Configure sequential handoffs between agents."""
        # StoryQueryAgent -> InconsistencyExplainerAgent
        self.story_query_agent.handoffs.append(
            handoff(
                self.inconsistency_explainer_agent,
                tool_description_override="Explain detected inconsistencies",
            )
        )
        # InconsistencyExplainerAgent -> StoryDebuggingAgent
        self.inconsistency_explainer_agent.handoffs.append(
            handoff(
                self.story_debugging_agent,
                tool_description_override="Guide the user through debugging steps",
            )
        )
        # StoryDebuggingAgent -> ResultsInterpreterAgent
        self.story_debugging_agent.handoffs.append(
            handoff(
                self.results_interpreter_agent,
                tool_description_override="Interpret the final results",
            )
        )

    async def reset(self) -> None:
        """Reset conversation state."""
        self._current_agent = self.story_query_agent
        self._input_items.clear()

    async def send(self, message: str, *, context: Any | None = None, max_turns: int = 8) -> str:
        """Send a user message through the workflow and return the assistant reply."""
        self._input_items.append({"role": "user", "content": message})
        result = await Runner.run(
            starting_agent=self._current_agent,
            input=self._input_items,
            context=context,
            max_turns=max_turns,
        )
        self._current_agent = result.last_agent
        self._input_items = result.to_input_list()
        return result.final_output_as(str)
