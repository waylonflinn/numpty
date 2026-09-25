"""Provider-neutral messages and content blocks."""

from dataclasses import dataclass


@dataclass
class Text:
    """Text content in an assistant reply.

    Attributes:
        text: The text.
    """
    text: str


@dataclass
class ToolCall:
    """Model request to run a tool.

    Attributes:
        id: Provider call ID. Matching `ToolResult.call_id` has the same value.
        name: Tool name.
        arguments: Argument values by parameter name.
    """
    id: str
    name: str
    arguments: dict


@dataclass
class Reasoning:
    """Model reasoning, kept to send back on later turns.

    Specific to a given model and provider. May be signed or encrypted. Do not modify.

    Attributes:
        data: Provider reasoning block, verbatim.
    """
    data: dict


Block = Text | ToolCall | Reasoning
"""One content item in an assistant reply."""


@dataclass
class SystemMessage:
    """Instructions for model behavior in the conversation.

    Attributes:
        content: The instructions.
    """
    content: str


@dataclass
class UserMessage:
    """Message from the user.

    Attributes:
        content: Message text.
    """
    content: str


@dataclass
class AssistantMessage:
    """Model reply.

    Attributes:
        blocks: Reply content, in model order.
        origin: `(provider, model)` that made the reply. `Reasoning` blocks go back
            only to a model with the same origin.
    """
    blocks: list[Block]
    origin: tuple[str, str]

    @property
    def tool_calls(self):
        """`ToolCall` blocks, in order."""
        return [b for b in self.blocks if isinstance(b, ToolCall)]

    @property
    def text(self):
        """`Text` blocks joined with no separator. `""` if none."""
        return "".join(b.text for b in self.blocks if isinstance(b, Text))


@dataclass
class ToolResult:
    """Result of one tool call.

    Attributes:
        call_id: `id` of the `ToolCall` this answers.
        content: Tool output as text.
        is_error: True if the tool failed. `content` then describes the failure.
    """
    call_id: str
    content: str
    is_error: bool = False


@dataclass
class ToolResultMessage:
    """Results of all tool calls in one assistant reply.

    Attributes:
        tool_results: One result per tool call.
    """
    tool_results: list[ToolResult]


Message = SystemMessage | UserMessage | AssistantMessage | ToolResultMessage
"""One entry in a conversation history."""
