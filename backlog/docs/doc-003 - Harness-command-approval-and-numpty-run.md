---
id: doc-003
title: Harness command approval and numpty run
type: other
created_date: '2026-10-01 20:20'
updated_date: '2026-10-06 22:22'
---
# Harness command approval and `numpty run`

Research for NUMP-009 (2026-10-01). This document records how two agent harnesses approve shell commands, and what that means for the `numpty run` command line.

Sources:

- Claude Code: https://code.claude.com/docs/en/permissions.md, read on 2026-10-01.
- Codex CLI: the `openai/codex` repository at commit `57a38c1b` (main, 2026-10-01), and https://learn.chatgpt.com/docs/agent-configuration/rules. Paths below are relative to `codex-rs/`.

## Problem

A reviewer approves a command pattern once. After that, the harness runs each matching command with no prompt. Each harness matches the command text or its words. It does not parse the arguments of `numpty`. Thus the harness does not check the text after the approved prefix.

If an argument after the prefix can widen the policy, an approval for a narrow policy also approves a wide one. Examples:

- `numpty run -p FS_READ -p UNRESTRICTED` matches a rule for `numpty run -p FS_READ`.
- `numpty run -p FS_READ,FS_WRITE_LOCATION -l /` matches a rule that has no `-l`. The default location (the current directory) changes to `/`.

The command line must make sure that no text after a complete approved prefix can widen the policy. This document calls that property "suffix-safe".

## Claude Code

Facts from the permissions documentation:

- Bash rules match the whole command text. A `*` matches any text, including spaces. A rule with no `*` matches one exact command.
- The space before a trailing `*` is part of the rule. `Bash(ls *)` matches `ls -la` but not `lsof`. `Bash(ls*)` matches both.
- `Bash(prefix:*)` is the same as `Bash(prefix *)`. The `:*` form is recognized only at the end of a pattern.
- A `*` can occur at any position in a rule.
- The permission dialog writes the space form when the user selects "Yes, and don't ask again".
- The dialog offers "don't ask again" only when the prompt can show everything that the saved rule allows.
- Claude Code splits compound commands at `&&`, `||`, `;`, `|`, `|&`, `&`, and newlines. An allow rule must match each subcommand.
- Deny and ask rules apply when any subcommand matches, also inside subshells and command substitutions.
- The order of evaluation is deny, then ask, then allow. A deny rule wins over a more specific allow rule.
- Here-docs and here-strings are not checked as redirection targets.
- Saved Bash rules go to `.claude/settings.local.json` at the repository root.

Results for `numpty run`:

| Rule | Command | Match |
|---|---|---|
| `Bash(numpty run -p FS_READ *)` | `numpty run -p FS_READ,UNRESTRICTED` | No. The rule needs a space after `FS_READ`. |
| `Bash(numpty run -p FS_READ *)` | `numpty run -p FS_READ -p UNRESTRICTED` | Yes |
| `Bash(numpty run -p FS_READ*)` | both commands above | Yes |
| `Bash(numpty run -p FS_READ,FS_WRITE_LOCATION -l ~/proj*)` | `... -l ~/proj/../..` | Yes |

- "Sometimes a permission prompt offers only a one-time approval." The dialog offers a saved rule "only when the prompt can show you everything" that the rule allows.

Not documented:

- How the dialog chooses the prefix that it offers to save. See "Observed in the Claude desktop app" below.
- Whether the newlines in a here-doc body split the command into subcommands. If they do, a `numpty run ... <<'EOF'` command does not match a `numpty run` rule. Test this before the CLI design depends on here-docs.
- Whether a command that fails has an effect on approvals. Approval occurs before the command runs, so an effect is not likely.

### Observed in the Claude desktop app

Observations from the Code tab of the Claude desktop app on 2026-10-01. The desktop documentation (https://code.claude.com/docs/en/desktop.md) describes "Always allow" only for websites, not for Bash commands.

- The Bash prompt no longer says "Yes, and don't ask again". It offers "Always allow".
- Some prompts offer only "Allow" and "Deny". This agrees with the documented rule about one-time approvals. Which commands get only two options is not known.
- Prefix rules are in use. In this session, approvals saved these rules to `.claude/settings.local.json`:
  - `Bash(backlog instructions *)`
  - `Bash(backlog task *)`
  - `Bash(backlog doc *)`
- The approved commands were `backlog doc create "<title>"` and `backlog doc update doc-003 --content ...`. The saved rule `Bash(backlog doc *)` also allows `backlog doc` commands that the user did not see, for example a delete.
- Each saved rule has the form "program, subcommand, ` *`". The permissions documentation recommends this form for rules that a user writes. Three examples are not proof that the dialog always uses it.

Inferred results for `numpty run`:

- One "Always allow" on a `numpty run -p ...` command probably saves `Bash(numpty run *)`. That rule allows every policy, `UNRESTRICTED` included.
- With that rule, an appended option cannot widen anything, because the rule already allows everything.
- A rule for one policy exists only if a person writes it, for example `Bash(numpty run -p FS_READ,FS_WRITE_NONE *)`.
- A deny rule such as `Bash(numpty run *UNRESTRICTED*)` can block some wide policies. Deny rules win over allow rules.
- Possible design response: put the policy in the subcommand name (for example `numpty run-readonly`). The default "program, subcommand" rule then also fixes the policy. Not evaluated.

## Codex CLI

Facts from the documentation (D) and the source (S):

- (D) Rules are `prefix_rule(pattern=[...], decision=...)` entries in `~/.codex/rules/*.rules`, and in `<repo>/.codex/rules/` for trusted projects. When more than one rule matches, the strictest decision wins: `forbidden`, then `prompt`, then `allow`. Rules are experimental.
- (S) `execpolicy/src/rule.rs:46-59`: matching compares words. Each pattern word must equal the command word, or equal one alternative in a list. Words after the pattern are ignored. There is no glob, regex, substring, or whole-command match.
- (S) `core/src/exec_policy.rs:372-374`: a rule for `numpty` also matches `/abs/path/numpty`, unless a `host_executable()` entry limits the paths.
- (S) `shell-command/src/bash.rs:29-130`, `core/src/exec_policy.rs:876-904`: Codex parses `bash -lc "<script>"` with tree-sitter. It splits the script only when the script has plain words, quotes, and `&& || ; |`. A redirection, here-doc, `$(...)`, variable, subshell, or glob stops the split. Codex then checks the whole argv `["bash", "-lc", "<script>"]` as one command.
- (S) `core/src/exec_policy_tests.rs:752`: a here-doc command does not match an allow rule for the inner command.
- (S) `core/src/tools/sandboxing.rs:71-115`: "Yes, and don't ask again for this command in this session" keeps the exact command in memory. It is not a prefix.
- (S) `core/src/exec_policy.rs:464-512`: "Yes, and don't ask again for commands that start with X" adds `prefix_rule(pattern=X, decision="allow")` to `~/.codex/rules/default.rules`.
- (S) `core/src/exec_policy.rs:958-1020`: the model can propose X on the tool call. Codex refuses a proposal on its banned list (for example `bash`, `python`, `python -c`, `env`, `git`). `numpty` is not on the list. Thus the model can propose `["numpty", "run"]`. If the model proposes nothing, Codex proposes the full argv.
- (S) `tui/src/bottom_pane/approval_overlay.rs:850-856`: the TUI does not offer a prefix rule when the prefix has a newline. Here-doc commands get only "once" or "this session".
- (S) `sandboxing/src/denial.rs`, `core/src/tools/orchestrator.rs:426-530`: after a failure, Codex can offer to run the command again outside its sandbox. It does this only for a failure that it classifies as a sandbox denial. Exit codes 2, 126, and 127 are never classified as a denial. The output must also contain words such as "permission denied" or "sandbox". The offer occurs only in the `untrusted` mode, or in `granular` mode with `sandbox_approval`.
- (D, S) `core/src/exec_policy.rs:440-454`: a command that matches an explicit `allow` rule runs outside the Codex sandbox. A command that Codex allows by its built-in rules stays in the sandbox.

Results for `numpty run`:

| Rule | Command | Match |
|---|---|---|
| `["numpty", "run", "-p", "FS_READ"]` | `numpty run -p FS_READ,UNRESTRICTED` | No. The word is different. |
| `["numpty", "run", "-p", "FS_READ"]` | `numpty run -p FS_READ -p UNRESTRICTED` | Yes |
| `["numpty", "run", "-p", "FS_READ"]` | `numpty run -p FS_READ <<'EOF' ... EOF` | No. Codex checks `bash -lc` as one command. |

Other results:

- An allowlisted `numpty run` runs outside the Codex sandbox. The numpty policy is then the only limit.
- A `numpty run` command with a here-doc cannot match a `numpty` rule. In `on-request` mode, it runs in the Codex sandbox with no prompt. Both limits then apply.
- The numpty exit codes 2 (usage error) and 126 (policy denial) never start the "run outside the sandbox" offer.
- If the code catches a denial and exits with code 1, the fastaudit message ("blocked in sandbox") can start the offer in `untrusted` mode.

## Facts for the CLI design

- Both harnesses check only a prefix. Text after the prefix is free.
- Neither harness splits one word. A value that has commas (`FS_READ,FS_WRITE_LOCATION`) is one word. A Claude Code rule in the space form, or any Codex rule, cannot match a longer value. A Claude Code rule with no space before `*` can match it.
- A repeated option (`-p ... -p ...`) or an option that the prefix does not have (`-l /`) matches both harnesses.
- A command that `numpty` rejects before it runs code does nothing. Neither harness changes its approvals after a failure.
- The Claude Code dialog saves the space form. The Codex model can propose a short prefix such as `numpty run`. A reviewer who accepts it approves every policy.
- Codex cannot allowlist a `numpty run` command that has a here-doc. Code in an argument (for example a `-c CODE` option) can match a rule.

## Candidate design (not decided)

From the NUMP-009 review on 2026-10-01:

- The command line must declare a full policy. There are no defaults. A full policy has one value for each dimension that can be set: read, write, and the location when a `_LOCATION` scope is used.
- Each dimension has exactly one definition. A second definition is an error (exit 2). The values can be in one `-p` with commas, or in more than one `-p`.
- "Policy" stays an abstract, documented concept. `--policy` is reserved for a future concrete form.

Open items:

- The name for "no write", because there are no defaults.
- Whether the CLI accepts network, process, and C extension flags. If it does, each must be a required dimension.
- Whether `-l` is an error when no `_LOCATION` scope is used.
- Whether `-t` can occur only once.
- The documentation must tell reviewers to end a Claude Code rule with ` *` (space, then star), not `*`.
- The documentation must tell reviewers that "Always allow" probably saves `Bash(numpty run *)`, and that a rule for one policy must be written by hand.

## Direction (2026-10-01)

The harness behavior is partly undocumented and changes between versions. Start with a best-effort CLI design. Test it in Claude Code and Codex, and change it based on the results.


## Decision (2026-10-06)

The CLI keeps the original design. The candidate design above (full policy required, no defaults) is not adopted.

- No option is required. The defaults are `Policy()`: `FS_READ`, no write, no network, no process. The CLI and the tool have the same defaults.
- Defaults are per dimension (filesystem read, append, write; network read, write; process). A dimension that no `-p` name sets takes the strictest policy enforceable today, which is `Policy()`'s value for it. Reads cannot be restricted now, so the read default is `FS_READ`; `-p FS_WRITE_LOCATION` alone is `FS_READ | FS_WRITE_LOCATION` and runs. When read restriction is implemented, the read default becomes none (or the strictest available) with no CLI change, and `-p FS_WRITE_LOCATION` then means no read. Leaving a flag out never errors. This keeps "no read" expressible without a new flag.
- `-p/--permission` accepts every slot: `FS_*`, `NET_*`, `PROC_*` (with `PROC_C_EXTENSIONS`), and `UNRESTRICTED`. Network, process, and C extensions are CLI dimensions.
- No repeat and no override. A second `-p`, `-l`, or `-t` is a usage error (exit 2).
- `-l` without a `_LOCATION` scope in the policy writes a warning to stderr. The run continues.

Reasons:

- The intended use (a reviewer approves a short command with a visible policy) does not agree with how Claude Code and Codex save an approval. "Always allow" saves a prefix such as `Bash(numpty run *)`, which allows every policy.
- The apparent fix is a default-allow style, where a rule names what is permitted and the command line is trusted. fastaudit and `Policy` are default-deny. The two styles contradict each other, and no design on paper shows which reconciliation works.
- Hands-on experience decides. Implement, run `numpty run` through approvals in Claude Code and Codex, and revise the CLI from the results.

Open items closed by this decision: the name for "no write" (not needed, defaults exist), the extra dimensions (accepted), `-l` without `_LOCATION` (warn), and `-t` (once). Items that remain for the hands-on round are listed in NUMP-009 under "Follow-up after implementation".
