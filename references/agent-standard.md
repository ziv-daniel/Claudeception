# Subagent Standard

Target shape for subagents Claudeception refines (`~/.claude/agents/*.md`, `.claude/agents/**/*.md`).
Plugin agents (`plugin:name`) are **read-only**: report findings, never edit plugin caches. Changes
there get overwritten on update. To customize one, copy it to `~/.claude/agents/` under a new name.

Docs last checked: 2026-09-24 (https://code.claude.com/docs/en/sub-agents).

## Frontmatter

```yaml
---
name: api-contract-auditor           # unique, no ':' and no leading '-'
description: >-                      # ~100–200 chars. All agent descriptions share a 15k-token budget
  Compares frontend API types/mocks with real backend responses. Use proactively after API
  or DTO changes.
tools: Read, Grep, Glob, Bash        # least privilege. Omitting it inherits EVERY tool
disallowedTools: Write, Edit         # alternative: inherit all but these
model: sonnet                        # alias (sonnet/opus/haiku/fable) or inherit. Never a pinned retired ID
effort: medium                       # optional
skills: [api-contract-drift-hidden-by-mocks]   # preload domain knowledge instead of pasting it
memory: user                         # optional: agent keeps notes in ~/.claude/agent-memory/
maxTurns: 30                         # optional safety cap
---
```

## System prompt (body)

The agent gets **only** this prompt plus environment details, not Claude Code's system prompt
and not the conversation. So:

1. **Role + scope in 1–2 lines.** What it owns, and what it must not touch.
2. **Procedure.** Numbered steps it follows.
3. **Output contract.** The exact shape to return (e.g. "≤15 bullets, each `file:line — issue — fix`",
   or a JSON schema). An agent with no output format rambles, and the parent pays for it in context.
4. **Stop conditions.** When to stop and report instead of guessing.
5. **Knowledge through `skills:`,** not pasted in. If the prompt is >250 lines of domain facts, extract a
   skill and preload it.
6. If `memory` is set, say when to read and when to update it.

## Refine checks

- Description missing a delegation cue ("Use proactively after…", "Use when…").
- `tools` omitted on a read-only role, which is over-privileged.
- A pinned or retired `model`. Prefer an alias or `inherit`.
- No output contract, no stop condition.
- Duplicates another agent or a skill. Merge, or keep the agent and preload the skill.
- A skill that is really an agent: persona, self-contained, verbose output, returns a summary.
  Propose converting it, keeping the knowledge as a skill the agent preloads.
- An agent that is really a skill: needs the conversation context or iterates with the user.
  Propose converting it the other way.
