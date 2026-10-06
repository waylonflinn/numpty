---
id: NUMP-019
title: 'Research spike: test numpty run approvals hands-on in Claude Code and Codex'
status: To Do
assignee: []
created_date: '2026-10-06 22:43'
labels:
  - research
dependencies:
  - NUMP-009
documentation:
  - doc-003 - Harness command approval and numpty run
type: spike
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up planned in NUMP-009 (2026-10-06). 'numpty run' lets a reviewer approve a short command and a simple policy instead of a long script. The CLI design (no required option, Policy() defaults per dimension, -p/-l/-t at most once) was chosen without hands-on harness tests. doc-003 has only inferred behavior: 'Always allow' in Claude Code probably saves 'Bash(numpty run *)', which allows every policy, UNRESTRICTED included. Claude Code matches rules on command text, Codex on words. An option that is not in an approved rule can be appended after the prefix, for example '-l /' after 'numpty run -p FS_WRITE_LOCATION', which moves the write scope. Open question from NUMP-009: the harness 'Always allow' is default-allow in style, while fastaudit and Policy are default-deny. Experience is to decide how to reconcile them. Candidate CLI changes already named in doc-003: a subcommand per policy (for example 'numpty run-readonly') and a '-c CODE' option for Codex allowlisting. Decision expected.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Doc records what 'Always allow' saves for a 'numpty run' command in the Claude Code CLI, the Claude Code desktop app, and Codex CLI, with the harness versions tested
- [ ] #2 Doc records, for each harness, whether a hand-written rule for one policy (for example -p FS_WRITE_LOCATION -l .) allows that policy and blocks a wider one: an appended -p, -l, or UNRESTRICTED, and a reordered command
- [ ] #3 Doc records whether stdin code (heredoc or pipe) changes how each harness matches or displays the command, and whether a '-c CODE' option would match better in Codex
- [ ] #4 Doc assesses the default-allow harness style against the default-deny Policy, and compares at least: no CLI change (documentation only), a subcommand per policy, required options, and '-c CODE'
- [ ] #5 Decision record states the CLI changes to make and the follow-up task(s) they need, or states that no change is needed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 doc records reasoning and sources
- [ ] #2 decision record produced
<!-- DOD:END -->
