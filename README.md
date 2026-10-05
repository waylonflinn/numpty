# numpty

Simple (sort of) secure agency for your shallow semantic engine.

*or, less alliteratively*

A minimal, provider-neutral agent library with optional guardrails.

## Install

The core has no dependencies, and without a provider it cannot call a model.
Install at least one extra:

- `anthropic` — `AnthropicMessages`
- `openai` — `OpenAIChat`, `OpenAIResponses`
- `providers` — `anthropic` and `openai` together
- `calc` — `simpleeval`, needed by the `calculate` function
- `security` — `fastaudit`, needed by a restrictive `Policy`

`all` installs every extra.

```bash
pip install 'numpty[providers,calc]'
```

## Example

```python
from numpty import Agent, AnthropicMessages, PythonTool
from numpty.functions import read_file, calculate

agent = Agent(AnthropicMessages("claude-sonnet-5"),
              [PythonTool(read_file), PythonTool(calculate)],
              system="You are a helpful assistant.")
agent("Read 'income.csv'. How much income did Bob have in total?")
```

`OpenAIChat` and `OpenAIResponses` work the same way. API key: `OPENAI_API_KEY`.

```python
from numpty import Agent, OpenAIChat, PythonTool
from numpty.functions import calculate

agent = Agent(OpenAIChat("gpt-5"), [PythonTool(calculate)])
agent("What is 17 * 25?")
```

## Structured output

Pass a JSON Schema as `schema`. The reply is a `dict` that conforms to it, instead of text.
Tools still work: the model may call tools first; the object comes on the final turn.

```python
schema = {
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "population": {"type": "integer"},
    },
    "required": ["city", "population"],
    "additionalProperties": False,
}
agent("What is the largest city in Portugal?", schema=schema)
# {'city': 'Lisbon', 'population': 545923}
```

Every provider accepts this subset: root `object` with `properties`, all of them in
`required`, and `additionalProperties: false`; `string`, `integer`, `number`, `boolean`,
`null`; `enum`; `array` with `items`; `description`. No numeric or length constraints, no
optional properties, no recursion. For an optional value, use `"type": ["string", "null"]`.

The schema is sent as given. Each provider constrains output on its side (strict mode, or a
grammar for local models). Out of subset: the provider rejects the request. The model
refused, hit the token limit, or returned something that is not a JSON object: `ValueError`.
A server without strict mode may return JSON that does not conform; it is returned as-is.

Without an agent: `model.query(messages, schema=schema).object`.

On llama.cpp, a schema takes precedence over `tools`: the model cannot call tools on that
turn, and Qwen templates reject the request (see Local models).

## Local models

`OpenAIChat` works with OpenAI-compatible servers. Set `base_url`. Tested with Qwen 3.8
on [llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server`, started with
`--jinja` so the server parses tool calls and separates reasoning from text.

```python
from numpty import Agent, OpenAIChat, PythonTool
from numpty.functions import calculate

model = OpenAIChat("qwen-38-27b-Q4", base_url="http://localhost:8080/v1", api_key="none",
                   reasoning_effort="medium")
agent = Agent(model, [PythonTool(calculate)])
agent("What is 17 * 25?")
```

Extra keyword arguments go into every request. `reasoning_effort` sets the thinking
budget. Qwen 3.8 accepts `low`, `medium`, and `xhigh`. The default is `xhigh`, which
is slow on consumer hardware. llama.cpp forwards this parameter from build b11429.
Older builds ignore it. There, use
`extra_body={"chat_template_kwargs": {"reasoning_effort": "medium"}}`.

A reply's `reasoning_content` becomes a `Reasoning` block and goes back on later turns
of the same model. The server's chat template decides whether the model sees it. For
Qwen 3.8 this is `preserve_thinking`, which can be set per request:
`extra_body={"chat_template_kwargs": {"preserve_thinking": False}}`.

Limits:

- `<think>` tags inside reply text are not parsed. Without `--jinja`, reasoning stays
  in the text.
- Hosted OpenAI models do not return `reasoning_content`. Use `OpenAIResponses` for
  reasoning with those.
- `schema` and `tools` in one request: the server constrains the reply to the schema and
  does not parse tool calls, so an agent with tools gets no tool turns. Qwen 3.6 and 3.8
  templates go further and reject the request with `failed to parse grammar`
  ([issue 27114](https://github.com/ggml-org/llama.cpp/issues/27114), closed as by design;
  Gemma 4 accepts it). Checked on build b11429. Use `schema` with an agent that has no tools.

## Permissions

The [fastaudit](https://github.com/AnswerDotAI/fastaudit) library is used for adding
guardrails to Agent tool calls. This is fit for preventing clumsy mistakes by the LLM 
(the failure mode found in most mainstream reasonably well-aligned models).
It should not be considered robust against adversarial attack.

A `Policy` limits what tool calls can do. `Agent` applies it to each tool call, not
to model queries. A denied action raises `PermissionError`, and the model gets it as
an error result.

```python
from numpty import Agent, AnthropicMessages, Policy, PythonTool
from numpty.functions import read_file, write_file

policy = Policy(Policy.Filesystem.READ | Policy.Filesystem.WRITE_LOCATION)
agent = Agent(AnthropicMessages("claude-sonnet-5"),
              [PythonTool(read_file), PythonTool(write_file)], policy=policy)
```

This policy lets tools read any file and write only in the current directory and its
subfolders. It denies network access, processes, and threads. `Policy()` reads only.
`Policy.UNRESTRICTED` checks nothing.

The policy is a guardrail against mistakes by a model. It is not a sandbox. Code that
tries to escape on purpose can escape. For adversarial code, use a container, a VM,
or an OS-level sandbox.

Limits:

- Reads are not checked. Tool output goes to the model provider, so a tool can leak
  any file that the user can read, for example a credentials file.
- New threads are denied unless the policy includes `Policy.Process.UNRESTRICTED`.
- C extensions that fastaudit does not know are denied. For example, pyarrow is
  denied, so `DataFrame.to_parquet` fails. `monitor_calls=False` lets them run
  unchecked.
- Only one policy can be active at a time. A nested agent with a different policy
  cannot run tools inside a tool call of the outer agent.
- `ShellTool` needs `Policy.Process.UNRESTRICTED`. A new process is not checked, so a
  shell has full access. For a tool that can run shell commands, use `Policy.UNRESTRICTED`
  to make this clear.

## Development

```bash
uv sync --all-extras
```

```bash
uv run pytest -q
```

Generate API documentation into `docs/`:

```bash
PYTHONPATH=src uv run griffonner generate griffonner/pages/numpty --output docs --template-dir griffonner
```

Files under `docs/` are generated. Change docstrings, page descriptors under
`griffonner/pages/numpty/`, or templates under `griffonner/numpty/`, then
regenerate.
