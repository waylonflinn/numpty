"""Model interface. Provider adapters are in submodules. Each needs its extra."""

import json
from abc import ABC, abstractmethod

from numpty.messages import AssistantMessage, Message, Object, Text
from numpty.tools import Tool

class Model(ABC):
    """Chat model adapter for one provider API.

    Subclass: implement `query` and set `name`. Convert numpty messages and tools
    to provider format, and convert the reply back.

    Attributes:
        name: Provider ID. First item of `origin` in replies.
    """
    name: str

    @abstractmethod
    def query(self, messages: list[Message], tools: list[Tool] = None, schema: dict | None = None):
        """Send a conversation and the available tools to the model. Get one reply.

        With `schema`, the provider constrains the reply to a JSON object that conforms
        to it. The reply then has one `Object` block in place of `Text`, unless the model
        called a tool: tool turns are unchanged, and the object arrives on the final turn.

        The schema is sent as given. Every provider accepts this subset: root `object`
        with `properties`, all of them in `required`, and `additionalProperties: false`;
        `string`, `integer`, `number`, `boolean`, `null`; `enum`; `array` with `items`;
        `description`. No numeric or length constraints, no optional properties, no
        recursion. Other keywords may be rejected by the provider.

        Args:
            messages: Conversation history, oldest first.
            tools: Tools the model can call. `None` or `[]` for no tools.
            schema: JSON Schema for the reply. `None` for a free-text reply.

        Returns:
            `AssistantMessage` with `origin` set to `(provider, model)`.

        Raises:
            ValueError: `schema` was given and the model refused, the reply was cut
                off at the token limit, or the reply is not a JSON object.
        """
        pass

    @staticmethod
    def parse_object(reply: AssistantMessage) -> AssistantMessage:
        """Replace the `Text` blocks of a structured reply with one `Object`.

        Args:
            reply: Reply to a query with a schema. Its `text` is the JSON.

        Returns:
            New message, same origin. Other blocks are kept in place; `Object` is last.

        Raises:
            ValueError: `reply.text` is not a JSON object.
        """
        text = reply.text
        try:
            value = json.loads(text)
        except ValueError:
            raise ValueError(f"structured output is not valid JSON: {text[:200]!r}") from None
        if not isinstance(value, dict):
            raise ValueError(f"structured output is not a JSON object: {text[:200]!r}")

        blocks = [b for b in reply.blocks if not isinstance(b, Text)] + [Object(value)]
        return AssistantMessage(blocks=blocks, origin=reply.origin)
