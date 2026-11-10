#!/usr/bin/env python3
"""Check the agent context files.

AGENTS.md is the single source of agent instructions, so it must exist, stay
under 200 lines, and every relative link in it must resolve. CLAUDE.md may only
import it. Skills live in one location, `.claude/skills/<name>/SKILL.md`, with
`name` and `description` frontmatter.

Fails when:
  missing   AGENTS.md is absent at the repo root or empty.
  length    AGENTS.md is longer than 200 lines.
  link      a relative link in AGENTS.md or CLAUDE.md does not resolve.
  claude    CLAUDE.md holds prose or rules instead of only `@AGENTS.md` imports.
  skills    a SKILL.md lacks name or description frontmatter, or skills exist
            outside `.claude/skills`.

Usage:
    python3 scripts/check_agent_docs.py

Exit: 0 pass, 1 a check failed. No dependencies, no database.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
CLAUDE = ROOT / "CLAUDE.md"
SKILLS = ROOT / ".claude" / "skills"
ALT_SKILLS = ROOT / ".agents" / "skills"
MAX_AGENTS_LINES = 200

# Links inside code spans and fenced blocks are examples, not links.
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def link_targets(text: str) -> list[str]:
    """Return the targets of the inline Markdown links in `text`."""
    body = FENCE_RE.sub("", text)
    body = CODE_SPAN_RE.sub("", body)
    targets: list[str] = []
    for raw in LINK_RE.findall(body):
        target = raw.strip()
        if target.startswith("<"):
            target = target[1:].split(">", 1)[0]
        else:
            target = target.split()[0] if target else ""
        targets.append(target)
    return targets


def is_relative(target: str) -> bool:
    """A local path, not a URL, an anchor or an absolute path."""
    return (
        bool(target)
        and not target.startswith(("#", "/"))
        and not urlsplit(target).scheme
    )


def check_links(path: Path) -> list[str]:
    problems: list[str] = []
    for target in link_targets(path.read_text(encoding="utf-8")):
        if not is_relative(target):
            continue
        relative = unquote(target.split("#", 1)[0])
        if not relative:
            continue
        resolved = (path.parent / relative).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            problems.append(f"{path.name}: link does not resolve: {target}")
    return problems


def check_agents() -> list[str]:
    if not AGENTS.is_file():
        return ["AGENTS.md is missing at the repo root"]
    text = AGENTS.read_text(encoding="utf-8")
    if not text.strip():
        return ["AGENTS.md is empty"]
    problems = []
    lines = len(text.splitlines())
    if lines > MAX_AGENTS_LINES:
        problems.append(
            f"AGENTS.md: {lines} lines exceeds the {MAX_AGENTS_LINES}-line limit"
        )
    return problems + check_links(AGENTS)


def check_claude() -> list[str]:
    if not CLAUDE.is_file():
        return []
    problems = [
        f"CLAUDE.md: rule text must live in AGENTS.md, not CLAUDE.md: {line.strip()!r}"
        for line in CLAUDE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("@")
    ]
    return problems + check_links(CLAUDE)


def frontmatter(text: str) -> dict[str, str]:
    """The `key: value` pairs of a leading YAML frontmatter block."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator and value.strip():
            fields[key.strip()] = value.strip()
    return fields


def check_skills() -> list[str]:
    problems: list[str] = []
    if ALT_SKILLS.exists() and not ALT_SKILLS.is_symlink():
        problems.append(
            ".agents/skills must be a symlink to .claude/skills, not a copy"
        )
    if not SKILLS.is_dir():
        return problems
    for skill in sorted(SKILLS.iterdir()):
        if not skill.is_dir():
            continue
        path = skill / "SKILL.md"
        if not path.is_file():
            problems.append(f"{skill.name}: SKILL.md is missing")
            continue
        fields = frontmatter(path.read_text(encoding="utf-8"))
        for field in ("name", "description"):
            if not fields.get(field):
                problems.append(f"{path.relative_to(ROOT)}: frontmatter has no {field}")
    return problems


def main() -> int:
    problems = check_agents() + check_claude() + check_skills()
    print(f"  {'FAIL' if problems else 'ok  '}  agent docs")
    for problem in problems:
        print(f"  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
