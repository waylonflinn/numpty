"""OpenAI adapters. Need the `openai` extra."""

import json

from openai import OpenAI

from numpty.messages import (AssistantMessage, Block, Message, Reasoning, SystemMessage, Text, ToolCall,
                             ToolResultMessage, UserMessage)
from numpty.models import Model
from numpty.tools import Tool


class OpenAIChat(Model):
    """Model adapter for the OpenAI Chat Completions API. Needs the `openai` extra.

    Also works with OpenAI-compatible servers, for example local models. Set `base_url`.
    """
    # NOTE: `Reasoning` not supported. Newer OpenAI models do not expose reasoning in this API.
    name = "openai-chat"

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, **kwargs):
        """Make a Chat Completions model adapter.

        Args:
            model: Model ID.
            base_url: API URL. Set for OpenAI-compatible servers. Default: OpenAI
                SDK default (`OPENAI_BASE_URL` or the OpenAI API).
            api_key: API key. Default: `OPENAI_API_KEY` environment variable.
            **kwargs: Extra arguments for each API call, for example `reasoning_effort`.
        """
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.kwargs = kwargs

    def query(self, messages: list[Message], tools: list[Tool] = None):
        """Send a conversation and the available tools to the model. Get one reply.

        - System prompt: every `SystemMessage` is sent, in place.
        - `ToolResult.is_error`: not sent. The model sees only `content`.
        - `Reasoning`: not read from replies. Not sent.

        Args:
            messages: Conversation history, oldest first.
            tools: Tools the model can call.

        Returns:
            Model reply.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[d for m in messages for d in self.render_message(m)],
            tools=[self.render_tool(t) for t in tools or []],
            **self.kwargs
        )

        message = response.choices[0].message
        blocks = []
        if message.content:
            blocks.append(Text(message.content))
        for c in message.tool_calls or []:
            blocks.append(ToolCall(c.id, c.function.name, json.loads(c.function.arguments)))

        return AssistantMessage(blocks=blocks, origin=(self.name, self.model))

    def render_message(self, message: Message) -> list[dict]:
        """Convert a numpty message to Chat Completions format.

        Args:
            message: Message to convert.

        Returns:
            Chat messages. One per tool result for `ToolResultMessage`, else one.
        """
        match message:
            case SystemMessage():    return [{"role": "system",    "content": message.content}]
            case UserMessage():      return [{"role": "user",      "content": message.content}]
            case AssistantMessage():
                rendered = {"role": "assistant", "content": message.text}
                if message.tool_calls:
                    rendered["tool_calls"] = [
                        {"id": c.id, "type": "function",
                         "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                        for c in message.tool_calls
                    ]
                return [rendered]
            case ToolResultMessage():
                return [{"role": "tool", "tool_call_id": t.call_id, "content": t.content}
                        for t in message.tool_results]

    def render_tool(self, tool: Tool):
        """Convert a tool to a Chat Completions tool definition.

        Args:
            tool: Tool to convert.

        Returns:
            Chat Completions tool definition.
        """
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        }


class OpenAIResponses(Model):
    """Model adapter for the OpenAI Responses API. Needs the `openai` extra."""
    name = "openai-responses"

    def __init__(self, model: str, reasoning_effort="medium"):
        """Make a Responses model adapter. API key: `OPENAI_API_KEY` environment variable.

        Args:
            model: OpenAI model ID.
            reasoning_effort: Reasoning effort, for example `none`, `low`, `medium`, `high`.
        """
        self.model = model
        self.client = OpenAI()
        self.reasoning = {"effort": reasoning_effort}

    def query(self, messages: list[Message], tools: list[Tool] = None):
        """Send a conversation and the available tools to the model. Get one reply.

        - System prompt: first `SystemMessage` only. Others are ignored.
        - `ToolResult.is_error`: not sent. The model sees only `content`.
        - `Reasoning`: sent back only if `origin` is `("openai-responses", <this model>)`.
        - Unknown output item types: dropped.

        Args:
            messages: Conversation history, oldest first.
            tools: Tools the model can call. `None` for no tools.

        Returns:
            Model reply.
        """
        system = next((m.content for m in messages if isinstance(m, SystemMessage)), None)

        response = self.client.responses.create(
            model=self.model,
            instructions=system,
            input=[d for m in messages for d in self.render_message(m)],
            tools=[self.render_tool(t) for t in tools or []],
            reasoning=self.reasoning
        )

        blocks = [b for item in response.output if (b := self.parse_item(item))]
        return AssistantMessage(blocks=blocks, origin=(self.name, self.model))

    def parse_item(self, item) -> Block | None:
        """Convert a Responses output item to a numpty block.

        Args:
            item: Responses output item.

        Returns:
            `Reasoning`, `Text`, or `ToolCall`. `None` for other types.
        """
        match item.type:
            case "reasoning":     return Reasoning(item.model_dump(exclude_none=True))
            case "message":       return Text("".join(c.text for c in item.content if c.type == "output_text"))
            case "function_call": return ToolCall(item.call_id, item.name, json.loads(item.arguments))
            case _:               return None

    def render_message(self, message: Message) -> list[dict]:
        """Convert a numpty message to Responses input items.

        Args:
            message: Message to convert.

        Returns:
            Input items. `[]` for `SystemMessage`. One item per block or tool result otherwise.
        """
        match message:
            case SystemMessage(): return []  # sent as `instructions` by `query`
            case UserMessage():   return [{"role": "user", "content": message.content}]
            case AssistantMessage():
                return [d for b in message.blocks if (d := self.render_block(b, message.origin))]
            case ToolResultMessage():
                return [{"type": "function_call_output", "call_id": t.call_id, "output": t.content}
                        for t in message.tool_results]

    def render_block(self, block, origin) -> dict | None:
        """Convert a numpty block to a Responses input item.

        Args:
            block: Block to convert.
            origin: `origin` of the message that holds the block.

        Returns:
            Input item. `None` for `Reasoning` from a different origin.
        """
        match block:
            case Text():      return {"role": "assistant", "content": block.text}
            case ToolCall():  return {"type": "function_call", "call_id": block.id,
                                      "name": block.name, "arguments": json.dumps(block.arguments)}
            case Reasoning(): return block.data if origin == (self.name, self.model) else None

    def render_tool(self, tool: Tool):
        """Convert a tool to a Responses tool definition.

        Args:
            tool: Tool to convert.

        Returns:
            Responses tool definition.
        """
        return {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "strict": False, # API default's to true, which forces optional parameters to be required.
        }
