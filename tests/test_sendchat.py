"""Tests for lsr.sendchat module.

Tests pure-logic functions: sanity_check_messages and ensure_alternating_roles.
No LLM/network/interactive dependencies.
"""

import pytest
from lsr.sendchat import sanity_check_messages, ensure_alternating_roles


class TestSanityCheckMessages:
    def test_alternating_returns_true(self):
        """user -> assistant -> user is valid, should return True."""
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        assert sanity_check_messages(messages) is True

    def test_system_interleaved(self):
        """System messages interspersed should not break alternation."""
        messages = [
            {"role": "system", "content": "sys1"},
            {"role": "user", "content": "hi"},
            {"role": "system", "content": "sys2"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        assert sanity_check_messages(messages) is True

    def test_consecutive_user_raises(self):
        messages = [
            {"role": "user", "content": "a"},
            {"role": "user", "content": "b"},
        ]
        with pytest.raises(ValueError, match="Messages don't properly alternate"):
            sanity_check_messages(messages)

    def test_consecutive_assistant_raises(self):
        messages = [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        with pytest.raises(ValueError, match="Messages don't properly alternate"):
            sanity_check_messages(messages)

    def test_consecutive_with_system_between(self):
        """System between two user messages still counts as consecutive user."""
        messages = [
            {"role": "user", "content": "u1"},
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u2"},
        ]
        with pytest.raises(ValueError, match="Messages don't properly alternate"):
            sanity_check_messages(messages)

    def test_consecutive_with_system_before_first(self):
        """System before two consecutive user messages."""
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "user", "content": "u2"},
        ]
        with pytest.raises(ValueError, match="Messages don't properly alternate"):
            sanity_check_messages(messages)

    def test_last_is_assistant_returns_false(self):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "reply"},
        ]
        assert sanity_check_messages(messages) is False

    def test_only_system_messages(self):
        """All system messages — no non-system role seen, last_non_system_role is None."""
        messages = [
            {"role": "system", "content": "s1"},
            {"role": "system", "content": "s2"},
        ]
        assert sanity_check_messages(messages) is False

    def test_empty_list_returns_false(self):
        assert sanity_check_messages([]) is False

    def test_single_user(self):
        """Single user message: no consecutive violation, last_non_system_role=='user' -> True."""
        assert sanity_check_messages([{"role": "user", "content": "hi"}]) is True

    def test_single_assistant(self):
        """Single assistant: no violation, last_non_system_role=='assistant' -> False."""
        assert sanity_check_messages([{"role": "assistant", "content": "hi"}]) is False

    def test_user_then_system_then_assistant_ok(self):
        """user -> system -> assistant is valid alternating (system skipped)."""
        messages = [
            {"role": "user", "content": "u"},
            {"role": "system", "content": "sys"},
            {"role": "assistant", "content": "a"},
        ]
        assert sanity_check_messages(messages) is False  # last is assistant

    def test_long_alternating(self):
        messages = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u3"},
        ]
        assert sanity_check_messages(messages) is True


class TestEnsureAlternatingRoles:
    def test_empty_list(self):
        assert ensure_alternating_roles([]) == []

    def test_already_alternating(self):
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
        ]
        result = ensure_alternating_roles(msgs)
        assert result == msgs

    def test_consecutive_user_inserts_assistant(self):
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "user", "content": "b"},
        ]
        expected = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "b"},
        ]
        assert ensure_alternating_roles(msgs) == expected

    def test_consecutive_assistant_inserts_user(self):
        msgs = [
            {"role": "assistant", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        expected = [
            {"role": "assistant", "content": "a"},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "b"},
        ]
        assert ensure_alternating_roles(msgs) == expected

    def test_multiple_consecutive_runs(self):
        msgs = [
            {"role": "user", "content": "u1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a1"},
            {"role": "assistant", "content": "a2"},
        ]
        result = ensure_alternating_roles(msgs)
        expected = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "a2"},
        ]
        assert result == expected

    def test_single_message(self):
        msgs = [{"role": "user", "content": "only"}]
        assert ensure_alternating_roles(msgs) == msgs

    def test_missing_role_key(self):
        """Message without 'role' key: msg.get('role') returns None.
        None != 'user' and None != 'assistant', so no insertion triggered
        — the consecutive check is a string equality of roles."""
        msgs = [
            {"role": "user", "content": "a"},
            {"content": "no role"},
        ]
        result = ensure_alternating_roles(msgs)
        # first msg role="user", second msg role=None, "user" != None -> no insert
        assert len(result) == 2
        assert result[0] == msgs[0]
        assert result[1] == msgs[1]

    def test_three_consecutive_same(self):
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "user", "content": "b"},
            {"role": "user", "content": "c"},
        ]
        result = ensure_alternating_roles(msgs)
        expected = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "b"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "c"},
        ]
        assert result == expected

    def test_assistant_then_user_already_ok(self):
        msgs = [
            {"role": "assistant", "content": "a"},
            {"role": "user", "content": "b"},
        ]
        assert ensure_alternating_roles(msgs) == msgs

    def test_long_sequence_with_some_consecutive(self):
        """user, assistant, user, user, assistant should fix the consecutive user pair."""
        msgs = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a2"},
        ]
        result = ensure_alternating_roles(msgs)
        expected = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a2"},
        ]
        assert result == expected
