"""
PlanCoder for /plan mode.

In plan mode the LLM explores the codebase and produces
a structured plan. It NEVER edits files.
"""

from .base_coder import Coder
from .plan_prompts import PlanPrompts


class PlanCoder(Coder):
    edit_format = "plan"
    gpt_prompts = PlanPrompts()

    def get_edits(self):
        """Plan mode never edits files."""
        return []

    def apply_edits(self, edits):
        pass
