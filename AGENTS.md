
<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.50.1 -->
<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**For every user request in this project, run `backlog instructions overview` before answering or taking action.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:
- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>
<!-- BACKLOG.MD GUIDELINES END -->

## Coordination conventions

Tasks pass through a **Planning** status before In Progress: claim into
Planning, record the plan, request review, and wait for approval before
implementing.

## Status lifecycle

`To Do -> Planning -> In Progress -> Done`

- **Claim:** the first write of a working session is
  `backlog task edit <id> -s 'Planning' -a @<name>`. Where the CLI execution
  guide says "mark it in progress," the active status for claiming in this
  project is **Planning**.
- **Planning phase:** research the system, draft the implementation plan
  (`--plan`). If the work exceeds one session /
  one reviewable outcome, create subtasks before requesting review; each
  subtask passes through its own Planning gate.
- **Planning is a review gate.** After recording the plan, stop. Do not move
  the task to In Progress or write implementation code until the plan is
  approved. Signal readiness:
  `backlog task edit <id> --comment "Plan ready for review" --comment-author @<name>`.
- **Approval:** a human approves in-session or by comment; only then
  `backlog task edit <id> -s 'In Progress'`.
- **Re-planning:** a material change of approach during implementation
  returns the task to Planning and re-enters the gate.
- **Queries:** plans awaiting review: `backlog task list -s Planning --plain`.
  The frontier query is unchanged (To Do is the takeable pool; Planning tasks
  are claimed, not takeable).