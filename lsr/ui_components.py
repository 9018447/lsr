"""
Enhanced UI components for lsr with Catppuccin Mocha theme.

Provides:
- File table with columns layout
- Enhanced diff display
- Styled confirmation dialogs
- Progress indicators
- Message separators and borders
- Tool output with status icons
- Loading widget with color cycling
"""

import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from lsr.theme import MOCHA_GRADIENT, SYMBOLS
from lsr.theme import CatppuccinMocha as Mocha


def render_file_table(
    files: list[str], token_counts: list[int], title: str = "Chat Files"
) -> Table:
    """Render a styled file table with token counts.

    Args:
        files: List of file paths
        token_counts: List of token counts for each file
        title: Table title

    Returns:
        Rich Table object
    """
    table = Table(
        show_header=True,
        header_style=f"bold {Mocha.MAUVE}",
        border_style=Mocha.SURFACE2,
        title=title,
        title_style=f"bold {Mocha.LAVENDER}",
        show_lines=False,
        pad_edge=False,
    )
    table.add_column("Tokens", style=Mocha.TEAL, justify="right", min_width=10)
    table.add_column("File", style=Mocha.YELLOW, min_width=30)
    table.add_column("Status", style=Mocha.OVERLAY1, min_width=15)

    for fname, tokens in zip(files, token_counts, strict=False):
        # Format token count with thousand separators
        token_str = f"{tokens:,}"
        table.add_row(token_str, fname, "/drop to remove")

    return table


def render_diff_table(old_lines: list, new_lines: list, filename: str = "") -> Table:
    """Render a side-by-side diff table with syntax highlighting.

    Args:
        old_lines: Lines from the old version
        new_lines: Lines from the new version
        filename: Filename for context

    Returns:
        Rich Table object
    """
    table = Table(
        show_header=True,
        header_style=f"bold {Mocha.LAVENDER}",
        border_style=Mocha.SURFACE2,
        title=f"Diff: {filename}" if filename else "Diff",
        title_style=f"bold {Mocha.MAUVE}",
        show_lines=False,
        pad_edge=False,
    )
    table.add_column("Line", style=Mocha.OVERLAY0, justify="right", min_width=5)
    table.add_column("Old", style=Mocha.TEXT, min_width=40)
    table.add_column("New", style=Mocha.TEXT, min_width=40)

    max_lines = max(len(old_lines), len(new_lines))
    for i in range(max_lines):
        line_num = str(i + 1)
        old_line = old_lines[i] if i < len(old_lines) else ""
        new_line = new_lines[i] if i < len(new_lines) else ""

        # Highlight differences
        old_style = Mocha.RED if old_line and not new_line else Mocha.TEXT
        new_style = Mocha.GREEN if new_line and not old_line else Mocha.TEXT

        table.add_row(
            line_num,
            Text(old_line, style=old_style),
            Text(new_line, style=new_style),
        )

    return table


def styled_confirm(
    message: str,
    default: bool = True,
    console: Console | None = None,
) -> bool:
    """Display a styled confirmation dialog.

    Args:
        message: Confirmation message
        default: Default answer
        console: Rich Console instance

    Returns:
        User's answer
    """
    if console is None:
        console = Console()

    default_hint = "[Y/n]" if default else "[y/N]"
    panel = Panel(
        f"[bold]{message}[/bold]\n[dim]{default_hint}[/dim]",
        title=f"[bold {Mocha.MAUVE}]Confirm[/bold {Mocha.MAUVE}]",
        border_style=Mocha.PEACH,
        style=f"on {Mocha.SURFACE0}",
        padding=(1, 2),
    )
    console.print(panel)

    while True:
        response = input().strip().lower()
        if not response:
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        console.print(f"[{Mocha.RED}]Please answer y or n[/{Mocha.RED}]")


class StyledProgress:
    """Styled progress indicator with Mocha theme."""

    def __init__(self, console: Console | None = None):
        """Initialize the progress indicator.

        Args:
            console: Rich Console instance
        """
        if console is None:
            console = Console()

        self.progress = Progress(
            SpinnerColumn(style=Mocha.MAUVE),
            TextColumn(
                "[progress.description]{task.description}",
                style=Mocha.TEXT,
            ),
            BarColumn(
                complete_style=Mocha.GREEN,
                finished_style=Mocha.GREEN,
                pulse_style=Mocha.MAUVE,
            ),
            TextColumn(
                "[progress.percentage]{task.percentage:>3.0f}%",
                style=Mocha.TEAL,
            ),
            console=console,
        )

    def __enter__(self):
        self.progress.start()
        return self.progress

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()


def render_token_summary(
    model_name: str,
    total_tokens: int,
    max_tokens: int,
    cost: float = 0.0,
) -> Panel:
    """Render a styled token usage summary panel.

    Args:
        model_name: Name of the model
        total_tokens: Total tokens used
        max_tokens: Maximum tokens available
        cost: Total cost

    Returns:
        Rich Panel object
    """
    remaining = max_tokens - total_tokens
    usage_pct = (total_tokens / max_tokens * 100) if max_tokens > 0 else 0

    # Choose color based on usage
    if usage_pct < 50:
        usage_color = Mocha.GREEN
    elif usage_pct < 80:
        usage_color = Mocha.YELLOW
    else:
        usage_color = Mocha.RED

    content = Text()
    content.append("Model: ", style=Mocha.SUBTEXT1)
    content.append(f"{model_name}\n", style=Mocha.LAVENDER)
    content.append("Tokens: ", style=Mocha.SUBTEXT1)
    content.append(f"{total_tokens:,}", style=usage_color)
    content.append(f" / {max_tokens:,}\n", style=Mocha.OVERLAY1)
    content.append("Usage: ", style=Mocha.SUBTEXT1)
    content.append(f"{usage_pct:.1f}%\n", style=usage_color)
    content.append("Remaining: ", style=Mocha.SUBTEXT1)
    content.append(f"{remaining:,}", style=Mocha.TEAL)

    if cost > 0:
        content.append("\nCost: ", style=Mocha.SUBTEXT1)
        content.append(f"${cost:.4f}", style=Mocha.GREEN)

    return Panel(
        content,
        title=f"[bold {Mocha.MAUVE}]Context Window[/bold {Mocha.MAUVE}]",
        border_style=Mocha.SURFACE2,
        style=f"on {Mocha.BASE}",
        padding=(1, 2),
    )


def render_command_help(command: str, description: str, usage: str = "") -> Panel:
    """Render a styled command help panel.

    Args:
        command: Command name
        description: Command description
        usage: Usage example

    Returns:
        Rich Panel object
    """
    content = Text()
    content.append(f"/{command}", style=f"bold {Mocha.MAUVE}")
    content.append(f"\n\n{description}", style=Mocha.TEXT)

    if usage:
        content.append("\n\nUsage: ", style=Mocha.SUBTEXT1)
        content.append(usage, style=Mocha.TEAL)

    return Panel(
        content,
        title=f"[bold {Mocha.LAVENDER}]Help[/bold {Mocha.LAVENDER}]",
        border_style=Mocha.SURFACE2,
        style=f"on {Mocha.BASE}",
        padding=(1, 2),
    )


# ---------------------------------------------------------------------------
# New visual-polish helpers
# ---------------------------------------------------------------------------


def render_separator(console: Console | None = None, char: str = "─") -> None:
    """Render a full-width horizontal separator line.

    Args:
        console: Rich Console instance
        char: Character to use for the line
    """
    if console is None:
        console = Console()
    width = max(1, console.width)
    console.print(Text(char * width, style=Mocha.SURFACE2))


def render_tool_output(
    message: str,
    status: str = "info",
    console: Console | None = None,
) -> None:
    """Render a tool output line with a status icon prefix.

    Args:
        message: The message to display
        status: One of 'success', 'error', 'warning', 'info'
        console: Rich Console instance
    """
    if console is None:
        console = Console()

    icon = SYMBOLS.get(status, SYMBOLS["info"])
    color = {
        "success": Mocha.GREEN,
        "error": Mocha.RED,
        "warning": Mocha.YELLOW,
        "info": Mocha.SKY,
    }.get(status, Mocha.TEXT)

    console.print(f"[{color}]{icon}[/{color}] {message}")


def render_assistant_output(
    message: str,
    console: Console | None = None,
    border_color: str = Mocha.LAVENDER,
) -> None:
    """Render assistant output with a left border decoration.

    Args:
        message: The message to display
        console: Rich Console instance
        border_color: Color for the left border line
    """
    if console is None:
        console = Console()

    lines = message.splitlines()
    for line in lines:
        decorated = Text()
        decorated.append(f"{SYMBOLS['separator']} ", style=border_color)
        decorated.append(line, style=Mocha.TEXT)
        console.print(decorated)


def render_user_message(
    message: str,
    console: Console | None = None,
) -> None:
    """Render a user message with a blue left border.

    Args:
        message: The message to display
        console: Rich Console instance
    """
    if console is None:
        console = Console()

    lines = message.splitlines()
    for line in lines:
        decorated = Text()
        decorated.append(f"{SYMBOLS['separator']} ", style=Mocha.BLUE)
        decorated.append(line, style=Mocha.TEXT)
        console.print(decorated)


class LoadingWidget:
    """Loading indicator with color-cycling text and elapsed time.

    Usage:
        widget = LoadingWidget("Generating...", console)
        widget.start()
        ...
        widget.update_text("Applying edits...")
        ...
        widget.stop(success=True)
    """

    def __init__(
        self,
        text: str,
        console: Console | None = None,
        colors: list[str] | None = None,
        show_elapsed: bool = True,
        show_interrupt_hint: bool = True,
    ):
        self.text = text
        self.console = console or Console()
        self.colors = colors or MOCHA_GRADIENT
        self.show_elapsed = show_elapsed
        self.show_interrupt_hint = show_interrupt_hint
        self.start_time = time.time()
        self._running = False
        self._color_idx = 0

    def _format_elapsed(self) -> str:
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}m{seconds:02d}s"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h{minutes:02d}m"

    def _cyclic_color_text(self, text: str) -> Text:
        """Apply a moving gradient color to the text characters."""
        result = Text()
        for i, ch in enumerate(text):
            color = self.colors[(self._color_idx + i) % len(self.colors)]
            result.append(ch, style=color)
        self._color_idx = (self._color_idx + 1) % len(self.colors)
        return result

    def start(self) -> None:
        """Print the initial loading line."""
        self._running = True
        self.start_time = time.time()
        self._render()

    def update_text(self, text: str) -> None:
        """Update the loading message text."""
        self.text = text
        if self._running:
            self._render(clear_previous=True)

    def _render(self, clear_previous: bool = False) -> None:
        prefix = f"{SYMBOLS['spinner'][0]} "
        elapsed = f" ({self._format_elapsed()})" if self.show_elapsed else ""
        hint = "  [dim]Ctrl-C: interrupt[/dim]" if self.show_interrupt_hint else ""

        line = Text(prefix)
        line.append(self._cyclic_color_text(self.text))
        line.append(elapsed, style=Mocha.OVERLAY1)
        line.append(hint)

        if clear_previous:
            self.console.print("\r\x1b[K", end="")
        self.console.print(line)

    def stop(self, success: bool = True, final_text: str | None = None) -> None:
        """Stop the loading widget and print a final status line.

        Args:
            success: True for success icon, False for failure
            final_text: Optional final message (defaults to current text)
        """
        self._running = False
        text = final_text if final_text is not None else self.text
        icon = SYMBOLS["spinner_success"] if success else SYMBOLS["spinner_failure"]
        color = Mocha.GREEN if success else Mocha.RED
        elapsed = f" ({self._format_elapsed()})" if self.show_elapsed else ""
        self.console.print(f"[{color}]{icon}[/{color}] {text}{elapsed}")


if __name__ == "__main__":
    # Demo the UI components
    console = Console()

    # File table
    console.print("\n[bold]File Table Demo:[/bold]")
    files = ["main.py", "utils.py", "config.yaml", "README.md"]
    tokens = [1250, 890, 340, 560]
    console.print(render_file_table(files, tokens))

    # Token summary
    console.print("\n[bold]Token Summary Demo:[/bold]")
    console.print(render_token_summary("gpt-4", 45000, 128000, 0.1234))

    # Command help
    console.print("\n[bold]Command Help Demo:[/bold]")
    console.print(
        render_command_help("add", "Add files to the chat", "/add <file1> <file2>")
    )

    # Separator
    console.print("\n[bold]Separator Demo:[/bold]")
    render_separator(console)

    # Tool outputs with icons
    console.print("\n[bold]Tool Output Icons Demo:[/bold]")
    render_tool_output("Files added successfully", status="success", console=console)
    render_tool_output("Connection timeout", status="error", console=console)
    render_tool_output("Large file detected", status="warning", console=console)
    render_tool_output("Processing request", status="info", console=console)

    # Assistant output with border
    console.print("\n[bold]Assistant Output Border Demo:[/bold]")
    render_assistant_output("This is a response from the assistant.\nIt can span multiple lines.", console=console)

    # User message with border
    console.print("\n[bold]User Message Border Demo:[/bold]")
    render_user_message("Please refactor this function to use async.", console=console)

    # Loading widget
    console.print("\n[bold]Loading Widget Demo:[/bold]")
    import time

    widget = LoadingWidget("Generating response...", console=console)
    widget.start()
    time.sleep(1.0)
    widget.update_text("Applying edits...")
    time.sleep(1.0)
    widget.stop(success=True, final_text="Done")

    # Progress indicator
    console.print("\n[bold]Progress Demo:[/bold]")
    with StyledProgress(console) as progress:
        task = progress.add_task("Processing...", total=100)
        for i in range(100):
            time.sleep(0.02)
            progress.update(task, advance=1)
