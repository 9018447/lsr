"""Tests for the runtime profiling harness decision logic."""

import os
from unittest import mock

from scripts.profile_runtime import (
    ALL_PROFILES,
    check_prerequisite,
    classify_time,
    select_profiles,
)


class TestSelectProfiles:
    def test_default_runs_all_profiles(self):
        assert select_profiles(None, False) == ALL_PROFILES

    def test_startup_only_overrides_requested(self):
        assert select_profiles(["compile", "chat"], True) == ["startup"]

    def test_requested_profiles_filtered(self):
        assert select_profiles(["startup", "compile", "unknown"], False) == [
            "startup",
            "compile",
        ]


class TestCheckPrerequisite:
    def test_startup_always_ok(self):
        ok, reason = check_prerequisite("startup")
        assert ok
        assert reason is None

    def test_section_parsing_always_ok(self):
        ok, reason = check_prerequisite("section_parsing")
        assert ok
        assert reason is None

    def test_compile_ok_when_pdflatex_available(self):
        with mock.patch("shutil.which", return_value="/usr/bin/pdflatex"):
            ok, reason = check_prerequisite("compile")
            assert ok
            assert reason is None

    def test_compile_skipped_when_pdflatex_missing(self):
        with mock.patch("shutil.which", return_value=None):
            ok, reason = check_prerequisite("compile")
            assert not ok
            assert "pdflatex" in reason

    def test_lsp_ok_when_texlab_available(self):
        with mock.patch("shutil.which", return_value="/usr/bin/texlab"):
            ok, reason = check_prerequisite("lsp")
            assert ok
            assert reason is None

    def test_lsp_skipped_when_texlab_missing(self):
        with mock.patch("shutil.which", return_value=None):
            ok, reason = check_prerequisite("lsp")
            assert not ok
            assert "texlab" in reason

    def test_chat_ok_when_api_key_present(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            ok, reason = check_prerequisite("chat")
            assert ok
            assert reason is None

    def test_chat_skipped_when_api_key_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            ok, reason = check_prerequisite("chat")
            assert not ok
            assert "OPENAI_API_KEY" in reason


class TestClassifyTime:
    def test_internal_external_split(self):
        row = classify_time("compile", 0.1, 0.9)
        assert row["profile"] == "compile"
        assert row["internal_s"] == 0.1
        assert row["external_s"] == 0.9
        assert row["total_s"] == 1.0
        assert row["internal_pct"] == 10.0

    def test_zero_total_avoids_division_by_zero(self):
        row = classify_time("section_parsing", 0.0, 0.0)
        assert row["internal_pct"] == 0.0
