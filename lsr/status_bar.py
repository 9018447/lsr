"""
Status bar module for lsr.

Provides a bottom status bar displaying current context information
with token usage progress, unicode symbols, and visual separators.
"""

from rich.text import Text

from lsr.theme import SYMBOLS
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

    def _render_mini_bar(self, pct: int, width: int = 8) -> tuple[str, str]:
        """Render a mini progress bar and choose color based on percentage.

        Returns:
            Tuple of (bar_string, color).
        """
        filled = int(pct / 100 * width)
        bar = SYMBOLS["progress_full"] * filled + SYMBOLS["progress_empty"] * (width - filled)
        if pct < 50:
            color = Mocha.GREEN
        elif pct < 80:
            color = Mocha.YELLOW
        else:
            color = Mocha.RED
        return bar, color

    def render(self, context: dict) -> None:
        """Render the status bar with context information.

        Args:
            context: Dictionary with keys:
                - model: str (current model name)
                - files: list (added files)
                - tokens: int (used tokens)
                - max_tokens: int (max tokens available, optional)
                - edit_format: str (current edit format)
                - git_branch: str (current git branch)
        """
        self._last_context = context
        self.visible = True

        line = Text()

        # Model icon + name
        line.append(f" {SYMBOLS['model']} ", style=Mocha.MAUVE)
        line.append(f"{context.get('model', 'unknown')}", style=Mocha.LAVENDER)

        line.append(f" {SYMBOLS['separator']} ", style=Mocha.SURFACE2)

        # File count
        files = context.get("files", [])
        line.append(f"{SYMBOLS['folder']} {len(files)} files", style=Mocha.SKY)

        line.append(f" {SYMBOLS['separator']} ", style=Mocha.SURFACE2)

        # Tokens with mini progress bar
        tokens = context.get("tokens", 0)
        max_tokens = context.get("max_tokens", 0)
        if max_tokens and max_tokens > 0:
            pct = min(100, int(tokens / max_tokens * 100))
            bar, bar_color = self._render_mini_bar(pct)
            line.append(
                f"{SYMBOLS['tokens']} {tokens / 1000:.1f}k/{max_tokens / 1000:.1f}k ",
                style=Mocha.TEAL,
            )
            line.append(f"[{bar}]", style=bar_color)
            line.append(f" {pct}%", style=bar_color)
        else:
            line.append(f"{SYMBOLS['tokens']} {tokens:,} tokens", style=Mocha.TEAL)

        # Git branch
        git_branch = context.get("git_branch")
        if git_branch:
            line.append(f" {SYMBOLS['separator']} ", style=Mocha.SURFACE2)
            line.append(f"{SYMBOLS['git_branch']} {git_branch}", style=Mocha.GREEN)

        line.append(f" {SYMBOLS['separator']} ", style=Mocha.SURFACE2)

        # Edit format
        edit_format = context.get("edit_format", "ask")
        line.append(f"{edit_format}", style=Mocha.SUBTEXT1)

        # Help hint
        line.append("  ", style=Mocha.SURFACE2)
        line.append("Ctrl-C: interrupt │ /help: help", style=Mocha.OVERLAY1)

        self.console.print(line, style=f"on {Mocha.MANTLE}")

        # Bottom separator line to visually separate from input area
        # Bottom separator line to visually separate from input area
        width = max(1, self.console.width)
        sep = Text(SYMBOLS["separator_horizontal"] * width, style=Mocha.SURFACE1)
        self.console.print(sep)

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
