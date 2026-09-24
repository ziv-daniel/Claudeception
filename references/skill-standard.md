# Skill Standard

The target shape for every skill Claudeception creates or refines. It follows the
[Agent Skills spec](https://agentskills.io/specification) (portable to Codex, the Skills API
and other agents) plus the Claude Code extensions that change behavior.

Docs last checked: 2026-09-24. Re-check the two sources in "References" if this date is older
than ~3 months, and update this file first.

## Frontmatter

```yaml
---
name: kebab-case-name            # = directory name, <=64 chars, [a-z0-9-], no leading/trailing/double hyphen
description: >-                  # <=1024 chars. Block scalar, so ': ' inside the text can't break YAML
  What it does, in one sentence. Use when: (1) exact error text or symptom,
  (2) the situation/context, (3) the tool + version. Key terms a user would type.
metadata:                        # string values only; Claude Code ignores this map
  author: claudeception
  version: "1.2.0"
  created: "2026-01-25"
  last_verified: "2026-09-24"    # last date the content was checked against reality/docs
  status: active                 # active | deprecated
  superseded_by: other-skill     # only when deprecated
---
```

Rules:

- **Only spec keys at top level**: `name`, `description`, `license`, `compatibility`,
  `metadata`, `allowed-tools`. Legacy top-level `author`/`version`/`date` go under
  `metadata` (Skills API uploads reject unknown top-level keys; Claude Code ignores them).
- **Claude Code-only keys are allowed only when they change behavior**:
  - `disable-model-invocation: true`: skills with side effects (deploy, publish, send, delete, restart).
  - `paths:`: skills that only matter for certain files (`"**/*.tf"`).
  - `context: fork` + `agent:`: self-contained work whose output you don't need in the main context.
  - `allowed-tools`: only when it pre-approves something specific. Never an empty list.
  - Do **not** use `when_to_use`. Put triggers in `description` so one field works in every agent.
- **YAML must parse.** If it doesn't, Claude Code loads the skill with *no* fields, which makes it
  invisible to model invocation. The common cause is an unquoted `: ` or `#` inside the
  description. Always use `>-` block scalars for descriptions.
- **The file must start with `---` on line 1.** A skill without frontmatter falls back to its first
  Markdown line as description ("# Some Title"), which almost never triggers.

## Description (the part that decides whether the skill is ever used)

Only `name` + `description` sit in context before invocation, and they're all the model sees.
Write it for retrieval:

1. **Lead with the key use case.** Listings truncate, so the first ~200 chars must stand alone.
2. **Trigger conditions**, in the form "Use when: (1) … (2) …". Include exact error strings, symptoms,
   commands, file names, and product names/versions.
3. **What it is NOT for**, when a sibling skill is easily confused ("Not for X, see other-skill").
4. Third person, no marketing, no "This skill…". Aim for 250–700 chars. Hard max 1024.

Bad: `Fix bcrypt native module errors on ARM64/Raspberry Pi Docker containers.` (no trigger, no error text)

Good:
```
Fix bcrypt native-module crashes in Node Docker images on ARM64 (Raspberry Pi, Apple Silicon
builders). Use when: (1) container logs "Error: .../bcrypt_lib.node: invalid ELF header" or
"Exec format error", (2) node_modules was copied from an x86 host into the image, (3) an Alpine
image lacks build tools for node-gyp. Covers rebuilding in-image, bcryptjs fallback, and
multi-arch buildx.
```

## Body

- **Under 500 lines, ideally under 200.** The whole body is loaded on invocation and stays in
  context. Move long reference material to `references/<topic>.md` and link to it one level deep.
  Put runnable helpers in `scripts/` and templates in `assets/`.
- **Imperative and procedural.** Steps the model executes, not an essay. Lead with the fix.
- **Required sections** (merge or skip any that would be empty):
  `## Problem` · `## Trigger conditions` · `## Solution` · `## Verification` · `## Notes` · `## References`
- **Model-agnostic.** Don't name a specific model or rely on one model's quirks. Describe the
  tool/API behavior instead. Never hardcode retired model IDs (`claude-3-*`, `claude-2`).
- **Tool-agnostic where cheap.** Write "search the codebase" rather than a specific tool name,
  unless the exact tool is the point.
- **No secrets, no personal data.** Use placeholders like `<API_KEY>`. Hostnames and IPs are fine only in
  personal ops skills that live outside any shared repo.
- **Dates are absolute** ("since v5.2, 2026-03"), never "recently" or "new".

## Library budget

Every listed skill's description costs context on every turn. Once the listing is too big (many
personal skills plus large plugins), Claude Code shows some skills **by name only**, and a name
alone rarely triggers auto-invocation. So:

- Fewer, sharper skills beat many overlapping ones. Merge near-duplicates.
- User-only workflows (deploys, ops runbooks you call by name) get
  `disable-model-invocation: true`, which drops them from the listing entirely.
- Rarely used skills can be demoted without deleting them, through `skillOverrides` in settings.json
  (`"name-only"`, `"user-invocable-only"`, `"off"`).
- Disable plugins whose skills you never use.
- Measure with `/skill-doctor`, which shows each skill's cost and how often it's used.

## Skill vs. something else

| The knowledge is… | Put it in |
|---|---|
| A reusable procedure/diagnosis the model runs in the main conversation | **Skill** |
| Self-contained work that produces verbose output, or needs its own tool limits, model or persona, and returns a summary | **Subagent** (`~/.claude/agents/`), preloading a skill via `skills:` if it needs the knowledge |
| A one-line always/never rule that applies to every session in a project | **CLAUDE.md / rules** |
| Something that must happen deterministically on an event (format on save, block a command) | **Hook** in settings.json |
| A fact about the user, the project state, or a pointer to a resource | **Memory** |
| Official docs you'd just be copying | Nothing. Link it from the skill that needs it |

## References

- Claude Code skills: https://code.claude.com/docs/en/skills
- Agent Skills spec: https://agentskills.io/specification
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
