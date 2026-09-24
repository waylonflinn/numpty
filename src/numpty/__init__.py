"""Minimal, provider-neutral agent library.

Core: no dependencies. Provider adapters load their SDK on first use.
`AnthropicMessages` needs the `anthropic` extra. `OpenAIChat` and
`OpenAIResponses` need `openai`.
"""

from importlib import import_module

from numpty.agent import Agent
from numpty.messages import (AssistantMessage, Block, Message, Reasoning, SystemMessage, Text, ToolCall, ToolResult,
                             ToolResultMessage, UserMessage)
from numpty.models import Model
from numpty.tools import PythonTool, ShellTool, Tool

_PROVIDERS = {
    "OpenAIChat": "numpty.models.openai",
    "OpenAIResponses": "numpty.models.openai",
    "AnthropicMessages": "numpty.models.anthropic",
}


def __getattr__(name):
    if name in _PROVIDERS:
        return getattr(import_module(_PROVIDERS[name]), name)
    raise AttributeError(f"module 'numpty' has no attribute '{name}'")


__all__ = [
    "Agent", "AssistantMessage", "Block", "Message", "Model", "PythonTool", "Reasoning", "ShellTool",
    "SystemMessage", "Text", "Tool", "ToolCall", "ToolResult", "ToolResultMessage", "UserMessage",
    *_PROVIDERS,
]
