"""
Tests for lsr.models — reasoning/thinking budget dispatch and getter helpers.
"""

from types import SimpleNamespace

from lsr import models


class TestThinkingBudgetDispatch:
    """Verify set_thinking_budget and set_thinking_tokens write the correct API key."""

    def test_qwen3_uses_thinking_budget(self):
        m = models.Model("openrouter/qwen/qwen3-235b-a22b")
        assert "thinking_budget" in m.accepts_settings
        m.set_thinking_budget("1500")
        assert m.extra_params["extra_body"]["thinking_budget"] == 1500
        assert m.get_raw_thinking_tokens() == 1500
        assert m.get_thinking_tokens() == "1.5k"

    def test_qwen3_disable_thinking_budget(self):
        m = models.Model("openrouter/qwen/qwen3-235b-a22b")
        m.set_thinking_budget("1500")
        m.set_thinking_budget("0")
        assert "thinking_budget" not in m.extra_params.get("extra_body", {})
        assert m.get_raw_thinking_tokens() is None

    def test_qwen3_set_thinking_tokens_does_not_write_thinking_budget(self):
        m = models.Model("openrouter/qwen/qwen3-235b-a22b")
        m.set_thinking_tokens("1500")
        assert "thinking_budget" not in m.extra_params.get("extra_body", {})

    def test_anthropic_uses_thinking_dict(self):
        m = models.Model("claude-sonnet-4-6")
        assert "thinking_tokens" in m.accepts_settings
        m.set_thinking_tokens("2000")
        assert m.extra_params["thinking"]["budget_tokens"] == 2000
        assert m.get_thinking_tokens() == "2.0k"

    def test_openrouter_non_qwen_uses_reasoning_max_tokens(self):
        m = models.Model("openrouter/openrouter/optimus-alpha")
        assert "thinking_tokens" in m.accepts_settings
        m.set_thinking_tokens("2000")
        assert m.extra_params["extra_body"]["reasoning"]["max_tokens"] == 2000
        assert m.get_thinking_tokens() == "2.0k"


class TestReasoningEffortDispatch:
    """Verify set_reasoning_effort writes the correct API shape per provider."""

    def test_deepseek_v4_uses_extra_body_reasoning_effort(self):
        m = models.Model("deepseek/deepseek-v4-pro")
        assert "reasoning_effort" in m.accepts_settings
        m.set_reasoning_effort("medium")
        assert m.extra_params["extra_body"]["reasoning_effort"] == "medium"
        assert m.get_reasoning_effort() == "medium"

    def test_openrouter_merges_reasoning_effort_with_thinking_tokens(self):
        m = models.Model("openrouter/openrouter/optimus-alpha")
        m.set_reasoning_effort("medium")
        m.set_thinking_tokens("2000")
        assert m.extra_params["extra_body"]["reasoning"] == {
            "effort": "medium",
            "max_tokens": 2000,
        }

    def test_openrouter_disable_thinking_keeps_reasoning_effort(self):
        m = models.Model("openrouter/openrouter/optimus-alpha")
        m.set_reasoning_effort("high")
        m.set_thinking_tokens("2000")
        m.set_thinking_tokens("0")
        assert m.extra_params["extra_body"]["reasoning"] == {"effort": "high"}

    def test_non_openrouter_uses_reasoning_effort_key(self):
        m = models.Model("o3-mini")
        # The generic OpenAI o3-mini rule sets reasoning_effort support.
        assert "reasoning_effort" in m.accepts_settings
        m.set_reasoning_effort("low")
        assert m.extra_params["extra_body"]["reasoning_effort"] == "low"


class TestDefaultReasoningControls:
    """Verify the main.py default logic applies budgets to all supported models."""

    def _apply_defaults(self, name):
        m = models.Model(name)
        args = SimpleNamespace(
            reasoning_effort=None,
            thinking_budget=None,
            thinking_tokens=None,
            check_model_accepts_settings=True,
        )
        DEFAULT_THINKING_BUDGET = "2000"
        DEFAULT_REASONING_EFFORT = "medium"

        reasoning_effort = (
            args.reasoning_effort
            if args.reasoning_effort is not None
            else DEFAULT_REASONING_EFFORT
        )
        thinking_budget = (
            args.thinking_budget
            if args.thinking_budget is not None
            else (
                args.thinking_tokens
                if args.thinking_tokens is not None
                else DEFAULT_THINKING_BUDGET
            )
        )

        if not args.check_model_accepts_settings or (
            m.accepts_settings and "reasoning_effort" in m.accepts_settings
        ):
            m.set_reasoning_effort(reasoning_effort)

        if not args.check_model_accepts_settings or (
            m.accepts_settings and "thinking_budget" in m.accepts_settings
        ):
            m.set_thinking_budget(thinking_budget)
        elif not args.check_model_accepts_settings or (
            m.accepts_settings and "thinking_tokens" in m.accepts_settings
        ):
            m.set_thinking_tokens(thinking_budget)

        return m

    def test_qwen3_gets_default_thinking_budget(self):
        m = self._apply_defaults("openrouter/qwen/qwen3-235b-a22b")
        assert m.extra_params["extra_body"]["thinking_budget"] == 2000

    def test_claude_gets_default_thinking_tokens(self):
        m = self._apply_defaults("claude-sonnet-4-6")
        assert m.extra_params["thinking"]["budget_tokens"] == 2000

    def test_openrouter_gets_default_reasoning_max_tokens(self):
        m = self._apply_defaults("openrouter/openrouter/optimus-alpha")
        assert m.extra_params["extra_body"]["reasoning"]["max_tokens"] == 2000
        assert m.extra_params["extra_body"]["reasoning"]["effort"] == "medium"

    def test_deepseek_v4_gets_default_reasoning_effort(self):
        m = self._apply_defaults("deepseek/deepseek-v4-pro")
        assert m.extra_params["extra_body"]["reasoning_effort"] == "medium"

    def test_unsupported_model_skips_both(self):
        m = self._apply_defaults("deepseek/deepseek-chat")
        assert "thinking_budget" not in m.extra_params.get("extra_body", {})
        assert "reasoning_effort" not in m.extra_params.get("extra_body", {})
        assert "thinking" not in m.extra_params
