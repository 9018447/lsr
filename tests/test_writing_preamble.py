"""Guards for the scientific-writing preamble (the global system-level prompt).

The preamble embeds three writing skills so lsr (which has no skill loader) applies
them in every edit mode:
- scientific-writing  -> Standards 1 & 4 (IMRAD, citations, reporting guidelines)
- paper-writing       -> Standard 2 (strategic argument & claim discipline)
- humanize-academic-writing -> Standard 3.G (anti-AI-writing patterns)

These tests assert the embedded principles stay present, so the embedding does not
silently regress.
"""

from lsr.coders.base_prompts import CoderPrompts


class TestScientificWritingPreamble:
    def test_all_four_standards_present(self):
        p = CoderPrompts.scientific_writing_preamble
        for std in ("STANDARD 1", "STANDARD 2", "STANDARD 3", "STANDARD 4"):
            assert std in p, f"{std} missing from scientific_writing_preamble"

    def test_embeds_paper_writing_claim_discipline(self):
        """paper-writing: underclaim/overdeliver, mechanism-first, reverse-outline."""
        p = CoderPrompts.scientific_writing_preamble
        assert "Underclaim in prose" in p
        assert "Lead with mechanism" in p
        assert "Reverse-outline" in p
        assert "one decisive figure" in p

    def test_embeds_humanize_anti_ai_patterns(self):
        """humanize-academic-writing: burstiness, abstract scaffolding, transitions."""
        p = CoderPrompts.scientific_writing_preamble
        assert "AVOID AI-WRITING PATTERNS" in p
        assert "Burstiness" in p
        assert "abstract scaffolding" in p

    def test_embeds_scientific_writing_craft(self):
        """scientific-writing: IMRAD, full-paragraph prose; clinical guidelines as pointer."""
        p = CoderPrompts.scientific_writing_preamble
        assert "IMRAD" in p
        assert "NEVER bullet-point" in p
        # Clinical reporting guidelines retained only as a pointer (4.4), not primary.
        assert "CONSORT" in p and "PRISMA" in p

    def test_retargeted_to_stem_reproducibility(self):
        """Standard 4 retargeted from clinical reporting to STEM reproducibility."""
        p = CoderPrompts.scientific_writing_preamble
        assert "REPRODUCIBILITY & TRANSPARENCY (STEM)" in p
        assert "error bars" in p
        assert "ablation" in p
        assert "Zenodo" in p

    def test_stem_notation_guidance(self):
        """1.5 retargeted to STEM math notation, units, chemical formulas."""
        p = CoderPrompts.scientific_writing_preamble
        assert "Scalars" in p and "Vectors" in p and "Matrices" in p
        assert "\\mathbf{x}" in p  # rendered LaTeX (single braces; preamble not .format()-ed)
        assert "SI throughout" in p

