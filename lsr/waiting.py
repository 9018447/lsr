#!/usr/bin/env python

"""
Thread-based, killable spinner utility with multi-frame support,
elapsed time display, and status transitions.

Use it like:

    from lsr.waiting import WaitingSpinner

    spinner = WaitingSpinner("Waiting for LLM")
    spinner.start()
    ...  # long task
    spinner.stop(success=True)
"""

import sys
import threading
import time

from rich.console import Console

from lsr.theme import BRAILLE_FRAMES, DOTS_FRAMES, MOCHA_GRADIENT, PULSE_FRAMES, SYMBOLS
from lsr.theme import CatppuccinMocha as Mocha


class Spinner:
    """
    Minimal spinner that cycles through unicode frames with color and elapsed time.

    Supports multiple frame sets (Braille, Pulse, Dots) and gradient color cycling.
    Automatically detects unicode support and falls back to ASCII if needed.
    """

    last_frame_idx = 0  # Class variable to store the last frame index

    def __init__(
        self,
        text: str,
        frames: list[str] | None = None,
        colors: list[str] | None = None,
        show_elapsed: bool = True,
        delay: float = 0.12,
    ):
        self.text = text
        self.show_elapsed = show_elapsed
        self.delay = delay
        self.start_time = time.time()
        self.last_update = 0.0
        self.visible = False
        self.is_tty = sys.stdout.isatty()
        self.console = Console()

        # Frame set selection with unicode fallback
        if frames is None:
            frames = BRAILLE_FRAMES
        self.frames = frames if self._supports_unicode() else ["+", "x", "*"]
        self.frame_idx = Spinner.last_frame_idx % max(1, len(self.frames))

        # Color cycling
        self.colors = colors if colors else MOCHA_GRADIENT
        self.color_idx = 0

        self.last_display_len = 0  # Length of the last spinner line

    def _supports_unicode(self) -> bool:
        if not self.is_tty:
            return False
        try:
            test = "⠋"
            sys.stdout.write(test + "\b \b")
            sys.stdout.flush()
            return True
        except (UnicodeEncodeError, Exception):
            return False

    def _next_frame(self) -> tuple[str, str]:
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        Spinner.last_frame_idx = self.frame_idx
        color = self.colors[self.color_idx % len(self.colors)]
        self.color_idx = (self.color_idx + 1) % len(self.colors)
        return frame, color

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
            seconds = int(elapsed % 60)
            return f"{hours}h{minutes:02d}m{seconds:02d}s"

    @staticmethod
    def _ansi_color(hex_color: str) -> str:
        """Convert hex color to ANSI foreground escape sequence."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"\033[38;2;{r};{g};{b}m"

    def step(self, text: str | None = None) -> None:
        if text is not None:
            self.text = text

        if not self.is_tty:
            return

        now = time.time()
        if not self.visible and now - self.start_time >= 0.5:
            self.visible = True
            self.last_update = 0.0
            self.console.show_cursor(False)

        if not self.visible or now - self.last_update < self.delay:
            return

        self.last_update = now
        frame, color = self._next_frame()

        elapsed_str = f" {self._format_elapsed()}" if self.show_elapsed else ""
        color_ansi = self._ansi_color(color)
        reset = "\033[0m"
        line_to_display = f"{color_ansi}{frame}{reset} {self.text}{elapsed_str}"

        max_width = max(0, self.console.width - 2)
        if len(line_to_display) > max_width:
            line_to_display = line_to_display[:max_width]

        padding = " " * max(0, self.last_display_len - len(line_to_display))

        sys.stdout.write(f"\r{line_to_display}{padding}")
        self.last_display_len = len(line_to_display)
        sys.stdout.flush()

    def end(self, success: bool | None = None, final_text: str | None = None) -> None:
        if self.visible and self.is_tty:
            # Clear the spinner line
            sys.stdout.write("\r" + " " * self.last_display_len + "\r")
            sys.stdout.flush()
            if success is not None:
                icon = SYMBOLS["spinner_success"] if success else SYMBOLS["spinner_failure"]
                color = Mocha.GREEN if success else Mocha.RED
                text = final_text if final_text is not None else self.text
                elapsed_str = f" {self._format_elapsed()}" if self.show_elapsed else ""
                self.console.print(f"[{color}]{icon}[/{color}] {text}{elapsed_str}")
            self.console.show_cursor(True)
        self.visible = False


class WaitingSpinner:
    """Background spinner that can be started/stopped safely with status transitions."""

    def __init__(
        self,
        text: str = "Waiting for LLM",
        delay: float = 0.12,
        frames: list[str] | None = None,
        show_elapsed: bool = True,
    ):
        self.spinner = Spinner(text, frames=frames, show_elapsed=show_elapsed, delay=delay)
        self.delay = delay
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        while not self._stop_event.is_set():
            self.spinner.step()
            time.sleep(self.delay)
        # Do not call end here; let stop() handle the final state

    def start(self):
        """Start the spinner in a background thread."""
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self, success: bool | None = None, final_text: str | None = None):
        """Request the spinner to stop and display final status.

        Args:
            success: True shows ✓ green, False shows ✗ red, None clears silently.
            final_text: Optional text to display on stop (defaults to spinner text).
        """
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self.delay * 2)
        self.spinner.end(success=success, final_text=final_text)

    # Allow use as a context-manager
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        self.stop(success=success)


def main():
    import time

    print("Demo: Braille spinner with elapsed time")
    spinner = Spinner("Running spinner...", frames=BRAILLE_FRAMES)
    try:
        for _ in range(40):
            time.sleep(0.08)
            spinner.step()
        spinner.end(success=True, final_text="Completed!")
    except KeyboardInterrupt:
        spinner.end(success=False, final_text="Interrupted")

    time.sleep(0.5)
    print("\nDemo: Pulse spinner")
    spinner2 = Spinner("Pulsing...", frames=PULSE_FRAMES, show_elapsed=False)
    for _ in range(20):
        time.sleep(0.15)
        spinner2.step()
    spinner2.end(success=True)

    time.sleep(0.5)
    print("\nDemo: Dots spinner with failure")
    spinner3 = Spinner("Loading data...", frames=DOTS_FRAMES)
    for _ in range(20):
        time.sleep(0.1)
        spinner3.step()
    spinner3.end(success=False, final_text="Failed to load")

    time.sleep(0.5)
    print("\nDemo: WaitingSpinner (threaded)")
    ws = WaitingSpinner("Threaded task...", delay=0.1)
    ws.start()
    time.sleep(2.0)
    ws.stop(success=True, final_text="Threaded task done")


if __name__ == "__main__":
    main()
