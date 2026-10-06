"""Minimal, provider-neutral agent library.

Core: no dependencies. Provider adapters load their SDK on first use.
`AnthropicMessages` needs the `anthropic` extra. `OpenAIChat` and
`OpenAIResponses` need `openai`. `TypeSafe` needs `typesafe`. A restrictive `Policy` needs `security`.
"""

from importlib import import_module

from numpty.agent import Agent
from numpty.decisions import Answer, Choice, DecisionModel, DecisionTool, Noul, Score, TypeSafe
from numpty.messages import (AssistantMessage, Block, Message, Object, Reasoning, SystemMessage, Text, ToolCall, ToolResult,
                             ToolResultMessage, UserMessage)
from numpty.models import Model
from numpty.policy import Policy
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
    "Agent", "Answer", "AssistantMessage", "Block", "Choice", "DecisionModel", "DecisionTool", "Message", "Model", "Noul",
    "Object", "Policy", "PythonTool", "Reasoning", "Score", "ShellTool", "SystemMessage", "Text", "Tool", "ToolCall",
    "ToolResult", "ToolResultMessage", "TypeSafe", "UserMessage",
    *_PROVIDERS,
]
