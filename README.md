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
