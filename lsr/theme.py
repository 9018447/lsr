"""
Catppuccin Mocha theme configuration for lsr.

This module provides a unified color theme based on Catppuccin Mocha palette.
https://catppuccin.com/palette
"""

from rich.theme import Theme


class CatppuccinMocha:
    """Catppuccin Mocha color palette."""

    # Accents
    ROSEWATER = "#f5e0dc"
    FLAMINGO = "#f2cdcd"
    PINK = "#f5c2e7"
    MAUVE = "#cba6f7"
    RED = "#f38ba8"
    MAROON = "#eba0ac"
    PEACH = "#fab387"
    YELLOW = "#f9e2af"
    GREEN = "#a6e3a1"
    TEAL = "#94e2d5"
    SKY = "#89dceb"
    SAPPHIRE = "#74c7ec"
    BLUE = "#89b4fa"
    LAVENDER = "#b4befe"

    # Neutrals
    TEXT = "#cdd6f4"
    SUBTEXT1 = "#bac2de"
    SUBTEXT0 = "#a6adc8"
    OVERLAY2 = "#9399b2"
    OVERLAY1 = "#7f849c"
    OVERLAY0 = "#6c7086"
    SURFACE2 = "#585b70"
    SURFACE1 = "#45475a"
    SURFACE0 = "#313244"
    BASE = "#1e1e2e"
    MANTLE = "#181825"
    CRUST = "#11111b"

    # Reset code for terminal output
    RESET = "\033[0m"


# Rich theme that overrides default green colors with Mocha palette
MOCHA_THEME = Theme(
    {
        # Override default green elements - this fixes the green lines!
        "rule.line": CatppuccinMocha.SURFACE2,
        "progress.spinner": CatppuccinMocha.MAUVE,
        "progress.download": CatppuccinMocha.GREEN,
        "progress.filesize": CatppuccinMocha.TEAL,
        "progress.filesize.total": CatppuccinMocha.TEAL,
        "progress.percentage": CatppuccinMocha.MAUVE,
        "progress.remaining": CatppuccinMocha.SKY,
        "progress.elapsed": CatppuccinMocha.YELLOW,
        "status.spinner": CatppuccinMocha.MAUVE,
        # Override repr styles
        "repr.str": CatppuccinMocha.GREEN,
        "repr.bool_true": CatppuccinMocha.GREEN,
        "repr.bool_false": CatppuccinMocha.RED,
        "repr.number": CatppuccinMocha.TEAL,
        "repr.none": CatppuccinMocha.MAUVE,
        "repr.url": f"underline {CatppuccinMocha.SAPPHIRE}",
        "repr.path": CatppuccinMocha.LAVENDER,
        "repr.filename": CatppuccinMocha.YELLOW,
        # Override JSON styles
        "json.str": CatppuccinMocha.GREEN,
        "json.bool_true": CatppuccinMocha.GREEN,
        "json.bool_false": CatppuccinMocha.RED,
        "json.number": CatppuccinMocha.TEAL,
        "json.null": CatppuccinMocha.MAUVE,
        "json.key": CatppuccinMocha.BLUE,
        # Override logging styles
        "logging.level.debug": CatppuccinMocha.OVERLAY1,
        "logging.level.info": CatppuccinMocha.SKY,
        "logging.level.warning": CatppuccinMocha.YELLOW,
        "logging.level.error": CatppuccinMocha.RED,
        "logging.level.critical": f"bold {CatppuccinMocha.RED}",
        # Override markdown styles
        "markdown.h1": f"bold {CatppuccinMocha.LAVENDER}",
        "markdown.h2": f"underline {CatppuccinMocha.MAUVE}",
        "markdown.h3": f"bold {CatppuccinMocha.SAPPHIRE}",
        "markdown.item.bullet": CatppuccinMocha.OVERLAY1,
        "markdown.item.number": CatppuccinMocha.TEAL,
        "markdown.link": CatppuccinMocha.SAPPHIRE,
        "markdown.link_url": f"underline {CatppuccinMocha.BLUE}",
        # Override table styles
        "table.header": f"bold {CatppuccinMocha.MAUVE}",
        "table.border": CatppuccinMocha.SURFACE2,
        "table.title": f"italic {CatppuccinMocha.LAVENDER}",
        # Override bar styles
        "bar.back": CatppuccinMocha.SURFACE0,
        "bar.complete": CatppuccinMocha.MAUVE,
        "bar.finished": CatppuccinMocha.GREEN,
        "bar.pulse": CatppuccinMocha.MAUVE,
        # Override traceback styles
        "traceback.border": CatppuccinMocha.RED,
        "traceback.note": f"bold {CatppuccinMocha.GREEN}",
    }
)


# Semantic color mapping for lsr UI components
THEME = {
    # User interaction
    "user_input_color": CatppuccinMocha.BLUE,
    "user_prompt_color": CatppuccinMocha.SAPPHIRE,
    # Tool output
    "tool_output_color": CatppuccinMocha.TEXT,
    "tool_error_color": CatppuccinMocha.RED,
    "tool_warning_color": CatppuccinMocha.PEACH,
    "tool_success_color": CatppuccinMocha.GREEN,
    "tool_info_color": CatppuccinMocha.TEAL,
    # AI Assistant
    "assistant_output_color": CatppuccinMocha.LAVENDER,
    "assistant_thinking_color": CatppuccinMocha.OVERLAY1,
    # Code & Syntax
    "code_theme": "monokai",  # Monokai pairs well with Mocha
    "code_keyword_color": CatppuccinMocha.MAUVE,
    "code_string_color": CatppuccinMocha.GREEN,
    "code_comment_color": CatppuccinMocha.OVERLAY1,
    # UI Elements
    "border_color": CatppuccinMocha.OVERLAY2,
    "separator_color": CatppuccinMocha.SURFACE2,
    "highlight_bg": CatppuccinMocha.SURFACE0,
    "selection_bg": CatppuccinMocha.SURFACE1,
    # Status indicators
    "status_success": CatppuccinMocha.GREEN,
    "status_error": CatppuccinMocha.RED,
    "status_warning": CatppuccinMocha.YELLOW,
    "status_info": CatppuccinMocha.SKY,
    "status_processing": CatppuccinMocha.MAUVE,
    # File & Path
    "file_name_color": CatppuccinMocha.YELLOW,
    "path_color": CatppuccinMocha.SAPPHIRE,
    "line_number_color": CatppuccinMocha.OVERLAY0,
    # Completion menu
    "completion_menu_color": CatppuccinMocha.TEXT,
    "completion_menu_bg_color": CatppuccinMocha.SURFACE0,
    "completion_menu_current_color": CatppuccinMocha.BASE,
    "completion_menu_current_bg_color": CatppuccinMocha.MAUVE,
    # Prompt
    "prompt_prefix_color": CatppuccinMocha.LAVENDER,
    "prompt_continuation_color": CatppuccinMocha.OVERLAY1,
}


# Symbols for UI elements (Unicode)
SYMBOLS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "arrow_right": "→",
    "arrow_left": "←",
    "arrow_up": "↑",
    "arrow_down": "↓",
    "bullet": "•",
    "separator": "│",
    "separator_horizontal": "─",
    "corner_top_left": "╭",
    "corner_top_right": "╮",
    "corner_bottom_left": "╰",
    "corner_bottom_right": "╯",
    "line": "─",
    "line_double": "═",
    "spinner": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
}


def get_prompt_prefix(edit_format: str | None = None) -> str:
    """Get styled prompt prefix based on edit format."""
    prefix_styles: dict[str, str] = {
        "ask": CatppuccinMocha.SAPPHIRE,
        "code": CatppuccinMocha.MAUVE,
        "help": CatppuccinMocha.TEAL,
    }

    style = prefix_styles.get(edit_format or "", CatppuccinMocha.LAVENDER)
    label = edit_format if edit_format else ""
    return f"[{style}]{label}>[/{style}] "
