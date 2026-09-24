# Refine Playbook

How to improve the skills and agents that already exist. Refining an existing skill usually
pays off more than extracting a new one: a skill that never triggers, or triggers and is wrong,
is worse than no skill.

## 0. Safety first

- The skill root must be under git (`git -C <root> rev-parse --show-toplevel`). If it isn't,
  stop and offer to `git init` it and commit a baseline. Never bulk-edit untracked skills.
- When running git: unset `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and `GIT_COMMON_DIR`, and
  check `rev-parse --show-toplevel` before any commit.
- Plugin-managed skills and agents (under `~/.claude/plugins/`) and `synced/` are read-only. Report on them only.
- Keep **one commit per skill or agent**, with the message `refine(<name>): <what changed>`, so
  any single change can be reverted.

## 1. Inventory

Run the read-only auditor:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py              # all default roots
python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py --only foo bar
python3 ${CLAUDE_SKILL_DIR}/scripts/audit.py --json > /tmp/audit.json
```

It catches the mechanical problems: broken or missing frontmatter, thin descriptions or ones
with no trigger, over 1024 chars, legacy keys, too long, stale or undated, retired model IDs,
credential-like strings, broken links, name/dir mismatch, overlap between descriptions, and
hints for side effects, agents and rules.

The script only finds candidates. The judgement below is yours.

## 2. Triage: one verdict per item

For each flagged item, read the whole file, then pick exactly one verdict:

| Verdict | When | Action |
|---|---|---|
| **fix-header** | Frontmatter broken/missing, name mismatch, thin/no-trigger description, legacy keys | Rewrite frontmatter per `skill-standard.md`. Body untouched |
| **refresh** | Facts may be outdated: tool/library versions, CLI flags, APIs, model IDs, dates > ~6 months | Verify against current docs (Context7 / official docs / web). Change only what the evidence shows |
| **simplify** | Too long, repetitive, essay-style, generic advice the model already knows | Cut to procedure. Move reference material to `references/`. Drop generic content |
| **merge** | Two items cover the same trigger or domain | Keep the better-named one and fold the other's unique content in. The loser gets `status: deprecated` + `superseded_by`, or is deleted if it's fully covered |
| **split** | One skill covers unrelated triggers | Split into focused skills with their own descriptions |
| **reclassify** | It's really an agent, a CLAUDE.md rule, a hook, or memory (see the table in `skill-standard.md`) | Propose the move. Never move without approval |
| **deprecate** | The tool or pattern is gone, or it's replaced by official behavior | `metadata.status: deprecated` + reason + replacement. Archive later |
| **ok** | Nothing material | Only stamp `last_verified` if you actually checked the content |

Heuristics:
- **A good description beats a good body.** Fix undiscoverable skills first.
- **Refresh from evidence, not memory.** Your training data is older than the docs. When a
  claim can be checked (a flag exists, a default changed, a version number), check it. When it
  can't, leave it and add a `Notes` line saying it wasn't re-verified.
- **Project or ops skills** (IPs, hostnames, service layout): verify against the live system when
  it's reachable and read-only (e.g. `docker ps`, `curl -I`). Otherwise leave the content alone.
- **Credential-like values:** replace them with `<PLACEHOLDER>` and tell the user to rotate the
  credential if it looks real. Don't just delete it silently.
- **Don't homogenize away specifics.** Exact error strings, versions and file paths are what make a skill
  trigger and work. Keep them.

## 3. Report first

Before editing anything, show one table:

```
| # | item | kind | verdict | why (evidence) | planned change |
```

Group by verdict. Put `reclassify`, `merge`, `deprecate` and every body rewrite on a list that
**needs approval**. Mechanical `fix-header` changes can be pre-approved as a batch if the user
agrees.

## 4. Apply

For each approved item:

1. Edit the file(s).
2. Bump `metadata.version`: patch for header/wording, minor for new or updated facts or a
   new variant, major for a split, merge, deprecation or changed behavior.
3. Set `metadata.last_verified` to today, but only if you verified the content.
4. Re-run `audit.py --only <name>` and confirm it's clean (or only has accepted infos).
5. Commit: `refine(<name>): <verdict> — <one line>`.

## 5. Summarize

List the items changed (with commit hashes), the items proposed but not done, and anything the
user must do by hand (rotate a credential, confirm a live-system fact).

## Fix-on-use (in-session refine)

If during normal work a loaded skill turns out **wrong, outdated or incomplete** (a step failed,
a flag no longer exists, you needed an extra step), then after the task:

1. Update that skill with the corrected step and the evidence (the exact error, the new doc link).
2. Bump the minor version and set `last_verified`.
3. If it didn't trigger when it should have, add the missed symptom or phrasing to its description.
4. Tell the user in one line what you changed.

This feedback loop is what keeps a skill library accurate over time.
