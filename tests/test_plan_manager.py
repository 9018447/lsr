"""
Tests for plan_manager: Plan dataclass, CRUD operations for .lsr/plans/ files.
Uses tmp_path for all filesystem operations; no real workspace touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lsr.plan_manager import (
    Plan,
    _now_id,
    _plans_dir,
    delete_plan,
    find_plan_by_id_or_latest,
    get_latest_plan,
    list_plans,
    load_plan,
    save_plan,
    update_plan,
)


class TestPlanDataclass:
    """Plan dataclass field defaults and computed properties."""

    def test_default_status_and_tags(self):
        p = Plan(id="20250101", title="Test", content="c", created="now")
        assert p.status == "draft"
        assert p.tags == []

    def test_short_id_first_eight(self):
        p = Plan(id="abcdefghijkl", title="T", content="c", created="n")
        assert p.short_id == "abcdefgh"

    @pytest.mark.parametrize(
        ("title", "expected_suffix"),
        [
            ("Hello World", "Hello_World"),
            ("Hello    World", "Hello____World"),  # spaces collapsed by strip+replace
            ("Special!@#Chars", "SpecialChars"),
            ("a" * 50, "a" * 30),
            ("  leading/trailing  ", "leadingtrailing"),
        ],
    )
    def test_filename_suffix(self, title, expected_suffix):
        pid = "20250101120000"
        p = Plan(id=pid, title=title, content="c", created="n")
        expected = f"{pid}_{expected_suffix}.md"
        assert p.filename == expected


class TestSavePlan:
    """save_plan writes YAML frontmatter + content to .lsr/plans/<id>_<title>.md."""

    def test_explicit_title_roundtrip(self, tmp_path: Path):
        plan = save_plan("Some content", "My Plan", tmp_path)
        assert plan.title == "My Plan"
        assert plan.content == "Some content"
        assert plan.status == "draft"
        assert plan.id == _now_id()

        filepath = _plans_dir(tmp_path) / plan.filename
        assert filepath.exists()
        text = filepath.read_text(encoding="utf-8")
        assert "---" in text
        assert plan.id in text
        assert "title: My Plan" in text
        assert "Some content" in text

    def test_empty_title_extracts_from_content(self, tmp_path: Path):
        content = "## Plan: Extracted Title\n\nSome body"
        plan = save_plan(content, "", tmp_path)
        assert plan.title == "Extracted Title"

    def test_empty_title_no_heading_falls_back(self, tmp_path: Path):
        plan = save_plan("Just body", "", tmp_path)
        assert plan.title == "Untitled Plan"

    def test_custom_status(self, tmp_path: Path):
        plan = save_plan("x", "T", tmp_path, status="completed")
        assert plan.status == "completed"

    def test_returns_plan_object(self, tmp_path: Path):
        plan = save_plan("x", "T", tmp_path)
        assert isinstance(plan, Plan)
        assert plan.id == _now_id()
        assert plan.title == "T"
        assert plan.content == "x"
        assert isinstance(plan.created, str)


class TestLoadPlan:
    """load_plan loads by full id or short id prefix."""

    def test_load_by_full_id(self, tmp_path: Path):
        saved = save_plan("content", "Title", tmp_path)
        loaded = load_plan(saved.id, tmp_path)
        assert loaded is not None
        assert loaded.id == saved.id
        assert loaded.title == "Title"
        assert loaded.content == "content"

    def test_load_by_short_id(self, tmp_path: Path):
        saved = save_plan("content", "Title", tmp_path)
        loaded = load_plan(saved.short_id, tmp_path)
        assert loaded is not None
        assert loaded.id == saved.id

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        assert load_plan("nosuchid", tmp_path) is None

    def test_load_empty_dir_returns_none(self, tmp_path: Path):
        assert load_plan("20250101", tmp_path) is None


class TestListPlans:
    """list_plans returns all plans sorted by created descending."""

    def test_multiple_plans_order(self, tmp_path: Path):
        p1 = save_plan("a", "First", tmp_path)
        p2 = save_plan("b", "Second", tmp_path)
        p3 = save_plan("c", "Third", tmp_path)

        plans = list_plans(tmp_path)
        assert len(plans) == 3
        # Newest first (ids are timestamp-based)
        assert plans[0].id == p3.id
        assert plans[1].id == p2.id
        assert plans[2].id == p1.id

    def test_empty_dir_returns_empty_list(self, tmp_path: Path):
        assert list_plans(tmp_path) == []


class TestDeletePlan:
    """delete_plan removes the plan file and returns success status."""

    def test_delete_existing(self, tmp_path: Path):
        saved = save_plan("content", "Title", tmp_path)
        assert delete_plan(saved.id, tmp_path) is True
        assert load_plan(saved.id, tmp_path) is None

    def test_delete_nonexistent(self, tmp_path: Path):
        assert delete_plan("nosuchid", tmp_path) is False

    def test_delete_by_short_id(self, tmp_path: Path):
        saved = save_plan("content", "Title", tmp_path)
        assert delete_plan(saved.short_id, tmp_path) is True
        assert load_plan(saved.id, tmp_path) is None


class TestUpdatePlan:
    """update_plan overwrites an existing plan file."""

    def test_update_content_and_status(self, tmp_path: Path):
        saved = save_plan("original", "Test", tmp_path)
        saved.content = "updated"
        saved.status = "completed"
        saved.tags = ["done"]

        update_plan(saved, tmp_path)

        loaded = load_plan(saved.id, tmp_path)
        assert loaded is not None
        assert loaded.content == "updated"
        assert loaded.status == "completed"
        assert loaded.tags == ["done"]

    def test_update_preserves_title(self, tmp_path: Path):
        saved = save_plan("original", "KeepTitle", tmp_path)
        saved.content = "new"
        update_plan(saved, tmp_path)
        loaded = load_plan(saved.id, tmp_path)
        assert loaded is not None
        assert loaded.title == "KeepTitle"


class TestGetLatestAndFindByIdOrLatest:
    """get_latest_plan and find_plan_by_id_or_latest convenience functions."""

    def test_get_latest_with_plans(self, tmp_path: Path):
        save_plan("a", "First", tmp_path)
        later = save_plan("b", "Second", tmp_path)
        assert get_latest_plan(tmp_path) is not None
        assert get_latest_plan(tmp_path).id == later.id  # type: ignore[union-attr]

    def test_get_latest_empty_dir(self, tmp_path: Path):
        assert get_latest_plan(tmp_path) is None

    def test_find_by_id(self, tmp_path: Path):
        saved = save_plan("content", "Title", tmp_path)
        result = find_plan_by_id_or_latest(saved.id, tmp_path)
        assert result is not None
        assert result.id == saved.id

    def test_find_latest_when_none(self, tmp_path: Path):
        assert find_plan_by_id_or_latest(None, tmp_path) is None

    def test_find_latest_with_plans(self, tmp_path: Path):
        save_plan("a", "First", tmp_path)
        later = save_plan("b", "Second", tmp_path)
        result = find_plan_by_id_or_latest(None, tmp_path)
        assert result is not None
        assert result.id == later.id
