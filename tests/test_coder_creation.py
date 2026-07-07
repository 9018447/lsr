"""Regression tests for Coder creation."""

from unittest.mock import MagicMock

from lsr.coders import Coder
from lsr.commands import Commands
from lsr.io import InputOutput


class TestCoderCreation:
    def test_create_edit_block_coder_with_lsp_args(self):
        """Creating an EditBlockCoder with LSP args must not raise AttributeError."""
        model = MagicMock()
        model.reasoning_tag = None
        model.streaming = False
        model.cache_control = False
        model.edit_format = "diff"
        model.commit_message_models.return_value = []
        model.max_chat_history_tokens = 1024
        model.weak_model = model
        model.info = {}
        model.name = "test-model"
        model.token_count.return_value = 0
        model.reminder = None
        model.system_prompt_prefix = None
        model.get_thinking_tokens.return_value = None

        args = MagicMock()
        args.disable_lsp = False
        args.lsp_server_latex = None
        args.lsp_server_typst = None
        args.lsp_server_markdown = None

        io = InputOutput(pretty=False, yes=True)
        commands = Commands(io, None, args=args)

        coder = Coder.create(
            main_model=model,
            edit_format="diff",
            io=io,
            commands=commands,
            fnames=[],
            use_git=False,
        )

        assert isinstance(coder, Coder)
        assert hasattr(coder, "root")
        assert coder.commands.lsp_manager is not None
        assert coder.commands.lsp_manager.enabled is True
