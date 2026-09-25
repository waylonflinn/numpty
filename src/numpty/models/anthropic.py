"""Anthropic adapter. Needs the `anthropic` extra."""

from anthropic import Anthropic, omit

from numpty.messages import (AssistantMessage, Block, Message, Reasoning, SystemMessage, Text, ToolCall,
                             ToolResultMessage, UserMessage)
from numpty.models import Model
from numpty.tools import Tool


class AnthropicMessages(Model):
    """Model adapter for the Anthropic Messages API. Needs the `anthropic` extra."""
    # NOTE: extended thinking is not turned on, so replies usually have no `Reasoning`.
    name = "anthropic"

    def __init__(self, model: str, max_tokens: int = 16_000):
        """Make an Anthropic model adapter. API key: `ANTHROPIC_API_KEY` environment variable.

        Args:
            model: Anthropic model ID, for example `claude-sonnet-5`.
            max_tokens: Maximum output tokens per reply.
        """
        self.client = Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def query(self, messages: list[Message], tools: list[Tool] = None):
        """Send a conversation and the available tools to the model. Get one reply.

        - System prompt: first `SystemMessage` only. Others are ignored.
        - `ToolResult.is_error`: sent to the model.
        - `Reasoning`: sent back only if `origin` is `("anthropic", <this model>)`.
        - Unknown reply block types: dropped.

        Args:
            messages: Conversation history, oldest first.
            tools: Tools the model can call. `None` for no tools.

        Returns:
            Model reply.
        """
        system = next((m.content for m in messages if isinstance(m, SystemMessage)), None)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system or omit,
            messages=[d for m in messages for d in self.render_message(m)],
            tools=[self.render_tool(t) for t in tools or []],
        )

        blocks = [b for c in response.content if (b := self.parse_block(c))]

        return AssistantMessage(blocks=blocks, origin=(self.name, self.model))

    def parse_block(self, block) -> Block | None:
        """Convert an Anthropic reply content block to a numpty block.

        Args:
            block: Anthropic content block.

        Returns:
            `Text`, `ToolCall`, or `Reasoning` (for `thinking` and `redacted_thinking`). `None` for other types.
        """
        match block.type:
            case "thinking" | "redacted_thinking": return Reasoning(block.model_dump(exclude_none=True))
            case "text":                           return Text(block.text)
            case "tool_use":                       return ToolCall(block.id, block.name, block.input)
            case _:                                return None

    def render_message(self, message) -> list[dict]:
        """Convert a numpty message to Anthropic API format.

        Args:
            message: Message to convert.

        Returns:
            Zero or one Anthropic messages. `[]` for `SystemMessage`.
        """
        match message:
            case SystemMessage():
                return []
            case UserMessage():
                return [{"role": "user", "content": message.content}]
            case AssistantMessage():
                blocks = [d for b in message.blocks if (d := self.render_block(b, message.origin))]
                return [{"role": "assistant", "content": blocks}]
            case ToolResultMessage():
                return [{"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": t.call_id, "content": t.content, "is_error": t.is_error}
                    for t in message.tool_results]}]

    def render_block(self, block, origin) -> dict | None:
        """Convert a numpty block to an Anthropic content block.

        Args:
            block: Block to convert.
            origin: `origin` of the message that holds the block.

        Returns:
            Anthropic content block. `None` for `Reasoning` from a different origin.
        """
        match block:
            case Text():      return {"type": "text", "text": block.text}
            case ToolCall():  return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.arguments}
            case Reasoning(): return block.data if origin == (self.name, self.model) else None

    def render_tool(self, tool: Tool):
        """Convert a tool to an Anthropic tool definition.

        Args:
            tool: Tool to convert.

        Returns:
            Anthropic tool definition.
        """
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters
        }
