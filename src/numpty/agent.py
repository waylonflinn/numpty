"""Agent loop."""

import json
from contextlib import nullcontext

from numpty.decisions import Answer, DecisionModel, Question, schema as decision_schema
from numpty.messages import SystemMessage, ToolCall, ToolResult, ToolResultMessage, UserMessage
from numpty.models import Model
from numpty.policy import Policy
from numpty.run import RunTool
from numpty.tools import ShellTool, Tool


class Agent:
    """Tool-use loop over a model. Keeps the conversation across calls.

    Chat model: `answer` and `decide`. Decision model: `decide` only.

    Attributes:
        messages: Conversation history, oldest first. Starts with the system message, if given.
        tools: Tools by name.
        model: The model.
        policy: Permissions for tool calls, or `None`.
    """

    def __init__(self, model: Model | DecisionModel, tools: list[Tool], system: str = "", policy: Policy | None = None):
        """Make an agent.

        Args:
            model: Chat model or decision model to query.
            tools: Tools the model can call. Same name: last one wins.
            system: System prompt.
            policy: Permissions for tool calls. Model queries are not checked. Default: `None`, no checks.
                `RunTool` code runs under it in its own process.

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

    def __call__(self, text, max_turns=5, schema: dict | None = None):
        """Same as `answer`."""
        return self.answer(text, max_turns, schema)

    def answer(self, text, max_turns=5, schema: dict | None = None):
        """Send a user message. Run tool calls until the model replies without one.

        Each turn: query the model, then run all tool calls in the reply.

        Args:
            text: User message.
            max_turns: Maximum model queries for this message.
            schema: JSON Schema the final reply must conform to. Passed to `Model.query`
                on every turn. `None` for a free-text reply.

        Returns:
            Text of the final reply. With `schema`: the reply's object, a `dict`.

        Raises:
            RuntimeError: Model still calls tools after `max_turns` queries. History
                keeps all turns, ending with tool results.
            ValueError: `schema` was given and the model returned no conforming object.
                See `Model.query`.
            TypeError: `model` is a `DecisionModel`.
        """
        if isinstance(self.model, DecisionModel):
            raise TypeError("a DecisionModel cannot chat: use decide")
        # NOTE: model API errors propagate. The user message stays in history with no
        # reply, so a retry adds a second user message in a row.
        self.messages.append(UserMessage(text))

        for _ in range(max_turns):
            reply = self.model.query(self.messages, list(self.tools.values()), schema)
            self.messages.append(reply)

            # non-tool call response, return
            if not reply.tool_calls:
                return reply.text if schema is None else reply.object

            self.messages.append(ToolResultMessage([self.run(c) for c in reply.tool_calls]))

        raise RuntimeError("max_turns exceeded")

    def decide(self, state: str | dict | list, questions: dict[str, Question]) -> dict[str, Answer]:
        """Answer typed questions about a state. Stateless: `messages` is not read or changed.

        Decision model: `model.decision`, with `confidence` and `probabilities`.
        Chat model: one `Model.query` with `decisions.schema(questions)`, no tools. The agent
        system prompt is not sent. The system message asks the questions and shows the schema
        (llama-server does not show the schema to the model), and the user message is the state.
        Labels only: `confidence` and `probabilities` are `None`.

        Args:
            state: Text, or a JSON object or array, to judge. Not text: sent as JSON text.
            questions: Questions by name.

        Returns:
            Answer by question name.

        Raises:
            ValueError: Chat model returned no conforming object. See `Model.query`.
        """
        if not isinstance(state, str):
            state = json.dumps(state)
        if isinstance(self.model, DecisionModel):
            return self.model.decision(state, questions)

        answer_schema = decision_schema(questions)
        system = ("Answer these questions about the user message. Reply in JSON per this schema:\n"
                  + json.dumps(answer_schema))
        values = self.model.query([SystemMessage(system), UserMessage(state)], schema=answer_schema).object
        return {key: Answer(values[key]) for key in questions}

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

            # NOTE: special case until tools declare the policy they need. The policy is enforced
            # in the RunTool process, not here.
            if isinstance(tool, RunTool):
                result = tool.run(tool_call.arguments, policy=self.policy or Policy.UNRESTRICTED)
            else:
                with self.policy.enforcement() if self.policy else nullcontext():
                    result = str(tool.run(tool_call.arguments))
            message = ToolResult(tool_call.id, result)
        except Exception as e:
            message = ToolResult(tool_call.id, f"{type(e).__name__}: {e}", is_error=True)

        return message
