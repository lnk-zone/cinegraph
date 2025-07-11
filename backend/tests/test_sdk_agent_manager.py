import pytest
from unittest.mock import AsyncMock, patch

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sdk_agents.manager import SDKAgentManager

class DummyResult:
    def __init__(self, agent, history, output):
        self._last_agent = agent
        self.input = history
        self.new_items = [{"role": "assistant", "content": output}]
        self.final_output = output
    @property
    def last_agent(self):
        return self._last_agent
    def to_input_list(self):
        return self.input + self.new_items
    def final_output_as(self, _type):
        return self.final_output

@pytest.mark.asyncio
async def test_continue_workflow_and_reset():
    manager = SDKAgentManager()
    agents = [manager.story_query_agent, manager.results_interpreter_agent]
    choose_mock = AsyncMock(return_value=agents)

    async def fake_run(starting_agent, input, context=None, max_turns=1):
        if starting_agent is agents[0]:
            return DummyResult(starting_agent, input, "Would you like more detail?")
        return DummyResult(starting_agent, input, "All done")

    with patch.object(SDKAgentManager, 'choose_agents', choose_mock), \
         patch('backend.sdk_agents.manager.Runner.run', new=AsyncMock(side_effect=fake_run)):
        out1 = await manager.send("Hello")
        assert "more detail" in out1
        assert manager._last_agent_index == 0
        history_len = len(manager._conversation_history)

        out2 = await manager.send("yes")
        assert out2 == "All done"
        assert manager._last_agent_index == 1
        assert len(manager._conversation_history) == history_len + 2
        assert choose_mock.call_count == 1

        await manager.reset()
        assert manager._last_agent_index == 0
        assert manager._conversation_history == []
        assert manager._current_agent is manager.story_query_agent

