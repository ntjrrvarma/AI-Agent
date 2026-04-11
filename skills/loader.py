# SKILL.md convention (Cursor-style):
# - Place files at skills/**/SKILL.md
#Optional YAML frontmatter:
# ---
# description: One-line when to use this skill
# ---
# Body: full instructions. Lines "USE FOR:" / "DO NOT USE FOR:" are also detected for the index.

from __future__ import annotations

from pathlib import Path


def _extract_use_lines(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.strip().upper().startswith(prefix.upper()):
            return line.split(":", 1)[-1].strip()
    return None


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm_block = parts[1].strip()
    body = parts[2].lstrip("\n")
    meta: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip().lower()] = val.strip()
    return meta, body


def _index_snippet(path: Path, skills_root: Path) -> str:
    rel = path.relative_to(skills_root).as_posix()
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"- {rel}: (unreadable)"

    meta, body = _parse_frontmatter(raw)
    description = (meta.get("description") or "").strip()
    if not description:
        description = (body.strip().splitlines() or [""])[0].strip("# ")
    use_for = (
        meta.get("use_for")
        or meta.get("use for")
        or _extract_use_lines(body[:4000], "USE FOR:")
        or ""
    )
    avoid = (
        meta.get("do_not_use_for")
        or meta.get("do not use for")
        or _extract_use_lines(body[:4000], "DO NOT USE FOR:")
        or ""
    )
    bits = [f"- `{rel}`"]
    if description:
        bits.append(f": {description}")
    if use_for:
        bits.append(f" — USE FOR: {use_for}")
    if avoid:
        bits.append(f" — AVOID: {avoid}")
    return "".join(bits)


def build_skills_index(skills_dir: Path, max_body_scan_bytes: int = 64_000) -> str:
    """Return markdown-style index of all SKILL.md files (metadata only; no full bodies)."""
    if not skills_dir.is_dir():
        return "(No skills directory yet.)"

    paths = sorted(skills_dir.rglob("SKILL.md"))
    if not paths:
        return "(No SKILL.md files found. Add skills under skills/<name>/SKILL.md.)"

    lines = ["## Available skills", ""]
    for p in paths:
        # Skip huge files for index scan safety
        try:
            if p.stat().st_size > max_body_scan_bytes:
                lines.append(f"- `{p.relative_to(skills_dir).as_posix()}`: (large file; open to read)")
                continue
        except OSError:
            continue
        lines.append(_index_snippet(p, skills_dir))
    lines.append("")
    lines.append("When a task matches a skill, ask to apply it or summarize how you will follow it.")
    return "\n".join(lines)


def read_skill_body(skills_dir: Path, relative_path: str) -> str:
    """Load full SKILL.md text; relative_path uses forward slashes under skills/."""
    rel = relative_path.strip().replace("\\", "/")
    if ".." in rel or rel.startswith("/"):
        raise ValueError("Invalid skill path")
    skills_root = skills_dir.resolve()
    target = (skills_root / rel).resolve()
    try:
        target.relative_to(skills_root)
    except ValueError as exc:
        raise ValueError("Invalid skill path") from exc
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    return target.read_text(encoding="utf-8", errors="replace")
