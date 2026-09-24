#!/usr/bin/env python3
"""Read-only audit of skills and subagents for Claudeception refine mode.

Never writes to any skill or agent file. Emits a Markdown report (default) or JSON.

Usage:
  audit.py                              # default skill + agent dirs
  audit.py --skills DIR [DIR...]        # custom skill roots
  audit.py --agents DIR [DIR...]        # custom agent roots
  audit.py --only NAME [NAME...]        # restrict to these skill/agent names
  audit.py --stale-days 180 --json
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from itertools import combinations

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

SPEC_SKILL_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_ONLY_SKILL_KEYS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "disallowed-tools", "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
}
LEGACY_TOP_LEVEL = {"author", "version", "date", "last_verified", "tags"}
AGENT_KEYS = {
    "name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns", "skills",
    "mcpServers", "hooks", "memory", "effort", "background", "omitClaudeMd", "isolation",
    "initialPrompt", "color", "experimental",
}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TRIGGER_RE = re.compile(r"\b(use (it )?when|use for|use this|trigger|when (the )?user|invoke when|use proactively)\b", re.I)
PLACEHOLDER_RE = re.compile(r"Continuous learning system\. Use /claudeception", re.I)
OLD_MODEL_RE = re.compile(r"\bclaude-(instant|2(\.\d)?|3(-5|-7)?-(opus|sonnet|haiku)|3-(opus|sonnet|haiku))[\w-]*", re.I)
SECRET_RE = re.compile(
    r"(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+]{12,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}",
    re.I,
)
PLACEHOLDER_SECRET_RE = re.compile(r"your|example|placeholder|changeme|change_me|xxx|dummy|test|supersecret|configservice|response|process\.env|\$\{|<", re.I)
SIDE_EFFECT_RE = re.compile(r"\b(deploy|publish|git push|send (a )?message|delete|drop table|rm -rf|restart)\b", re.I)
LINK_RE = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")
STOP = set("a an the and or of to in for on with when use is are be this that it by as at from your you".split())


def parse(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    issues = []
    if "\r\n" in text:
        issues.append(("info", "crlf", "CRLF line endings"))
        text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None, text, issues + [("error", "no-frontmatter", "file does not start with '---'")]
    end = text.find("\n---", 4)
    if end == -1:
        return None, text, issues + [("error", "no-frontmatter", "unterminated frontmatter")]
    try:
        fm = yaml.safe_load(text[4:end]) or {}
        if not isinstance(fm, dict):
            raise ValueError("frontmatter is not a mapping")
    except Exception as e:  # noqa: BLE001
        return None, text, issues + [("error", "yaml", f"frontmatter YAML invalid: {e}")]
    return fm, text[end + 4:].lstrip("\n"), issues


def as_date(v):
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 2}


def audit_skill(skill_dir, stale_days):
    name = os.path.basename(skill_dir.rstrip("/"))
    path = os.path.join(skill_dir, "SKILL.md")
    r = {"kind": "skill", "name": name, "path": path, "issues": [], "hints": []}
    fm, body, issues = parse(path)
    r["issues"] += issues
    if fm is None:
        return r
    desc = fm.get("description")
    desc = desc.strip() if isinstance(desc, str) else ""
    r["description"] = desc
    meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    lines = body.count("\n") + 1
    r["lines"] = lines

    fn = fm.get("name")
    if not fn:
        r["issues"].append(("warn", "name-missing", "no name field"))
    elif fn != name:
        r["issues"].append(("warn", "name-mismatch", f"name '{fn}' != dir '{name}'"))
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        r["issues"].append(("warn", "name-format", "dir name not lowercase-hyphen <=64"))

    if not desc:
        r["issues"].append(("error", "desc-missing", "no description"))
    else:
        if PLACEHOLDER_RE.search(desc) and name != "claudeception":
            r["issues"].append(("error", "desc-placeholder", "description is the claudeception placeholder"))
        if len(desc) > 1024:
            r["issues"].append(("error", "desc-too-long", f"{len(desc)} chars > 1024 (Agent Skills spec)"))
        elif len(desc) < 80:
            r["issues"].append(("warn", "desc-thin", f"only {len(desc)} chars; likely too vague to trigger"))
        if not TRIGGER_RE.search(desc):
            r["issues"].append(("warn", "desc-no-trigger", "no 'Use when ...' trigger conditions"))

    legacy = sorted(k for k in fm if k in LEGACY_TOP_LEVEL)
    if legacy:
        r["issues"].append(("info", "legacy-keys", f"move {legacy} under metadata:"))
    unknown = sorted(k for k in fm if k not in SPEC_SKILL_KEYS | CLAUDE_ONLY_SKILL_KEYS | LEGACY_TOP_LEVEL)
    if unknown:
        r["issues"].append(("warn", "unknown-keys", f"unrecognized keys {unknown}"))
    if "when_to_use" in fm:
        r["issues"].append(("info", "when-to-use", "fold when_to_use into description (portable)"))
    if isinstance(fm.get("allowed-tools"), list) and not fm["allowed-tools"]:
        r["issues"].append(("info", "empty-allowed-tools", "allowed-tools is an empty list; remove it"))

    if lines > 500:
        r["issues"].append(("warn", "too-long", f"{lines} lines > 500; move detail to references/"))
    elif lines > 300:
        r["issues"].append(("info", "long", f"{lines} lines; consider progressive disclosure"))
    if lines < 8:
        r["issues"].append(("warn", "too-short", f"{lines} body lines; may be a rule, not a skill"))

    verified = as_date(meta.get("last_verified")) or as_date(fm.get("last_verified"))
    created = as_date(meta.get("created")) or as_date(meta.get("date")) or as_date(fm.get("date"))
    ref = verified or created
    r["last_verified"] = str(verified) if verified else None
    if ref is None:
        r["issues"].append(("info", "undated", "no created/last_verified date"))
    elif (dt.date.today() - ref).days > stale_days:
        r["issues"].append(("warn", "stale", f"last touched {ref} (> {stale_days}d)"))
    if str(meta.get("status", "")).lower() == "deprecated":
        r["hints"].append("deprecated: archive candidate")

    if re.search(r"(^|[\s`(~])\.Codex/|Codex-agent-sdk|name: Codex-", body + str(fm.get("name", ""))):
        r["issues"].append(("warn", "migration-corruption", "'.Codex/' path or Codex-substituted name; likely a bad Claude->Codex rewrite"))
    if OLD_MODEL_RE.search(body):
        r["issues"].append(("warn", "old-model-id", f"mentions retired model id '{OLD_MODEL_RE.search(body).group(0)}'"))
    secrets = [m.group(0) for m in SECRET_RE.finditer(body) if not PLACEHOLDER_SECRET_RE.search(m.group(0))]
    if secrets:
        r["issues"].append(("error", "possible-secret", f"{len(secrets)} credential-like value(s), e.g. '{secrets[0][:12]}…'; review"))
    for link in set(LINK_RE.findall(body)):
        target = os.path.normpath(os.path.join(skill_dir, link.split("#")[0]))
        if link.split("#")[0] and not os.path.exists(target):
            r["issues"].append(("warn", "broken-link", f"relative link '{link}' missing"))

    if SIDE_EFFECT_RE.search(desc) and not fm.get("disable-model-invocation"):
        r["hints"].append("side-effect workflow: consider disable-model-invocation: true")
    if re.search(r"^you are (a|an) ", body, re.I | re.M) and re.search(r"\b(return|report) (a |only )?(summary|findings)\b", body, re.I):
        r["hints"].append("persona + returns summary: agent candidate")
    if lines < 15 and re.search(r"\b(always|never|must)\b", body, re.I):
        r["hints"].append("short always/never rules: CLAUDE.md rule candidate")
    return r


def audit_agent(path):
    name = os.path.splitext(os.path.basename(path))[0]
    r = {"kind": "agent", "name": name, "path": path, "issues": [], "hints": []}
    fm, body, issues = parse(path)
    r["issues"] += issues
    if fm is None:
        return r
    r["name"] = fm.get("name") or name
    desc = str(fm.get("description") or "").strip()
    r["description"] = desc
    r["lines"] = body.count("\n") + 1
    if not fm.get("name") or not desc:
        r["issues"].append(("error", "agent-required", "name and description are required or the agent is skipped"))
    if len(desc) > 400:
        r["issues"].append(("warn", "agent-desc-long", f"{len(desc)} chars; aim for ~100-200 (shared 15k-token budget)"))
    if desc and not TRIGGER_RE.search(desc):
        r["issues"].append(("info", "agent-no-trigger", "description lacks 'Use when/proactively' delegation cue"))
    unknown = sorted(k for k in fm if k not in AGENT_KEYS)
    if unknown:
        r["issues"].append(("warn", "agent-unknown-keys", f"unrecognized keys {unknown}"))
    if "tools" not in fm and "disallowedTools" not in fm:
        r["hints"].append("no tools/disallowedTools: inherits every tool; restrict if read-only")
    model = str(fm.get("model", ""))
    if OLD_MODEL_RE.search(model) or OLD_MODEL_RE.search(body):
        r["issues"].append(("warn", "old-model-id", "retired model id; use an alias (sonnet/opus/haiku) or inherit"))
    if r["lines"] < 5:
        r["issues"].append(("warn", "agent-thin-prompt", "system prompt is nearly empty"))
    if not re.search(r"\b(output|return|report|format)\b", body, re.I):
        r["hints"].append("system prompt never states the output format")
    if r["lines"] > 250 and not fm.get("skills"):
        r["hints"].append("long embedded knowledge: move to a skill and preload via skills:")
    return r


def find_skills(roots):
    seen = set()
    for root in roots:
        root = os.path.expanduser(root)
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            d = os.path.join(root, entry)
            if entry.startswith(".") or entry == "synced":
                continue
            if os.path.isfile(os.path.join(d, "SKILL.md")):
                real = os.path.realpath(d)
                if real not in seen:
                    seen.add(real)
                    yield d


def find_agents(roots):
    for root in roots:
        root = os.path.expanduser(root)
        for dirpath, _, files in os.walk(root):
            for f in sorted(files):
                if f.endswith(".md"):
                    yield os.path.join(dirpath, f)


def overlaps(items, threshold):
    pairs = []
    toks = [(i, tokens(i.get("description"))) for i in items if i.get("description")]
    for (a, ta), (b, tb) in combinations(toks, 2):
        if a["kind"] != b["kind"] or not ta or not tb:
            continue
        j = len(ta & tb) / len(ta | tb)
        if j >= threshold:
            pairs.append((round(j, 2), a["name"], b["name"], a["kind"]))
    return sorted(pairs, reverse=True)


SEV = {"error": 0, "warn": 1, "info": 2}


def report_md(items, pairs):
    out = [f"# Claudeception audit — {dt.date.today()}", ""]
    counts = {s: sum(1 for i in items for x in i["issues"] if x[0] == s) for s in SEV}
    out.append(f"{sum(i['kind'] == 'skill' for i in items)} skills, {sum(i['kind'] == 'agent' for i in items)} agents. "
               f"Issues: {counts['error']} error, {counts['warn']} warn, {counts['info']} info.")
    out.append("")
    ranked = sorted(items, key=lambda i: (min([SEV[x[0]] for x in i["issues"]] or [3]), -len(i["issues"])))
    for i in ranked:
        if not i["issues"] and not i["hints"]:
            continue
        out.append(f"## {i['kind']}: {i['name']}  ({i.get('lines', '?')} lines)")
        out.append(f"`{i['path']}`")
        for sev, code, msg in sorted(i["issues"], key=lambda x: SEV[x[0]]):
            out.append(f"- **{sev}** `{code}` — {msg}")
        for h in i["hints"]:
            out.append(f"- hint — {h}")
        out.append("")
    if pairs:
        out += ["## Overlap candidates (merge / cross-link)", ""]
        out += [f"- {j:.2f} {k}: `{a}` ↔ `{b}`" for j, a, b, k in pairs]
    clean = [i["name"] for i in items if not i["issues"] and not i["hints"]]
    if clean:
        out += ["", f"## Clean ({len(clean)})", ", ".join(clean)]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skills", nargs="*", default=[".claude/skills", "~/.claude/skills", "~/.agents/skills", "~/.codex/skills"])
    ap.add_argument("--agents", nargs="*", default=[".claude/agents", "~/.claude/agents"])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--stale-days", type=int, default=180)
    ap.add_argument("--overlap", type=float, default=0.35, help="description Jaccard threshold")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    items = [audit_skill(d, a.stale_days) for d in find_skills(a.skills)]
    items += [audit_agent(p) for p in find_agents(a.agents)]
    if a.only:
        items = [i for i in items if i["name"] in a.only]
    pairs = overlaps(items, a.overlap)
    if a.json:
        json.dump({"items": items, "overlaps": pairs}, sys.stdout, indent=2, default=str)
    else:
        sys.stdout.write(report_md(items, pairs))


if __name__ == "__main__":
    main()
