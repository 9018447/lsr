"""
Tests for lsr/exceptions.py — ExInfo, EXCEPTIONS, and LiteLLMExceptions.
"""

import pytest

from lsr.exceptions import ExInfo, EXCEPTIONS, LiteLLMExceptions


class TestExInfo:
    """Tests for the ExInfo dataclass."""

    def test_construction_and_access(self):
        """Fields name, retry, description are accessible."""
        info = ExInfo("TestError", True, "A test error")
        assert info.name == "TestError"
        assert info.retry is True
        assert info.description == "A test error"

    def test_none_description(self):
        """Description may be None."""
        info = ExInfo("NoDescError", False, None)
        assert info.name == "NoDescError"
        assert info.retry is False
        assert info.description is None


class TestEXCEPTIONS:
    """Tests for the EXCEPTIONS list."""

    def test_non_empty(self):
        """EXCEPTIONS list is not empty."""
        assert len(EXCEPTIONS) > 0

    def test_all_are_exinfo(self):
        """Every entry is an ExInfo instance."""
        for ex in EXCEPTIONS:
            assert isinstance(ex, ExInfo)

    def test_bad_request_error(self):
        """BadRequestError exists and has retry=False."""
        info = next(ex for ex in EXCEPTIONS if ex.name == "BadRequestError")
        assert info.retry is False

    def test_api_connection_error(self):
        """APIConnectionError exists and has retry=True."""
        info = next(ex for ex in EXCEPTIONS if ex.name == "APIConnectionError")
        assert info.retry is True

    def test_context_window_exceeded_error(self):
        """ContextWindowExceededError exists and has retry=False."""
        info = next(ex for ex in EXCEPTIONS if ex.name == "ContextWindowExceededError")
        assert info.retry is False


class TestLiteLLMExceptions:
    """Tests for LiteLLMExceptions (requires litellm installed)."""

    def _get_instance(self):
        try:
            return LiteLLMExceptions()
        except ImportError:
            pytest.skip("litellm is not installed")

    def test_exceptions_tuple_non_empty(self):
        """exceptions_tuple() returns a non-empty tuple."""
        instance = self._get_instance()
        tup = instance.exceptions_tuple()
        assert isinstance(tup, tuple)
        assert len(tup) > 0

    def test_get_ex_info_unknown(self):
        """get_ex_info on an unknown exception returns ExInfo(None, None, None)."""
        instance = self._get_instance()
        info = instance.get_ex_info(ValueError("something"))
        assert info == ExInfo(None, None, None)
