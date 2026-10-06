# Web UI: link task documentation entries to documents and decisions

## Problem

A task's `documentation` field often points at a Backlog document, for example `doc-004`. The web UI renders this entry as plain monospace text. It makes a link only when the entry starts with `http://` or `https://`. The reader must open the Documentation page and find the document by hand.

Observed in v1.53.0, task detail view, Documentation section.

## Workaround

A full URL works, for example `http://localhost:6420/documentation/4/structured-output-across-providers-and-jev`. This has three costs:

- The URL binds the task to a port.
- The link text is the raw URL, not the document title.
- The entry loses the `doc-004` id that the CLI uses.

The current compromise is a plain entry like `doc-004 - Structured output across providers and Jev`. This matches the output of `backlog doc list --plain`, so it is readable and greppable, but it is not clickable.

## Proposal

When a documentation entry matches a document or decision id, render it as an internal link:

- `doc-004` and `doc-004 - Any title` link to `/documentation/4/<slug>`.
- `decision-003` and `decision-003 - Any title` link to `/decisions/3/<slug>`.
- Show the stored entry text as the link text. If the entry is only an id, show the resolved document title after it.
- Entries that match no known id render as they do today.

The same lookup also helps the `references` field, if it applies there.

## Why

Task metadata already uses ids as the stable key. The CLI accepts `doc-004` on the command line, and the web UI already builds document routes from `id` and `title` for the side navigation. Resolving ids in the Documentation section makes the two interfaces agree on one format and removes the need for port-bound URLs.
