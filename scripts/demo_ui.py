#!/usr/bin/env python
"""
Demo script for Catppuccin Mocha UI components.

Run this script to see all UI components in action.
"""

import time

from rich.console import Console

from lsr.status_bar import StatusBar
from lsr.theme import CatppuccinMocha as Mocha, get_prompt_prefix
from lsr.ui_components import (
    StyledProgress,
    render_command_help,
    render_diff_table,
    render_file_table,
    render_token_summary,
)


def demo_theme_colors(console: Console):
    """Demo the theme color palette."""
    console.print("\n[bold]1. Theme Colors[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    colors = [
        ("Rosewater", Mocha.ROSEWATER),
        ("Flamingo", Mocha.FLAMINGO),
        ("Pink", Mocha.PINK),
        ("Mauve", Mocha.MAUVE),
        ("Red", Mocha.RED),
        ("Maroon", Mocha.MAROON),
        ("Peach", Mocha.PEACH),
        ("Yellow", Mocha.YELLOW),
        ("Green", Mocha.GREEN),
        ("Teal", Mocha.TEAL),
        ("Sky", Mocha.SKY),
        ("Sapphire", Mocha.SAPPHIRE),
        ("Blue", Mocha.BLUE),
        ("Lavender", Mocha.LAVENDER),
    ]

    for name, color in colors:
        console.print(f"  {name:12} {color}", style=color)


def demo_file_table(console: Console):
    """Demo the file table component."""
    console.print("\n[bold]2. File Table[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    files = [
        "lsr/main.py",
        "lsr/io.py",
        "lsr/theme.py",
        "lsr/ui_components.py",
        "lsr/status_bar.py",
        "README.md",
        "pyproject.toml",
    ]
    tokens = [4500, 3200, 850, 1200, 650, 1800, 450]

    table = render_file_table(files, tokens, title="Chat Files")
    console.print(table)


def demo_token_summary(console: Console):
    """Demo the token summary panel."""
    console.print("\n[bold]3. Token Summary[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    # Low usage
    console.print("\n[dim]Low usage (< 50%):[/dim]")
    console.print(render_token_summary("gpt-4", 30000, 128000, 0.0750))

    # Medium usage
    console.print("\n[dim]Medium usage (50-80%):[/dim]")
    console.print(render_token_summary("gpt-4", 80000, 128000, 0.2000))

    # High usage
    console.print("\n[dim]High usage (> 80%):[/dim]")
    console.print(render_token_summary("gpt-4", 110000, 128000, 0.2750))


def demo_command_help(console: Console):
    """Demo the command help panel."""
    console.print("\n[bold]4. Command Help[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    console.print(
        render_command_help(
            "add",
            "Add files to the chat session. Supports glob patterns.",
            "/add *.py src/**/*.ts",
        )
    )


def demo_diff_table(console: Console):
    """Demo the diff table component."""
    console.print("\n[bold]5. Diff Table[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    old_lines = [
        "def hello():",
        "    print('Hello')",
        "",
        "def goodbye():",
        "    print('Goodbye')",
    ]
    new_lines = [
        "def hello(name: str):",
        "    print(f'Hello {name}')",
        "",
        "def goodbye(name: str):",
        "    print(f'Goodbye {name}')",
        "",
        "def welcome(name: str):",
        "    print(f'Welcome {name}')",
    ]

    console.print(render_diff_table(old_lines, new_lines, "example.py"))


def demo_prompt_prefix(console: Console):
    """Demo the prompt prefix styles."""
    console.print("\n[bold]6. Prompt Prefixes[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    formats = ["ask", "code", "help", None]
    for fmt in formats:
        prefix = get_prompt_prefix(fmt)
        label = fmt if fmt else "default"
        console.print(f"  {label:8} {prefix}Some user input here...")


def demo_progress(console: Console):
    """Demo the progress indicator."""
    console.print("\n[bold]7. Progress Indicator[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    with StyledProgress(console) as progress:
        task = progress.add_task("Processing files...", total=50)
        for _ in range(50):
            time.sleep(0.05)
            progress.update(task, advance=1)


def demo_status_bar(console: Console, io):
    """Demo the status bar."""
    console.print("\n[bold]8. Status Bar[/bold]", style=Mocha.LAVENDER)
    console.print("=" * 50, style=Mocha.SURFACE2)

    status = StatusBar(io)
    context = {
        "model": "gpt-4",
        "files": ["main.py", "utils.py", "theme.py"],
        "tokens": 45000,
        "edit_format": "code",
        "git_branch": "main",
    }
    status.render(context)


def main():
    """Run all demos."""
    console = Console()

    console.print("\n" + "=" * 60, style=Mocha.MAUVE)
    console.print(
        "  Catppuccin Mocha UI Components Demo", style=f"bold {Mocha.LAVENDER}"
    )
    console.print("=" * 60, style=Mocha.MAUVE)

    # Create a minimal IO object for StatusBar demo
    from lsr.io import InputOutput

    io = InputOutput(pretty=True)

    demo_theme_colors(console)
    demo_file_table(console)
    demo_token_summary(console)
    demo_command_help(console)
    demo_diff_table(console)
    demo_prompt_prefix(console)
    demo_progress(console)
    demo_status_bar(console, io)

    console.print("\n" + "=" * 60, style=Mocha.MAUVE)
    console.print("  Demo Complete!", style=f"bold {Mocha.GREEN}")
    console.print("=" * 60, style=Mocha.MAUVE)


if __name__ == "__main__":
    main()
