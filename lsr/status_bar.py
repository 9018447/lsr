"""
Status bar module for lsr.

Provides a bottom status bar displaying current context information.
"""

from rich.text import Text

from lsr.theme import CatppuccinMocha as Mocha


class StatusBar:
    """Bottom status bar displaying current context information."""

    def __init__(self, io):
        """Initialize the status bar.

        Args:
            io: The InputOutput instance for console access
        """
        self.io = io
        self.console = io.console
        self.visible = False
        self._last_context = {}

    def render(self, context: dict) -> None:
        """Render the status bar with context information.

        Args:
            context: Dictionary with keys:
                - model: str (current model name)
                - files: list (added files)
                - tokens: int (used tokens)
                - edit_format: str (current edit format)
                - git_branch: str (current git branch)
        """
        self._last_context = context
        self.visible = True

        line = Text()
        line.append(" ⚡ ", style=Mocha.YELLOW)
        line.append(f"{context.get('model', 'unknown')}", style=Mocha.LAVENDER)

        line.append(" │ ", style=Mocha.SURFACE2)
        files = context.get("files", [])
        line.append(f"📁 {len(files)} files", style=Mocha.SKY)

        line.append(" │ ", style=Mocha.SURFACE2)
        tokens = context.get("tokens", 0)
        line.append(f"🔤 {tokens:,} tokens", style=Mocha.TEAL)

        git_branch = context.get("git_branch")
        if git_branch:
            line.append(" │ ", style=Mocha.SURFACE2)
            line.append(f"🔀 {git_branch}", style=Mocha.GREEN)

        line.append(" │ ", style=Mocha.SURFACE2)
        edit_format = context.get("edit_format", "ask")
        line.append(f"{edit_format}", style=Mocha.SUBTEXT1)

        line.append("  ", style=Mocha.SURFACE2)
        line.append("Ctrl-C: interrupt │ /help: help", style=Mocha.OVERLAY1)

        self.console.print(line, style=f"on {Mocha.MANTLE}")

    def update_model(self, model: str) -> None:
        """Update only the model in the status bar."""
        self._last_context["model"] = model
        if self.visible:
            self.render(self._last_context)

    def update_tokens(self, tokens: int) -> None:
        """Update only the token count in the status bar."""
        self._last_context["tokens"] = tokens
        if self.visible:
            self.render(self._last_context)

    def hide(self) -> None:
        """Hide the status bar."""
        self.visible = False

    def show(self) -> None:
        """Show the status bar with last known context."""
        if self._last_context:
            self.visible = True
            self.render(self._last_context)
