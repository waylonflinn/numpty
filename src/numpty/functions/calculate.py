"""Math expression evaluation. Needs the `calc` extra. `simpleeval` loads on first call."""

import math
import random
from functools import cache
from typing import Annotated

functions = {"sqrt": math.sqrt, "log": math.log, "exp": math.exp, "cos": math.cos, "sin": math.sin, "tan": math.tan,
             "rand": random.random, "int": int}


@cache
def _evaluator():
    try:
        from simpleeval import SimpleEval
    except ImportError as e:
        raise ImportError("calculate requires simpleeval: pip install 'numpty[calc]'") from e
    return SimpleEval(functions=functions)


def calculate(
    expression: Annotated[str, f"A valid mathematical string to evaluate, e.g., '3 * sqrt(9) + 4'. Includes functions for { ", ".join(list(functions.keys()))}.  'rand' returns a float in [0, 1). "]) -> float:
    """Evaluate a math expression. Needs the `calc` extra.

    | Operator          | Meaning        | Example            |
    |-------------------|----------------|--------------------|
    | `+`               | add            | `1 + 1` → `2`      |
    | `-`               | subtract       | `100 - 1` → `99`   |
    | `*`               | multiply       | `10 * 10` → `100`  |
    | `/`               | divide         | `100 / 10` → `10`  |
    | `**`              | power          | `2 ** 10` → `1024` |
    | `%`               | remainder      | `15 % 4` → `3`     |
    | `==`              | equal          | `15 == 4` → `0`    |
    | `<` `>` `<=` `>=` | compare        | `1 < 4` → `1`      |
    | `>>` `<<`         | bit shift      | `100 >> 2` → `25`  |
    | `^`               | bitwise XOR    | `62 ^ 20` → `42`   |
    | `\\|`              | bitwise OR     | `8 \\| 34` → `42`   |
    | `&`               | bitwise AND    | `100 & 63` → `36`  |
    | `~`               | bitwise invert | `~ -43` → `42`     |

    Args:
        expression: Expression to evaluate.

    Returns:
        Result as a float. Comparisons give `1.0` or `0.0`.

    Raises:
        ImportError: `simpleeval` not installed.
        Exception: Invalid expression (for example `SyntaxError`, `ZeroDivisionError`).
    """
    evaluator = _evaluator()
    return float(evaluator.eval(expression))
