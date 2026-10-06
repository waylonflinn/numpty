---
id: NUMP-017
title: >-
  Research spike: should DecisionTool requests be exempt from the tool-call
  Policy
status: To Do
assignee: []
created_date: '2026-10-06 21:25'
labels:
  - research
dependencies:
  - NUMP-007
type: spike
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found during NUMP-007 (2026-10-06). `Agent.run` applies `Agent.policy` to every tool call, but not to model queries. A `DecisionTool` call sends a request to a decision model (TypeSafe or llama-server). Under `Policy()` that request fails: `TypeSafeAPIConnectionError ... socket.connect blocked`. It works only with `Policy.Network.UNRESTRICTED`, which also opens the network to every other tool of the agent. The current behavior is documented in the README (Decisions) and the `DecisionTool` docstring. Arguments both ways: a decision request is a model query in nature (fixed endpoint, chosen by the developer, not the model), so a guardrail on it may add no safety. But the model chooses the `state` text, so the request can carry file contents read by other tools to a remote host, and an exemption makes a hole in the default-deny boundary. The user is not yet convinced either way. Decision expected.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Doc states what the policy protects against today and whether a decision-model request falls inside that threat model (data exfiltration through `state`, endpoint choice, local vs remote host)
- [ ] #2 Doc compares at least: no change (document only), exempt DecisionTool requests, allow a narrower network grant (for example a host or endpoint allowlist, if Policy or fastaudit can express it), and treat the decision model as an Agent-level model rather than a tool
- [ ] #3 Doc checks what fastaudit can express today (per-host or per-call-site allowances) with a probe, and what each option costs in Policy or Tool surface (no cross-layer attributes on Tool)
- [ ] #4 Decision record states the chosen option and the follow-up task(s) it needs, or states that no change is needed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 doc records reasoning and sources
- [ ] #2 decision record produced
<!-- DOD:END -->
