"""Agent loop."""

from numpty.messages import SystemMessage, ToolCall, ToolResult, ToolResultMessage, UserMessage
from numpty.models import Model
from numpty.tools import Tool


class Agent:
    """Tool-use loop over a model. Keeps the conversation across calls.

    Attributes:
        messages: Conversation history, oldest first. Starts with the system message, if given.
        tools: Tools by name.
        model: The model.
    """

    def __init__(self, model: Model, tools: list[Tool], system: str = ""):
        """Make an agent.

        Args:
            model: Model to query.
            tools: Tools the model can call. Same name: last one wins.
            system: System prompt.
        """
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.messages = [SystemMessage(system)] if system else []

    def __call__(self, text, max_turns=5):
        """Send a user message. Run tool calls until the model replies without one.

        Each turn: query the model, then run all tool calls in the reply.

        Args:
            text: User message.
            max_turns: Maximum model queries for this message.

        Returns:
            Text of the final reply.

        Raises:
            RuntimeError: Model still calls tools after `max_turns` queries. History
                keeps all turns, ending with tool results.
        """
        # NOTE: model API errors propagate. The user message stays in history with no
        # reply, so a retry adds a second user message in a row.
        self.messages.append(UserMessage(text))

        for _ in range(max_turns):
            reply = self.model.query(self.messages, list(self.tools.values()))
            self.messages.append(reply)

            # non-tool call response, return
            if not reply.tool_calls:
                return reply.text

            self.messages.append(ToolResultMessage([self.run(c) for c in reply.tool_calls]))

        raise RuntimeError("max_turns exceeded")

    def run(self, tool_call: ToolCall) -> ToolResult:
        """Run one tool call. Never raises.

        Args:
            tool_call: Call to run.

        Returns:
            Tool output converted to text. On failure (tool raises, or no tool
            with that name): `is_error=True`, content `<ExceptionType>: <message>`.
        """
        try:
            tool = self.tools[tool_call.name]

            result = str(tool.run(tool_call.arguments))
            message = ToolResult(tool_call.id, result)
        except Exception as e:
            message = ToolResult(tool_call.id, f"{type(e).__name__}: {e}", is_error=True)

        return message
