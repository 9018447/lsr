"""
Plan persistence manager for lsr.

Stores plans in .lsr/plans/ as Markdown files with YAML frontmatter.
Each plan has a timestamp-based ID for easy reference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

import yaml

PLANS_DIR = ".lsr/plans"


@dataclass
class Plan:
    id: str
    title: str
    content: str
    created: str
    status: str = "draft"
    tags: list[str] = field(default_factory=list)

    @property
    def short_id(self) -> str:
        """First 8 chars of id for display."""
        return self.id[:8]

    @property
    def filename(self) -> str:
        safe_title = re.sub(r"[^\w\s-]", "", self.title).strip().replace(" ", "_")[:30]
        return f"{self.id}_{safe_title}.md"


def _plans_dir(root: str | Path) -> Path:
    d = Path(root) / PLANS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _now_iso() -> str:
    return datetime.now().isoformat()


def save_plan(content: str, title: str, root: str | Path, status: str = "draft") -> Plan:
    """Parse a plan from LLM output and save it to disk.

    Extracts the first ## heading as title if title is empty.
    """
    plan_id = _now_id()

    # Try to extract title from content if not provided
    if not title:
        m = re.search(r"^## Plan:\s*(.+)$", content, re.MULTILINE)
        if m:
            title = m.group(1).strip()
        else:
            title = "Untitled Plan"

    plan = Plan(
        id=plan_id,
        title=title,
        content=content.strip(),
        created=_now_iso(),
        status=status,
    )

    frontmatter = {
        "id": plan.id,
        "title": plan.title,
        "created": plan.created,
        "status": plan.status,
    }

    text = f"---\n{yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)}---\n\n{plan.content}\n"

    filepath = _plans_dir(root) / plan.filename
    filepath.write_text(text, encoding="utf-8")
    return plan


def update_plan(plan: Plan, root: str | Path) -> None:
    """Overwrite an existing plan file with updated content/status."""
    frontmatter = {
        "id": plan.id,
        "title": plan.title,
        "created": plan.created,
        "status": plan.status,
        "tags": plan.tags,
    }

    text = f"---\n{yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)}---\n\n{plan.content}\n"

    filepath = _plans_dir(root) / plan.filename
    filepath.write_text(text, encoding="utf-8")


def load_plan(plan_id: str, root: str | Path) -> Plan | None:
    """Load a plan by full or short id."""
    d = _plans_dir(root)
    candidates = list(d.glob(f"{plan_id}*.md"))
    if not candidates:
        # Try short-id match
        candidates = [p for p in d.glob("*.md") if p.stem.startswith(plan_id)]

    if not candidates:
        return None
    if len(candidates) > 1:
        # Prefer exact prefix match
        exact = [p for p in candidates if p.stem.startswith(f"{plan_id}_")]
        if exact:
            candidates = exact[:1]
        else:
            candidates = candidates[:1]

    return _parse_plan_file(candidates[0])


def _parse_plan_file(filepath: Path) -> Plan:
    text = filepath.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1])
            content = parts[2].strip()
            return Plan(
                id=str(fm.get("id", filepath.stem.split("_")[0])),
                title=fm.get("title", "Untitled"),
                content=content,
                created=fm.get("created", ""),
                status=fm.get("status", "draft"),
                tags=fm.get("tags", []) or [],
            )

    # Fallback: no frontmatter
    return Plan(
        id=filepath.stem.split("_")[0],
        title=filepath.stem,
        content=text.strip(),
        created="",
        status="draft",
    )


def list_plans(root: str | Path) -> list[Plan]:
    """Return all plans sorted by creation time (newest first)."""
    d = _plans_dir(root)
    plans = [_parse_plan_file(p) for p in d.glob("*.md")]
    return sorted(plans, key=lambda p: p.created or p.id, reverse=True)


def delete_plan(plan_id: str, root: str | Path) -> bool:
    """Delete a plan by id. Returns True if found and deleted."""
    d = _plans_dir(root)
    candidates = list(d.glob(f"{plan_id}*.md"))
    if not candidates:
        candidates = [p for p in d.glob("*.md") if p.stem.startswith(plan_id)]

    if not candidates:
        return False

    for c in candidates:
        c.unlink()
    return True


def get_latest_plan(root: str | Path) -> Plan | None:
    """Return the most recently created plan, or None."""
    plans = list_plans(root)
    return plans[0] if plans else None


def find_plan_by_id_or_latest(plan_id: str | None, root: str | Path) -> Plan | None:
    """Load by id if given, otherwise return the latest plan."""
    if plan_id:
        return load_plan(plan_id, root)
    return get_latest_plan(root)
