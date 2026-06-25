"""
Tests for lsr.format_settings — sensitive info scrubbing and settings formatting.
"""

import types

import pytest

from lsr.format_settings import format_settings, scrub_sensitive_info


class FakeParser:
    """A minimal stand-in for argument parsers with format_values()."""

    def __init__(self, formatted):
        self._formatted = formatted

    def format_values(self):
        return self._formatted


# ============================================================
# scrub_sensitive_info
# ============================================================


class TestScrubSensitiveInfo:
    """Test replacement of API keys with masked versions."""

    @pytest.mark.parametrize("text", [None, "", "  "])
    def test_falsy_text_returns_as_is(self, text):
        args = types.SimpleNamespace(openai_api_key="sk-secret123", anthropic_api_key="")
        assert scrub_sensitive_info(args, text) is text

    def test_openai_key_replaced(self):
        args = types.SimpleNamespace(openai_api_key="sk-secret1234567890", anthropic_api_key="")
        text = "Bearer sk-secret1234567890 in the string"
        result = scrub_sensitive_info(args, text)
        assert "sk-secret1234567890" not in result
        assert "...7890" in result

    def test_anthropic_key_replaced(self):
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="sk-ant-secret00009999")
        text = "key=sk-ant-secret00009999"
        result = scrub_sensitive_info(args, text)
        assert "sk-ant-secret00009999" not in result
        assert "...9999" in result

    def test_both_keys_replaced(self):
        args = types.SimpleNamespace(
            openai_api_key="sk-oooo8888", anthropic_api_key="sk-ant-aaaa9999"
        )
        text = "openai=sk-oooo8888 anthropic=sk-ant-aaaa9999"
        result = scrub_sensitive_info(args, text)
        assert "sk-oooo8888" not in result
        assert "sk-ant-aaaa9999" not in result
        assert "...8888" in result
        assert "...9999" in result

    def test_no_keys_empty_text_unchanged(self):
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="")
        text = "no secrets here"
        assert scrub_sensitive_info(args, text) == "no secrets here"

    def test_key_not_in_text_unchanged(self):
        args = types.SimpleNamespace(openai_api_key="sk-absent", anthropic_api_key="")
        text = "plain text"
        assert scrub_sensitive_info(args, text) == "plain text"

    def test_empty_keys_guard(self):
        """Use empty strings to safely skip scrubbing without AttributeError."""
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="")
        text = "some text"
        assert scrub_sensitive_info(args, text) == "some text"

    def test_key_appears_multiple_times(self):
        args = types.SimpleNamespace(openai_api_key="sk-dupe", anthropic_api_key="")
        text = "sk-dupe before and sk-dupe after"
        result = scrub_sensitive_info(args, text)
        assert result == "...dupe before and ...dupe after"


# ============================================================
# format_settings
# ============================================================


class TestFormatSettings:
    """Test assembling and scrubbing the full settings output."""

    def test_contains_option_settings_heading(self):
        parser = FakeParser("Some env block")
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="", verbose=False)
        result = format_settings(parser, args)
        assert "Option settings:" in result
        assert "Some env block" in result

    def test_openai_key_scrubbed_from_parser_values(self):
        key = "sk-hidden00001111"
        parser = FakeParser(f"api={key}")
        args = types.SimpleNamespace(openai_api_key=key, anthropic_api_key="")
        result = format_settings(parser, args)
        assert key not in result
        assert "...1111" in result

    def test_openai_key_scrubbed_from_option_list(self):
        key = "sk-option9999"
        parser = FakeParser("env section")
        args = types.SimpleNamespace(openai_api_key=key, anthropic_api_key="", setting="x")
        result = format_settings(parser, args)
        assert key not in result
        assert "...9999" in result
        assert "Option settings:" in result

    def test_anthropic_key_also_scrubbed(self):
        key_o = "sk-openai-aaa"
        key_a = "sk-ant-bbb"
        parser = FakeParser("env")
        args = types.SimpleNamespace(openai_api_key=key_o, anthropic_api_key=key_a)
        result = format_settings(parser, args)
        assert key_o not in result
        assert key_a not in result

    def test_falsy_values_still_rendered(self):
        """0 and False are falsy so skip the scrub pass, but still appear in output."""
        parser = FakeParser("env")
        args = types.SimpleNamespace(
            openai_api_key="", anthropic_api_key="", count=0, enabled=False
        )
        result = format_settings(parser, args)
        assert "count: 0" in result
        assert "enabled: False" in result

    def test_positive_value_appears(self):
        parser = FakeParser("env")
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="", temperature=0.7)
        result = format_settings(parser, args)
        assert "temperature: 0.7" in result

    def test_environment_headings_normalized(self):
        """Environment Variables: and Defaults: get a leading newline."""
        parser = FakeParser("Environment Variables:\nsome=var\nDefaults:\nval=42")
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="")
        result = format_settings(parser, args)
        assert "\nEnvironment Variables:" in result
        assert "\nDefaults:" in result

    def test_option_settings_lists_args_after_parser_values(self):
        parser = FakeParser("HEADER")
        args = types.SimpleNamespace(openai_api_key="", anthropic_api_key="", opt="val")
        result = format_settings(parser, args)
        assert result.startswith("HEADER")
        assert "Option settings:" in result
        assert "  - opt: val" in result
