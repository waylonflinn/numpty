"""Decision models: typed questions about a state, answered with confidence.

Core: no dependencies. `TypeSafe` needs the `typesafe` extra, imported on construction.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

from numpty.tools import Tool


@dataclass
class Choice:
    """Question: pick one label.

    Attributes:
        instructions: What to decide.
        criteria: Description by label. `None`: the label alone.
    """
    instructions: str
    criteria: dict[str, str | None]


@dataclass
class Score:
    """Question: rate on ordered levels.

    Attributes:
        instructions: What to rate.
        criteria: Level descriptions, lowest first. Level number is the index.
    """
    instructions: str
    criteria: list[str]


@dataclass
class Noul:
    """Question: yes or no.

    Attributes:
        instructions: The yes/no question or statement.
        criteria: `{"true": <what counts as yes>, "false": <what counts as no>}`, or `None`.
    """
    instructions: str
    criteria: dict[str, str] | None = None


Question = Choice | Score | Noul
"""One typed question."""


@dataclass
class Answer:
    """Answer to one question.

    | Question | `value`                    | `probabilities`       |
    |----------|----------------------------|-----------------------|
    | `Choice` | label, `str`               | `{label: p}`          |
    | `Score`  | level, `int` or `float`    | `{level: p}`          |
    | `Noul`   | `bool`                     | `{True: p, False: p}` |

    `Score` from a decision model: expected level, a `float` between levels. From a chat model: `int`.

    Attributes:
        value: The answer.
        confidence: Certainty, 0 to 1. `None` from a chat model.
        probabilities: Probability of each option. `None` from a chat model.
    """
    value: str | int | float | bool
    confidence: float | None = None
    probabilities: dict | None = None


class DecisionModel(ABC):
    """Model that answers typed questions about a state. No chat, no tools.

    Subclass: implement `decision` and set `name`.

    Attributes:
        name: Provider ID.
    """
    name: str

    @abstractmethod
    def decision(self, state: str | dict | list, questions: dict[str, Question]) -> dict[str, Answer]:
        """Answer all questions about one state, in one request.

        Args:
            state: Text, or a JSON object or array, to judge.
            questions: Questions by name.

        Returns:
            Answer by question name, with `confidence` and `probabilities`.
        """
        pass


def schema(questions: dict[str, Question]) -> dict:
    """Make the JSON Schema of the answers, for a chat model with structured output.

    | Question | Property                                  |
    |----------|-------------------------------------------|
    | `Choice` | `string`, `enum` of labels                |
    | `Score`  | `integer`, `enum` of levels `0` to `n-1`  |
    | `Noul`   | `boolean`                                 |

    `description`: instructions, then one line per label, level, or `true`/`false`.
    In the portable subset of `Model.query`.

    Args:
        questions: Questions by name.

    Returns:
        JSON Schema of type `object`, one required property per question.
    """
    props = {}
    for key, q in questions.items():
        if isinstance(q, Choice):
            prop = {"type": "string", "enum": list(q.criteria)}
            lines = [f"{label}: {text}" if text else label for label, text in q.criteria.items()]
        elif isinstance(q, Score):
            prop = {"type": "integer", "enum": list(range(len(q.criteria)))}
            lines = [f"{level}: {text}" for level, text in enumerate(q.criteria)]
        else:
            prop = {"type": "boolean"}
            lines = [f"{k}: {v}" for k, v in (q.criteria or {}).items()]
        prop["description"] = "\n".join([q.instructions, *lines])
        props[key] = prop
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


class DecisionTool(Tool):
    """Tool that asks a decision model a fixed question set about a state the model gives.

    A tool call, so `Agent.policy` checks the request. A remote decision model needs
    `Policy.Network.UNRESTRICTED`.
    """

    parameters = {
        "type": "object",
        "properties": {"state": {"type": "string", "description": "Text to judge"}},
        "required": ["state"],
        "additionalProperties": False,
    }

    def __init__(self, decider: DecisionModel, questions: dict[str, Question], name: str | None = None,
                 description: str | None = None):
        """Wrap a question set as a tool.

        Args:
            decider: Decision model that answers.
            questions: Questions by name. Same set on every call.
            name: Tool name. Default: `decision-model-<question names joined by "-">`, cut to 64 characters.
            description: Tool description. Default: `DecisionTool.describe(questions)`.
        """
        self.decider = decider
        self.questions = questions
        self.name = name or ("decision-model-" + "-".join(questions))[:64]
        self.description = description or DecisionTool.describe(questions)

    def run(self, arguments: dict) -> dict:
        """Ask the questions about `arguments["state"]`.

        Args:
            arguments: `{"state": <text to judge>}`.

        Returns:
            `{name: {"value", "confidence", "probabilities"}}`, one entry per question.
        """
        answers = self.decider.decision(arguments["state"], self.questions)
        return {key: asdict(answer) for key, answer in answers.items()}

    @staticmethod
    def describe(questions: dict[str, Question]) -> str:
        """Make a tool description: one line per question, then how to call and what returns.

        Args:
            questions: Questions by name.

        Returns:
            Description text for the model.
        """
        lines = ["Ask a decision model these questions about a text:"]
        for key, q in questions.items():
            if isinstance(q, Choice):
                kind = f"choice of {', '.join(q.criteria)}"
            elif isinstance(q, Score):
                kind = f"score, levels 0 to {len(q.criteria) - 1}"
            else:
                kind = "yes/no"
            lines.append(f"- {key} ({kind}): {q.instructions}")
        lines.append('Call with {"state": <text to judge>}. '
                     "Returns per question: value, confidence (0 to 1), probabilities of each option.")
        return "\n".join(lines)


class TypeSafe(DecisionModel):
    """Decision model behind the System One protocol (`POST /v1/systemone`), through `typesafe-sdk`.

    Serves TypeSafe (Jev), llama-server with a decision GGUF, and llmman. Needs the `typesafe` extra.

    SDK exceptions propagate. llama-server: bad request is `TypeSafeBadRequestError` (400),
    not a decision model is `TypeSafeInternalServerError` (501). Option count, level count, and
    state length limits are per model. Not checked here: the server rejects.

    Attributes:
        model: Model name sent with each request.
        client: The `typesafe_sdk.TypeSafeClient`.
    """
    name = "typesafe"

    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, **kwargs):
        """Make a client.

        Args:
            model: Model name. For example `jev-latest`, or a llama-server model ID.
            base_url: Server URL. Default: TypeSafe.
            api_key: API key. Default: `$TYPESAFE_API_KEY`. Local hosts: any non-empty string.
            **kwargs: Passed to every `client.system_one` call. For example `timeout`, `extra_body`.
        """
        from typesafe_sdk import TypeSafeClient

        self.model = model
        self.client = TypeSafeClient(api_key=api_key, base_url=base_url)
        self.kwargs = kwargs

    def decision(self, state: str | dict | list, questions: dict[str, Question]) -> dict[str, Answer]:
        """Answer all questions about one state, in one request. See `DecisionModel.decision`."""
        wire = {key: self.render_question(q) for key, q in questions.items()}
        response = self.client.system_one(state, wire, model=self.model, **self.kwargs)
        return {key: self.parse_answer(a) for key, a in response.answers.items()}

    @staticmethod
    def render_question(question: Question) -> dict:
        """Convert a question to the wire format.

        Args:
            question: Question to send.

        Returns:
            `{"type", "instructions", "criteria"}`. `Noul` with no criteria: no `criteria` key.
        """
        kind = {Choice: "choice", Score: "score", Noul: "noul"}[type(question)]
        wire = {"type": kind, "instructions": question.instructions}
        if question.criteria is not None:
            wire["criteria"] = question.criteria
        return wire

    @staticmethod
    def parse_answer(answer) -> Answer:
        """Convert an SDK answer to an `Answer`.

        Score: `legend` is dropped. Noul: the wire has only `p`, the probability of yes.
        Then `value` is `p >= 0.5` and `confidence` is `2 * max(p, 1 - p) - 1`
        (the Choice formula at two options, derived here, not from the server).

        Args:
            answer: `ChoiceAnswer`, `ScoreAnswer`, or `NoulAnswer`.

        Returns:
            The answer.

        Raises:
            ValueError: Unknown answer type.
        """
        if answer.type == "choice":
            return Answer(answer.choice, answer.confidence, dict(answer.probabilities))
        if answer.type == "score":
            return Answer(answer.score, answer.confidence, dict(answer.probabilities))
        if answer.type == "noul":
            p = answer.noul
            return Answer(p >= 0.5, 2 * max(p, 1 - p) - 1, {True: p, False: 1 - p})
        raise ValueError(f"unknown answer type: {answer.type!r}")
