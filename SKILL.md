---
name: claudeception
description: >-
  Continuous learning for skills and agents: extracts new skills from work sessions and refines
  existing ones (refresh stale facts, fix undiscoverable descriptions, simplify, merge
  duplicates, reclassify skill vs agent vs rule). Use when: (1) /claudeception, /claudeception
  refine, or /claudeception audit, (2) "save this as a skill", "what did we learn?", "improve,
  update, clean up or audit my skills/agents", (3) after a task needing non-obvious debugging,
  workarounds, or trial-and-error, (4) a skill you just used turned out wrong, outdated, or
  failed to trigger.
argument-hint: "[extract | refine [name...|--stale] | audit]"
metadata:
  author: blader, extended by ziv-daniel
  version: "4.0.0"
  last_verified: "2026-09-24"
---

# Claudeception

A continuous learning loop for a skill library, with three modes:

| Mode | Trigger | Does |
|---|---|---|
| **Extract** | `/claudeception`, end of session, non-obvious discovery | Turns new knowledge into a skill, or into an update of an existing one |
| **Refine** | `/claudeception refine [names or --stale]`, "improve/clean up my skills/agents" | Audits and improves existing skills and agents |
| **Fix-on-use** | A skill you just used was wrong, stale, or didn't trigger | Corrects that skill right away |

`/claudeception audit` runs only the read-only report from Refine step 1.

All modes write to the same standard: **[references/skill-standard.md](references/skill-standard.md)**
(frontmatter, descriptions, size, skill vs agent vs rule) and
**[references/agent-standard.md](references/agent-standard.md)** for subagents. Read the relevant one
before writing.

Skill roots, project first: `.claude/skills/`, `~/.claude/skills/`, `~/.agents/skills/`, `~/.codex/skills/`.
Agent roots: `.claude/agents/`, `~/.claude/agents/`. Treat plugin (`~/.claude/plugins/`) and `synced/` content as read-only.

---

## Extract mode

### When it's worth it

Extract only knowledge that is:
- **Reusable**: it will help future tasks, not just this one.
- **Non-trivial**: it took discovery; a docs lookup or general knowledge wouldn't have been enough.
- **Specific**: you can state the exact trigger (error text, symptom, context) and the fix.
- **Verified**: it actually worked in this session.

Typical sources: a misleading error and its real root cause, a workaround for a tool
limitation, an undocumented config or project convention, or a multi-step process that could
be streamlined.

Skip: mundane fixes, anything the model already knows, copies of official docs, and anything
unverified.

### Steps

1. **Search existing skills and agents first.** Most learnings belong in an existing skill.
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py --json | python3 -c "import json,sys; [print(i['name'],'—',i.get('description','')[:120]) for i in json.load(sys.stdin)['items']]"
   rg -il "exact error text|tool name|config key" ~/.claude/skills .claude/skills 2>/dev/null
   ```
   | Found | Action |
   |---|---|
   | Nothing related | Create new |
   | Same trigger and same fix | Update the existing skill (minor version bump) |
   | Same trigger, different root cause | Create new, and add `See also:` links in both directions |
   | Same domain, different trigger | Add a "Variant" section to the existing skill |
   | Existing skill is stale or wrong | Fix it (Refine rules), don't duplicate it |
2. **Decide the form.** Use the "Skill vs. something else" table in the standard. A one-line rule
   belongs in CLAUDE.md, a deterministic trigger belongs in a hook, and self-contained verbose
   work belongs in an agent. Propose non-skill forms to the user instead of writing a skill.
3. **Research when it's tech-specific.** Check current docs (Context7 or official docs; web search
   for errors) for anything version-dependent. Cite sources in `## References`. Skip this for
   project-internal knowledge.
4. **Write it** from [references/skill-template.md](references/skill-template.md), following the
   standard. The description matters most: lead with the use case, then "Use when: (1)…" with
   exact error strings, then the key tools and versions. Keep it ≤1024 chars and use a `>-` block scalar.
5. **Save it** to `.claude/skills/<name>/SKILL.md` if it's project-specific, otherwise to
   `~/.claude/skills/<name>/SKILL.md`. Put helpers in `scripts/` and long reference material in `references/`.
6. **Validate** with `python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py --only <name>`. Fix every error and warn it reports.
   Commit the change if the root is a git repo.

### Retrospective (`/claudeception` at the end of a session)

Review the session. List the candidates with a one-line justification each, and include
**updates to existing skills** as candidates (skills that were used and needed correcting).
Do the top 1–3, then report what was created or updated and why.

---

## Refine mode

Follow **[references/refine-playbook.md](references/refine-playbook.md)**. In short:

0. **Safety.** The root must be a git repo (offer `git init` + a baseline commit if it isn't). Strip `GIT_*` env vars.
   Plugin and synced content is report-only.
1. **Inventory.** Run `python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py [--only names]`. It's read-only.
2. **Triage** each flagged item after reading it in full, with one verdict each: `fix-header`, `refresh`,
   `simplify`, `merge`, `split`, `reclassify` (skill ↔ agent ↔ rule ↔ hook ↔ memory), `deprecate` or `ok`.
3. **Report first.** Show a table of item, verdict, evidence and planned change. Structural changes
   (merge, split, reclassify, deprecate, body rewrites) need the user's approval.
4. **Apply** one commit per item. Bump `metadata.version`. Set `last_verified` only if you checked the facts.
   Re-run the audit on that item.
5. **Summarize** the changes (with commits), what was deferred, and any manual follow-ups (e.g. rotate a leaked credential).

Principles:
- **Discoverability first.** A skill with a broken or vague description is invisible. Fix those before anything else.
- **Refresh from evidence, not memory.** Your training data is older than current docs, so verify
  version-dependent claims. Mark anything unverifiable in `Notes` instead of guessing.
- **Simplify.** Cut generic advice the model already knows, keep the exact specifics (error
  strings, flags, paths), and move bulk to `references/`.
- **Model-agnostic.** No model-specific quirks and no retired model IDs.

---

## Fix-on-use

When a skill you loaded during the task turns out wrong, outdated, incomplete, or didn't
trigger when it should have, fix it right after the task. Correct the step and add the evidence,
add the missed trigger phrasing to the description, bump the minor version, set `last_verified`,
and tell the user in one line. See the end of the playbook.

---

## Quality gates (every write)

- [ ] Frontmatter parses. `name` matches the directory. Only spec keys plus behavior-changing Claude Code keys are used.
- [ ] The description leads with the use case, has "Use when" triggers with exact symptoms, and is ≤1024 chars.
- [ ] The body is procedural, under 500 lines (ideally under 200), and details live in `references/`.
- [ ] The solution was verified. Web sources are cited in `## References`.
- [ ] No secrets, tokens, or personal data (use `<PLACEHOLDER>`).
- [ ] It doesn't duplicate an existing skill; cross-links are added both ways.
- [ ] `metadata.version` is bumped. `last_verified` is set only when the content was checked.
- [ ] `audit.py --only <name>` is clean.
