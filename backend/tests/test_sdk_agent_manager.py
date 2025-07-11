import os
import sys
import types
from unittest.mock import AsyncMock, patch

import pytest

# Provide minimal stubs for external dependencies so sdk_agents.manager can import
agents_pkg = types.ModuleType("agents")
class Runner:
    @staticmethod
    async def run(starting_agent, input, context=None, max_turns=1):
        raise NotImplementedError

def handoff(agent):
    return agent
agents_pkg.Runner = Runner
agents_pkg.handoff = handoff
sys.modules['agents'] = agents_pkg

agent_base = types.ModuleType("agents.agent")
class Agent:
    def __init__(self):
        self.handoffs = []
agent_base.Agent = Agent
sys.modules['agents.agent'] = agent_base

agent_tool = types.ModuleType("agents.tool")
agent_tool.function_tool = lambda f: f
sys.modules['agents.tool'] = agent_tool

# Stub out graphiti_core modules used by GraphitiManager
graphiti_core = types.ModuleType("graphiti_core")
graphiti_core.Graphiti = object
nodes = types.ModuleType("graphiti_core.nodes")
nodes.EntityNode = object
nodes.EpisodicNode = object
edges = types.ModuleType("graphiti_core.edges")
edges.EntityEdge = object
sys.modules['graphiti_core'] = graphiti_core
sys.modules['graphiti_core.nodes'] = nodes
sys.modules['graphiti_core.edges'] = edges
search_mod = types.ModuleType("graphiti_core.search.search")
search_mod.SearchConfig = object
sys.modules['graphiti_core.search'] = types.ModuleType("graphiti_core.search")
sys.modules['graphiti_core.search.search'] = search_mod

# Stub neo4j driver used in story_processor
neo4j = types.ModuleType("neo4j")
neo4j.AsyncGraphDatabase = object
sys.modules['neo4j'] = neo4j

# Ensure backend directory is on path
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
async def test_follow_up_workflow():
    """Workflow continues only through configured handoffs."""
    os.environ.pop("OPENAI_API_KEY", None)
    manager = SDKAgentManager()
    agents = [manager.story_query_agent, manager.results_interpreter_agent]

    choose_mock = AsyncMock(return_value=agents)

    async def fake_run(starting_agent, input, context=None, max_turns=1):
        if starting_agent is agents[0]:
            # handoff to next agent should be configured
            assert starting_agent.handoffs == [agents[1]]
            return DummyResult(starting_agent, input, "Would you like more detail?")
        assert starting_agent.handoffs == []
        return DummyResult(starting_agent, input, "All done")

    run_mock = AsyncMock(side_effect=fake_run)
    with patch.object(SDKAgentManager, "choose_agents", choose_mock), patch(
        "sdk_agents.manager.Runner.run", run_mock
    ):
        out1 = await manager.send("Hello")
        assert "more detail" in out1
        assert manager._last_agent_index == 0
        assert len(manager._conversation_history) == 2

        out2 = await manager.send("yes")
        assert out2 == "All done"
        assert manager._last_agent_index == 1
        assert len(manager._conversation_history) == 4
        assert choose_mock.call_count == 1
        assert run_mock.call_count == 2

    # handoffs cleared after send
    assert manager.story_query_agent.handoffs == []
    assert manager.results_interpreter_agent.handoffs == []


@pytest.mark.asyncio
async def test_decline_follow_up():
    """If the user declines, workflow does not continue to the next agent."""
    os.environ.pop("OPENAI_API_KEY", None)
    manager = SDKAgentManager()
    agents = [manager.story_query_agent, manager.results_interpreter_agent]

    choose_mock = AsyncMock(return_value=agents)

    async def fake_run(starting_agent, input, context=None, max_turns=1):
        return DummyResult(starting_agent, input, "Would you like more detail?")

    run_mock = AsyncMock(side_effect=fake_run)
    with patch.object(SDKAgentManager, "choose_agents", choose_mock), patch(
        "sdk_agents.manager.Runner.run", run_mock
    ):
        await manager.send("Hello")
        calls = run_mock.call_count
        out = await manager.send("no thanks")
        assert out.startswith("Okay")
        assert run_mock.call_count == calls
        assert manager._last_agent_index == 0
        assert len(manager._conversation_history) == 3
        assert choose_mock.call_count == 1

    assert manager.story_query_agent.handoffs == []
    assert manager.results_interpreter_agent.handoffs == []
