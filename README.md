# numpty

A minimal, provider-neutral agent library: tools, messages, model adapters, and
an agent loop.

## Install

The core has no dependencies, and without a provider it cannot call a model.
Install at least one extra:

- `anthropic` — `AnthropicMessages`
- `openai` — `OpenAIChat`, `OpenAIResponses`
- `providers` — `anthropic` and `openai` together
- `calc` — `simpleeval`, needed by the `calculate` function

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
