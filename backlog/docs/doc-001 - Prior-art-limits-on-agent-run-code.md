---
id: doc-001
title: 'Prior art: limits on agent-run code'
type: other
created_date: '2026-09-25 22:30'
updated_date: '2026-09-25 22:30'
---
# Prior art: limits on agent-run code

Survey done on 2026-09-25 for NUMP-008 and the tasks that follow it (NUMP-009 to NUMP-012). The question: can numpty limit what Python code does, including code in libraries such as pandas?

## Summary

There are two classes of solution:

- **In-process guardrails.** A Python-level check runs inside the interpreter. These catch accidental overreach. They do not stop code that tries to escape.
- **OS-level sandboxes.** The kernel enforces the policy on a whole process. These also cover C extensions, ctypes, and child processes.

numpty uses an in-process guardrail (fastaudit) first. An OS-level sandbox is later, optional work (NUMP-012). The policy interface stays the same for both.

## Python audit hooks (PEP 578)

`sys.addaudithook` registers a function that CPython calls for sensitive events, such as `open`, `os.remove`, and `subprocess.Popen`. It is the base for the in-process approach.

The CPython documentation says that audit hooks are not a sandbox. Known limits:

- Code in the same process can find and change the hook state, for example through `gc` or frame inspection.
- C extensions that do their own I/O do not raise events. An example is pyarrow, which pandas uses to write Parquet files.
- ctypes can call C library functions directly.
- A hook does not apply to a child process.

## fastaudit (Answer.AI)

fastaudit is a small library built on audit hooks. Its stated purpose is to stop accidental damage by code that an LLM writes. It does not claim to stop adversarial code. It is the closest match to the numpty use case. Refer to doc-002 (fastaudit notes) for details.

## smolagents LocalPythonExecutor (Hugging Face)

This is a custom Python interpreter. It allows only a list of safe imports and limits file I/O. The model must write code in a limited subset of Python. For stronger isolation, smolagents runs code remotely (E2B, Modal, Docker, and others). The subset approach does not fit numpty, because numpty wants normal Python with libraries such as pandas.

## llm-sandbox

A Python library that runs LLM-generated code in containers (Docker, Kubernetes, Podman). It gives strong isolation. It also needs a container runtime, which is too heavy for the numpty default.

## OS-level sandboxes

These tools apply a policy to a process at the kernel level:

- **Seatbelt** (macOS). The `sandbox-exec` command runs a process under a profile that lists allowed paths and operations. Apple marks it as deprecated, but major agent tools use it.
- **Landlock** (Linux). A kernel feature that lets a process limit its own file access. Rules apply to a directory and everything below it.
- **seccomp** (Linux). A kernel filter on system calls. Agent tools use it to block network calls.
- **bubblewrap** (Linux). A tool that runs a process in a new namespace, with bind mounts that are read-only or writable.

Known limits for the numpty policy model:

- Neither Seatbelt nor Landlock can force append-only writes.
- Landlock cannot express "the current directory only, without subdirectories". Seatbelt can.
- A policy that limits reads must also allow the interpreter, the standard library, site-packages, and the virtual environment.

## Agent tools that use OS-level sandboxes

- **Codex CLI (OpenAI).** It has policy modes such as read-only, workspace-write, and full access. It uses Seatbelt on macOS and Landlock with seccomp on Linux.
- **Anthropic sandbox-runtime.** An open-source tool that applies filesystem and network limits to any process, without a container. It uses Seatbelt on macOS and bubblewrap on Linux. It sends network traffic through a local proxy that filters requests. It is a Node package, which is a poor fit as a numpty dependency.
- **Claude Code sandboxing.** Claude Code uses sandbox-runtime for its sandboxed Bash tool. The sandbox limits writes to the working directory and filters network access.

## Other tools found

- **agentseatbelt.** A command wrapper for AI agents with a YAML policy and an audit log. It uses normal OS process permissions.
- **safer-exec (cdxgen).** An OS-level sandbox for any program, with tracing and a learning mode.
- **pysandbox.** An old attempt at an in-process Python sandbox. The author abandoned it and said that the approach cannot be made secure.

## Conclusions for numpty

1. In-process checks are useful as a guardrail against model mistakes. This matters more for local models with low reliability.
2. A hard security boundary needs an OS-level sandbox on a subprocess.
3. A policy with network access blocked still leaks data if reads are not limited. Tool output goes to the model provider.
4. The policy interface must not depend on the enforcement backend.

## Sources

- [PEP 578: Python Runtime Audit Hooks](https://peps.python.org/pep-0578/)
- [Python `sys` documentation](https://docs.python.org/3/library/sys.html)
- [cpython issue 87604: audit hook documentation limits](https://github.com/python/cpython/issues/87604)
- [fastaudit](https://github.com/AnswerDotAI/fastaudit)
- [smolagents: secure code execution](https://huggingface.co/docs/smolagents/en/tutorials/secure_code_execution)
- [llm-sandbox](https://github.com/vndee/llm-sandbox)
- [Anthropic sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime)
- [Anthropic: Claude Code sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Claude Code docs: sandboxing](https://code.claude.com/docs/en/sandboxing)
- [Codex sandbox platform implementation](https://codex.danielvaughan.com/2026/04/08/codex-sandbox-platform-implementation/)
- [A deep dive on agent sandboxes (Pierce Freeman)](https://pierce.dev/notes/a-deep-dive-on-agent-sandboxes)
- [agentseatbelt](https://github.com/neshboy/agentseatbelt)
- [safer-exec](https://github.com/cdxgen/safer-exec)
- [pysandbox](https://github.com/haypo/pysandbox)
