"""Model interface. Provider adapters are in submodules. Each needs its extra."""

from abc import ABC, abstractmethod


class Model(ABC):
    """Chat model adapter for one provider API.

    Subclass: implement `query` and set `name`. Convert numpty messages and tools
    to provider format, and convert the reply back.

    Attributes:
        name: Provider ID. First item of `origin` in replies.
    """
    # BUG: `name` needed by every subclass. Not declared or enforced here.

    @abstractmethod
    def query(self):
        """Send a conversation and the available tools to the model. Get one reply.

        Args:
            messages: Conversation history, oldest first.
            tools: Tools the model can call. `None` or `[]` for no tools.

        Returns:
            `AssistantMessage` with `origin` set to `(provider, model)`.
        """
        # BUG: signature has no `messages` or `tools`. Subclasses take `(messages, tools=None)`.
        pass
