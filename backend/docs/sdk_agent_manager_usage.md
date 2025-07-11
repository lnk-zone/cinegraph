# SDKAgentManager Quick Guide

This guide explains how to use the `SDKAgentManager` class to route messages between specialized agents.

## Initialization

```python
from sdk_agents.manager import SDKAgentManager

manager = SDKAgentManager()
```

The manager automatically creates all internal agents and sets up conversation state.

## Sending Messages

Use `send()` to process user input. The manager will choose the appropriate agent sequence and return the reply.

```python
response = await manager.send("How does the story begin?")
print(response)
```

The conversation history is stored internally so follow‑up calls to `send()` maintain context.

## Resetting the Conversation

Call `reset()` to clear the conversation history and return to the initial agent.

```python
await manager.reset()
```

After a reset the next `send()` call starts a fresh conversation.
