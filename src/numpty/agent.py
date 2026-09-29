"""Agent loop."""

from contextlib import nullcontext

from numpty.messages import SystemMessage, ToolCall, ToolResult, ToolResultMessage, UserMessage
from numpty.models import Model
from numpty.policy import Policy
from numpty.tools import ShellTool, Tool


class Agent:
    """Tool-use loop over a model. Keeps the conversation across calls.

    Attributes:
        messages: Conversation history, oldest first. Starts with the system message, if given.
        tools: Tools by name.
        model: The model.
        policy: Permissions for tool calls, or `None`.
    """

    def __init__(self, model: Model, tools: list[Tool], system: str = "", policy: Policy | None = None):
        """Make an agent.

        Args:
            model: Model to query.
            tools: Tools the model can call. Same name: last one wins.
            system: System prompt.
            policy: Permissions for tool calls. Model queries are not checked. Default: `None`, no checks.

        Raises:
            ValueError: A tool starts processes (`ShellTool`) and `policy` does not allow processes.
        """
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.messages = [SystemMessage(system)] if system else []
        self.policy = policy
        self._check_policy()

    def _check_policy(self):
        """Raise ValueError if a tool needs more than the policy allows. Fail at construction,
        not on every call."""
        # NOTE: special case until tools declare the policy they need.
        if self.policy and Policy.Process.UNRESTRICTED not in self.policy.process:
            for tool in self.tools.values():
                if isinstance(tool, ShellTool):
                    raise ValueError(f"tool '{tool.name}' starts processes: policy needs Policy.Process.UNRESTRICTED")

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
            Tool output converted to text. On failure (tool raises, no tool
                with that name, or `policy` denies an action): `is_error=True`,
                content `<ExceptionType>: <message>`.
        """
        try:
            tool = self.tools[tool_call.name]

            with self.policy.enforcement() if self.policy else nullcontext():
                result = str(tool.run(tool_call.arguments))
            message = ToolResult(tool_call.id, result)
        except Exception as e:
            message = ToolResult(tool_call.id, f"{type(e).__name__}: {e}", is_error=True)

        return message
