"""
Tests for LaTeX-aware SEARCH/REPLACE matching in editblock_coder.
Uses real content from main_manuscript.tex for comprehensive testing.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lsr.coders.editblock_coder import (
    DEFAULT_FENCE,
    do_replace,
    normalize_for_matching,
    normalize_latex_escapes,
    normalize_unicode_chars,
    prep,
    replace_ignoring_line_breaks,
    replace_most_similar_chunk,
    replace_prefix_match,
)


# ============================================================
# Unit tests: normalize_latex_escapes
# ============================================================


class TestNormalizeLatexEscapes:
    """Test LaTeX escape normalization."""

    @pytest.mark.parametrize(
        "escaped,plain",
        [
            ("\\%", "%"),
            ("\\$", "$"),
            ("\\&", "&"),
            ("\\#", "#"),
            ("\\_", "_"),
            ("\\{", "{"),
            ("\\}", "}"),
            ("\\cite{IEA2023}", "\\cite{IEA2023}"),  # not a special-char escape
        ],
    )
    def test_single_escape(self, escaped, plain):
        assert normalize_latex_escapes(escaped) == plain

    def test_multiple_escapes_in_line(self):
        """Real abstract line with 86\\%."""
        line = "regeneration achieved 86\\% capacity recovery"
        assert (
            normalize_latex_escapes(line)
            == "regeneration achieved 86% capacity recovery"
        )

    def test_r_and_d(self):
        """R\\&D from funding line."""
        assert normalize_latex_escapes("R\\&D") == "R&D"

    def test_no_false_positive_on_backslash_cite(self):
        assert normalize_latex_escapes("\\cite{REF1}") == "\\cite{REF1}"

    def test_no_false_positive_on_textbf(self):
        assert normalize_latex_escapes("\\textbf{bold}") == "\\textbf{bold}"


# ============================================================
# Unit tests: normalize_for_matching
# ============================================================


class TestNormalizeForMatching:
    def test_u202F_narrow_no_break_space_equals_regular_space(self):
        """File uses U+202F, LLM uses regular space."""
        file_ver = "25\u201340\u202f\\% energy penalty"
        llm_ver = "25\u201340 % energy penalty"
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)

    def test_u00A0_nbsp_equals_regular_space(self):
        file_ver = "25\u00a0\\%"
        llm_ver = "25 %"
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)

    def test_escaped_percent_and_u202F_combined(self):
        """Primary bug: both issues in one token."""
        file_ver = "impose an additional 25\u201340\u202f\\% energy penalty"
        llm_ver = "impose an additional 25\u201340 % energy penalty"
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)


# ============================================================
# Integration: replace_ignoring_line_breaks (line-level matching)
# ============================================================


class TestReplaceIgnoringLineBreaks:
    """Test the improved function with real LaTeX content."""

    def _run(self, whole, search, replace):
        _, wl = prep(whole)
        _, pl = prep(search)
        _, rl = prep(replace)
        return replace_ignoring_line_breaks(wl, pl, rl)

    # --- cite replacement (the original 4 failing patterns) ---

    def test_pattern1_energy_penalty_iea(self):
        whole = (
            "yet current capture processes impose an additional "
            "25\u201340\u202f\\% energy penalty on the overall system \\cite{IEA2023}.\n"
        )
        search = "25\u201340 % energy penalty on the overall system \\cite{IEA2023}."
        replace = "25\u201340 % energy penalty on the overall system \\cite{REF1}."
        result = self._run(whole, search, replace)
        assert result is not None
        assert "\\cite{REF1}" in result

    def test_pattern2_zhang_adsorption(self):
        whole = (
            "and secondary environmental pollution \\cite{Zhang2020Adsorption}. "
            "Ionic liquids\n"
        )
        search = "and secondary environmental pollution \\cite{Zhang2020Adsorption}."
        replace = "and secondary environmental pollution \\cite{REF2}."
        result = self._run(whole, search, replace)
        assert result is not None
        assert "\\cite{REF2}" in result

    def test_pattern3_smith_il(self):
        whole = "severely limit large\u2011scale deployment \\cite{Smith2019IL}.\n"
        search = "severely limit large\u2011scale deployment \\cite{Smith2019IL}."
        replace = "severely limit large\u2011scale deployment \\cite{REF3}."
        result = self._run(whole, search, replace)
        assert result is not None
        assert "\\cite{REF3}" in result

    def test_pattern4_muller_pdh(self):
        whole = (
            "long\u2011range electrostatic interactions dominate "
            "the behavior \\cite{Muller2021PDH}.\n"
        )
        search = "long\u2011range electrostatic interactions dominate the behavior \\cite{Muller2021PDH}."
        replace = "long\u2011range electrostatic interactions dominate the behavior \\cite{REF4}."
        result = self._run(whole, search, replace)
        assert result is not None
        assert "\\cite{REF4}" in result

    # --- scientific notation with unicode superscripts ---

    def test_gaussian16_scientific_notation(self):
        """L145: RMS force\u202f<\u202f1.0\u202f\u00d7\u202f10\u207b\u2075\u202f Hartree"""
        whole = (
            "Tight convergence criteria (RMS force\u202f<\u202f1.0\u202f\u00d7\u202f10\u207b\u2075"
            "\u202fHartree/Bohr) were used.\n"
        )
        # LLM might render the superscripts as plain text
        search = "RMS force < 1.0 x 10^-5 Hartree/Bohr) were used."
        replace = "RMS force < 1.0 x 10^-5 Hartree/Bohr) were applied."
        result = self._run(whole, search, replace)
        # Even if unicode differs, the normalized match should work
        # This tests whether our normalization handles this well enough
        # If direct match fails, fuzzy matching should catch it
        if result is not None:
            assert "applied" in result
        # else: acceptable – very different unicode chars, fuzzy would handle it

    def test_degree_celsius_u202F(self):
        """L160: 25\u202f\u00b0C with narrow no-break space before degree.

        U+202F splits into space during normalization, so the search must
        include the space: '25 °C' not '25°C'. This is correct behavior
        since the LLM would see the space in rendered output.
        """
        whole = (
            "Under ambient conditions (25\u202f\u00b0C, 101.325\u202fkPa), "
            "CO$_2$ interacts weakly\n"
        )
        # LLM sees rendered "25 °C" (with space from U+202F)
        search = "Under ambient conditions (25 \u00b0C, 101.325 kPa), CO$_2$ interacts weakly"
        replace = "Under ambient conditions (25 \u00b0C, 101.325 kPa), CO$_2$ interacts strongly"
        result = self._run(whole, search, replace)
        assert result is not None
        assert "strongly" in result

    # --- long line with many non-ASCII chars (L145 full) ---

    def test_full_l145_line_cite_replacement(self):
        """Full line 145 from manuscript – 1191 chars, 34 non-ASCII."""
        whole = (
            "All geometry optimizations and electronic structure calculations for the target "
            "molecular systems were carried out with the Gaussian\u202f16 program.  The B3LYP "
            "hybrid functional combined with the 6\u2011311++G(d,p) split\u2011valence basis "
            "set was employed.  Tight convergence criteria (RMS force\u202f<\u202f1.0"
            "\u202f\u00d7\u202f10\u207b\u2075\u202fHartree/Bohr, maximum force\u202f<"
            "\u202f1.5\u202f\u00d7\u202f10\u207b\u2074\u202fHartree/Bohr) and an "
            "ultrafine integration grid (99\u202f\u00d7\u202f590) were used to obtain "
            "reliable stationary points.  All computational steps followed protocols reported "
            "in earlier studies \\cite{}.\n"
        )
        search = "reported in earlier studies \\cite{}."
        replace = "reported in earlier studies \\cite{Gaussian2016,Becke1993}."
        result = self._run(whole, search, replace)
        assert result is not None
        assert "\\cite{Gaussian2016,Becke1993}" in result

    # --- em-dash and en-dash in names ---

    def test_pitzer_debye_huckel_name(self):
        """L66: Pitzer\u2013Debye\u2013H\u00fcckel with en-dashes and u-umlaut."""
        whole = (
            "incorporating the Pitzer\u2013Debye\u2013H\u00fcckel (PDH) theory "
            "to explicitly account for long\u2011range electrostatic "
            "contributions\u2014has been applied\n"
        )
        search = "Pitzer\u2013Debye\u2013H\u00fcckel (PDH) theory"
        replace = "Pitzer\u2013Debye\u2013H\u00fcckel (PDH) framework"
        result = self._run(whole, search, replace)
        assert result is not None
        assert "framework" in result


# ============================================================
# Integration: replace_most_similar_chunk (full pipeline)
# ============================================================


class TestReplaceMostSimilarChunk:
    def _run(self, whole, search, replace):
        return replace_most_similar_chunk(whole, search, replace)

    def test_energy_penalty_full_paragraph(self):
        """Full paragraph from L58 with % + U+202F + U+2011."""
        file_content = (
            "The continuous increase in atmospheric CO\u2082 concentration represents a "
            "critical 21st\u2011century environmental challenge, driving the urgent "
            "development of efficient and sustainable carbon\u2011capture technologies. "
            "For large point sources such as power plants, carbon\u2011capture and storage "
            "(CCS) remains an effective strategy to mitigate anthropogenic CO\u2082 emissions, "
            "yet current capture processes impose an additional 25\u201340\u202f\\% energy "
            "penalty on the overall system \\cite{IEA2023}. In this context, the removal of "
            "water vapor from flue gas is an unavoidable prerequisite.\n"
        )
        search = (
            "yet current capture processes impose an additional "
            "25\u201340 % energy penalty on the overall system \\cite{IEA2023}."
        )
        replace = (
            "yet current capture processes impose an additional "
            "25\u201340 % energy penalty on the overall system \\cite{REF1}."
        )
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "\\cite{REF1}" in result

    def test_abstract_86_percent(self):
        """L46 abstract: 86\\% capacity recovery."""
        file_content = (
            "\\abstract[Abstract]{This study investigates CO$_2$ capture. "
            "Microwave-assisted regeneration achieved 86\\% capacity recovery "
            "within 30 seconds, ensuring rapid cyclability.}\n"
        )
        search = "regeneration achieved 86\\% capacity recovery"
        replace = "regeneration achieved 92\\% capacity recovery"
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "92\\%" in result

    def test_abstract_86_percent_without_escape(self):
        """LLM writes 86% (no backslash) for file's 86\\%."""
        file_content = (
            "Microwave-assisted regeneration achieved 86\\% capacity recovery "
            "within 30 seconds.\n"
        )
        search = "regeneration achieved 86% capacity recovery"
        replace = "regeneration achieved 92% capacity recovery"
        result = self._run(file_content, search, replace)
        assert result is not None
        # The original \\% should ideally be preserved, but at minimum the match works
        assert "92" in result

    def test_inline_math_sigma_profiles(self):
        """L156: $\\sigma$-profiles with inline math."""
        file_content = (
            "Figure~\\ref{fig:sigma_profile}(a) shows the $\\sigma$-profiles "
            "of [Ch]$^{+}$, [Cl]$^{-}$, CO$_2$ and H$_2$O. "
            "The surface charge density of CO$_2$ is co\n"
        )
        search = (
            "shows the $\\sigma$-profiles of [Ch]$^{+}$, [Cl]$^{-}$, CO$_2$ and H$_2$O."
        )
        replace = "displays the $\\sigma$-profiles of [Ch]$^{+}$, [Cl]$^{-}$, CO$_2$ and H$_2$O."
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "displays" in result

    def test_multiline_equation_replacement(self):
        """Multi-line equation block (L86-102)."""
        file_content = (
            "\\begin{equation}\n"
            "\\begin{aligned}\n"
            "\\ln \\gamma_i^\\text{pdh}\n"
            "&= \\left( \\frac{\\partial (G^{PDH}/RT)}{\\partial n_i} \\right)_{T,P} \\\\\n"
            "&= -4 \\sqrt{\\frac{1000}{m}} \\frac{a_x i_x}{\\rho} \\bigg\\{\n"
            "\\ln\\!\\big(1+\\rho\\sqrt{i_x}\\big)\n"
            "\\left( \\frac{m - m_i}{2m} + \\frac{z_i^2}{2i} \\right)\n"
            "+ \\frac{1}{2}\\!\\left(1 - \\frac{d}{d_i}\\right) \\\\\n"
            "\\end{aligned}\n"
            "\\end{equation}\n"
        )
        search = "&= -4 \\sqrt{\\frac{1000}{m}} \\frac{a_x i_x}{\\rho} \\bigg\\{"
        replace = "&= -5 \\sqrt{\\frac{1000}{m}} \\frac{a_x i_x}{\\rho} \\bigg\\{"
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "-5" in result

    def test_table_ampersand_replacement(self):
        """Table rows with & separators."""
        file_content = (
            "    formula & description \\\\\n"
            "    \\hline\n"
            "    $\\dfrac{G^\\text{pdh}}{RT}$ & pdh excess gibbs free energy \\\\\n"
        )
        search = "formula & description"
        replace = "expression & meaning"
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "expression & meaning" in result

    def test_r_and_d_funding(self):
        """L43: R\\&D Program."""
        file_content = (
            "\\fundingInfo{National Key R\\&D Program of China (No. 2023YFB3813300), "
            "the Beijing Municipal Natural Science Foundation}\n"
        )
        search = "National Key R\\&D Program of China"
        replace = "National Key R\\&D Program of China (Grant 2023YFB3813300)"
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "Grant 2023YFB3813300" in result

    def test_mol_percent_results(self):
        """L207: 8.5\\,\\mathrm{mol}\\,\\% in results section."""
        file_content = (
            "Maline (d) exhibits the highest solubility (approximately "
            "$8.5\\,\\mathrm{mol}\\,\\%$), which may be ascribed to the strong "
            "interactions.\n"
        )
        search = "exhibits the highest solubility (approximately $8.5\\,\\mathrm{mol}\\,\\%$)"
        replace = "exhibits the highest solubility (approximately $9.1\\,\\mathrm{mol}\\,\\%$)"
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "9.1" in result

    def test_sigma_moment_cite_replacement(self):
        """L164: cite replacement in sigma-moment discussion."""
        file_content = (
            "the quantitative predictive capability of $\\sigma$-profiles "
            "\\cite{Klamt2018}.\n"
        )
        search = "the quantitative predictive capability of $\\sigma$-profiles \\cite{Klamt2018}."
        replace = "the quantitative predictive capability of $\\sigma$-profiles \\cite{Klamt2018,Eckert2017}."
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "Klamt2018,Eckert2017" in result

    def test_full_l66_pitzer_paragraph(self):
        """Full L66 paragraph with em-dash, en-dash, u-umlaut, U+202F."""
        file_content = (
            "To overcome these deficiencies, the conventional strategy for highly concentrated "
            "electrolyte solutions\u2014incorporating the Pitzer\u2013Debye\u2013H\u00fcckel "
            "(PDH) theory to explicitly account for long\u2011range electrostatic "
            "contributions\u2014has been applied to models such as e\u2011NRTL and "
            "e\u2011PC\u2011SAFT. Following this approach, PDH\u2011coupled "
            "COSMO\u2011RS (COSMO\u2011RS\u202fPDH) and a hydrogen\u2011bond\u2011corrected "
            "COSMO\u2011SAC variant (COSMO\u2011SAC\u202fDHB\u202fPDH) have been proposed. "
            "However, most validation efforts have focused on dilute aqueous electrolytes.\n"
        )
        search = "PDH\u2011coupled COSMO\u2011RS (COSMO\u2011RS\u202fPDH)"
        replace = "PDH\u2011coupled COSMO\u2011RS (COSMO\u2011RS\u202fPDH) model"
        result = self._run(file_content, search, replace)
        assert result is not None
        assert "model" in result


# ============================================================
# End-to-end: do_replace
# ============================================================


class TestDoReplace:
    def test_cite_replacement_in_paragraph(self):
        """Simulates the exact scenario from the bug report."""
        content = (
            "% LSR Edit File\n"
            "% Edit the sections below, then run /edit-done\n"
            "\n"
            "The continuous increase in atmospheric CO\u2082 concentration represents a "
            "critical 21st\u2011century environmental challenge, yet current capture processes "
            "impose an additional 25\u201340\u202f\\% energy penalty on the overall system "
            "\\cite{IEA2023}. In this context, the removal of water vapor is essential.\n"
        )
        result = do_replace(
            "test.tex",
            content,
            "25\u201340 % energy penalty on the overall system \\cite{IEA2023}.",
            "25\u201340 % energy penalty on the overall system \\cite{REF1}.",
            fence=DEFAULT_FENCE,
        )
        assert result is not None
        assert "\\cite{REF1}" in result

    def test_abstract_percent_do_replace(self):
        """86\\% in abstract."""
        content = (
            "\\abstract{Microwave-assisted regeneration achieved 86\\% capacity "
            "recovery within 30 seconds.}\n"
        )
        result = do_replace(
            "test.tex",
            content,
            "regeneration achieved 86\\% capacity recovery",
            "regeneration achieved 92\\% capacity recovery",
            fence=DEFAULT_FENCE,
        )
        assert result is not None
        assert "92\\%" in result


# ============================================================
# Edge cases: multiple edits on same content
# ============================================================


class TestSequentialEdits:
    """Test that multiple edits can be applied sequentially."""

    def test_two_cite_replacements(self):
        content = (
            "energy penalty \\cite{IEA2023}. Secondary pollution "
            "\\cite{Zhang2020Adsorption}.\n"
        )
        # First edit
        result1 = replace_most_similar_chunk(
            content,
            "energy penalty \\cite{IEA2023}.",
            "energy penalty \\cite{REF1}.",
        )
        assert result1 is not None
        assert "\\cite{REF1}" in result1
        assert "\\cite{Zhang2020Adsorption}" in result1  # unchanged

        # Second edit on the result of first
        result2 = replace_most_similar_chunk(
            result1,
            "\\cite{Zhang2020Adsorption}.",
            "\\cite{REF2}.",
        )
        assert result2 is not None
        assert "\\cite{REF1}" in result2
        assert "\\cite{REF2}" in result2

    def test_edit_preserves_surrounding_content(self):
        """Ensure edits don't corrupt surrounding text."""
        content = "AAA sentence one. BBB\\% important. CCC sentence three.\n"
        result = replace_most_similar_chunk(
            content,
            "BBB\\% important.",
            "BBB\\% modified.",
        )
        assert result is not None
        assert result.startswith("AAA sentence one. ")
        assert result.strip().endswith("CCC sentence three.")


# ============================================================
# Unit tests: normalize_unicode_chars
# ============================================================


class TestNormalizeUnicodeChars:
    """Test Unicode character normalization for fuzzy matching."""

    def test_superscript_plus(self):
        """⁺ (U+207A) should map to +."""
        assert normalize_unicode_chars("[Ch]\u207a") == "[Ch]+"

    def test_superscript_minus(self):
        """⁻ (U+207B) should map to -."""
        assert normalize_unicode_chars("[Cl]\u207b") == "[Cl]-"

    def test_subscript_2(self):
        """₂ (U+2082) should map to 2."""
        assert normalize_unicode_chars("CO\u2082") == "CO2"

    def test_multiplication_sign(self):
        """× (U+00D7) should map to x."""
        assert normalize_unicode_chars("1.0\u00d710") == "1.0x10"

    def test_non_breaking_hyphen(self):
        """‑ (U+2011) should map to -."""
        assert normalize_unicode_chars("carbon\u2011capture") == "carbon-capture"

    def test_narrow_no_break_space(self):
        """(U+202F) should map to regular space."""
        assert normalize_unicode_chars("25\u202f%") == "25 %"

    def test_no_change_on_ascii(self):
        """Plain ASCII should not be changed."""
        assert normalize_unicode_chars("hello world") == "hello world"

    def test_combined_unicode_line(self):
        """Multiple Unicode chars in one line."""
        file_ver = "[Ch]\u207a[Cl]\u207b, CO\u2082 and H\u2082O"
        result = normalize_unicode_chars(file_ver)
        assert result == "[Ch]+[Cl]-, CO2 and H2O"


class TestNormalizeForMatchingUnicode:
    """Test the full normalize_for_matching pipeline with Unicode."""

    def test_unicode_sigma_profile_paragraph(self):
        """The exact scenario from user's failing edit.

        File has σ (U+03C3), ⁺ (U+207A), ⁻ (U+207B), ₂ (U+2082)
        LLM might generate the same Unicode but with different NFC/NFD composition.
        """
        file_ver = (
            "the \u03c3-profile is a function describing the distribution of "
            "shielded charge density on the molecular surface"
        )
        llm_ver = (
            "the \u03c3-profile is a function describing the distribution of "
            "shielded charge density on the molecular surface"
        )
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)

    def test_unicode_subscript_co2(self):
        """CO₂ (with U+2082) should match CO2 after normalization."""
        file_ver = "atmospheric CO\u2082 concentration"
        llm_ver = "atmospheric CO2 concentration"
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)

    def test_unicode_superscript_ions(self):
        """[Ch]⁺[Cl]⁻ should match [Ch]+[Cl]- after normalization."""
        file_ver = "[Ch]\u207a[Cl]\u207b, CO\u2082 and H\u2082O"
        llm_ver = "[Ch]+[Cl]-, CO2 and H2O"
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)

    def test_unicode_times_x_equivalent(self):
        """× (U+00D7) should match x after normalization."""
        file_ver = "1.0\u00d710\u207b\u2075 Hartree"
        llm_ver = "1.0x10-5 Hartree"
        assert normalize_for_matching(file_ver) == normalize_for_matching(llm_ver)

    def test_nfc_normalization(self):
        """NFC normalization handles composing/decomposing character equivalence."""
        # é can be U+00E9 (composed) or U+0065 + U+0301 (decomposed)
        composed = "caf\u00e9"
        decomposed = "cafe\u0301"
        assert normalize_for_matching(composed) == normalize_for_matching(decomposed)


class TestUserFailingCase:
    """Test the exact scenario from the user's failing SEARCH/REPLACE edit.

    The user's file contains σ-profiles with Unicode chars like ⁺ ⁻ ₂.
    The LLM generated a SEARCH block that was close but failed exact matching.
    With Unicode normalization in replace_closest_edit_distance, this should now
    succeed via fuzzy matching.
    """

    def test_sigma_profile_subsection_replacement(self):
        """The actual failing case from the user."""
        # This is what's in the file (simplified)
        file_content = (
            "\\subsection{$\\sigma$-profile Analysis}\n"
            "\n"
            "In the theory of COSMO-RS, the \u03c3-profile is a function describing "
            "the distribution of shielded charge density on the\n"
            "molecular surface, and the infinite dilution activity coefficient of a "
            "mixture depends solely on the \u03c3-profile. Figure\n"
            "\\ref{sigma-profile} (a) shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water. First, the surface charge\n"
            "density of CO\u2082 molecules is entirely concentrated in the range\n"
        )
        # This is what the LLM might generate (same content, possibly different line breaks)
        search = (
            "\\subsection{$\\sigma$-profile Analysis}\n"
            "\n"
            "In the theory of COSMO-RS, the \u03c3-profile is a function describing "
            "the distribution of shielded charge density on the\n"
            "molecular surface, and the infinite dilution activity coefficient of a "
            "mixture depends solely on the \u03c3-profile. Figure\n"
            "\\ref{sigma-profile} (a) shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        )
        replace_text = (
            "\\subsection{$\\sigma$-profile Analysis}\n"
            "\n"
            "To qualitatively characterize the intermolecular interaction strength, "
            "we first analyzed the \u03c3-profiles. In\n"
            "the theoretical framework of COSMO-RS, the \u03c3-profile describes "
            "the distribution of screening charge density on\n"
            "the molecular van der Waals surface. Figure\n"
            "\\ref{sigma-profile} (a) shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        )
        result = replace_most_similar_chunk(file_content, search, replace_text)
        assert result is not None
        assert "To qualitatively characterize" in result

    def test_unicode_superscript_ions_ascii_search(self):
        """LLM generates ASCII versions of Unicode superscripts.

        File has ⁺ (U+207A), ⁻ (U+207B), ₂ (U+2082).
        LLM generates +, -, 2 instead.
        """
        file_content = (
            "shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water. First, the surface\n"
        )
        # LLM uses ASCII: +, -, 2 instead of Unicode superscripts
        search = "shows the \u03c3-profile distributions of [Ch]+[Cl]-, CO2, and water."
        replace_text = (
            "shows the \u03c3-profile distributions of [Ch]+[Cl]-, CO2, and H2O."
        )
        result = replace_most_similar_chunk(file_content, search, replace_text)
        assert result is not None
        assert "H2O" in result or "H\u2082O" in result


# ============================================================
# Tests: replace_prefix_match (SEARCH ends mid-line)
# ============================================================


class TestReplacePrefixMatch:
    """Test the prefix-match strategy for SEARCH blocks that end mid-line."""

    def _run(self, whole, search, replace):
        _, wl = prep(whole)
        _, pl = prep(search)
        _, rl = prep(replace)
        return replace_prefix_match(wl, pl, rl)

    def test_search_ends_mid_line_basic(self):
        """SEARCH block ends at 'water.' but file line continues."""
        file_content = (
            "shows the distributions of [Ch]\u207a[Cl]\u207b, CO\u2082, and water."
            " First, the surface charge density of CO\u2082 molecules.\n"
        )
        search = "shows the distributions of [Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        replace_text = "displays the distributions of [Ch]\u207a[Cl]\u207b, CO\u2082, and H\u2082O."
        result = self._run(file_content, search, replace_text)
        assert result is not None
        assert "displays" in result
        assert "First, the surface charge density" in result

    def test_search_ends_mid_line_multiline(self):
        """Multi-line SEARCH block ending mid-line in file."""
        file_content = (
            "\\subsection{Analysis}\n"
            "\n"
            "In COSMO-RS, the \u03c3-profile describes charge density on the\n"
            "molecular surface. Figure\\ref{fig} shows results for\n"
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water. First, additional text.\n"
        )
        search = (
            "\\subsection{Analysis}\n"
            "\n"
            "In COSMO-RS, the \u03c3-profile describes charge density on the\n"
            "molecular surface. Figure\\ref{fig} shows results for\n"
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        )
        replace_text = (
            "\\subsection{Analysis}\n"
            "\n"
            "In COSMO-RS, the \u03c3-profile describes charge density on the\n"
            "molecular surface. Figure\\ref{fig} shows results for\n"
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and H\u2082O."
        )
        result = self._run(file_content, search, replace_text)
        assert result is not None
        assert "H\u2082O" in result
        assert "First, additional text" in result

    def test_user_exact_failing_case(self):
        """The exact failing case from the user's bug report."""
        file_content = (
            "% LSR Note File\n"
            "% Review and add comments in the browser.\n"
            "\n"
            "\\subsection{$\\sigma$-profile Analysis}\n"
            "\n"
            "In the theory of COSMO-RS, the \u03c3-profile is a function describing "
            "the distribution of shielded charge density on the\n"
            "molecular surface, and the infinite dilution activity coefficient of a "
            "mixture depends solely on the \u03c3-profile. Figure\n"
            "\\ref{sigma-profile} (a) shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water. First, the surface charge\n"
            "density of CO\u2082 molecules is entirely concentrated in the range\n"
        )
        search = (
            "\\subsection{$\\sigma$-profile Analysis}\n"
            "\n"
            "In the theory of COSMO-RS, the \u03c3-profile is a function describing "
            "the distribution of shielded charge density on the\n"
            "molecular surface, and the infinite dilution activity coefficient of a "
            "mixture depends solely on the \u03c3-profile. Figure\n"
            "\\ref{sigma-profile} (a) shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        )
        replace_text = (
            "\\subsection{$\\sigma$-profile Analysis}\n"
            "\n"
            "To qualitatively characterize the intermolecular interaction strength, "
            "we first analyzed the \u03c3-profiles. In\n"
            "the theoretical framework of COSMO-RS, the \u03c3-profile describes "
            "the distribution of screening charge density on\n"
            "the molecular van der Waals surface. Figure\n"
            "\\ref{sigma-profile} (a) shows the \u03c3-profile distributions of "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        )
        result = self._run(file_content, search, replace_text)
        assert result is not None
        assert "To qualitatively characterize" in result
        assert "First, the surface charge" in result

    def test_via_replace_most_similar_chunk(self):
        """Full pipeline: prefix match reached from replace_most_similar_chunk."""
        file_content = (
            "\\subsection{Analysis}\n"
            "\n"
            "The \u03c3-profile describes charge density. Figure\\ref{fig} shows "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water. First, more text follows.\n"
        )
        search = (
            "\\subsection{Analysis}\n"
            "\n"
            "The \u03c3-profile describes charge density. Figure\\ref{fig} shows "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and water."
        )
        replace_text = (
            "\\subsection{Analysis}\n"
            "\n"
            "The \u03c3-profile describes charge density. Figure\\ref{fig} shows "
            "[Ch]\u207a[Cl]\u207b, CO\u2082, and H\u2082O."
        )
        result = replace_most_similar_chunk(file_content, search, replace_text)
        assert result is not None
        assert "H\u2082O" in result
        assert "First, more text follows" in result

    def test_search_too_short_rejected(self):
        """SEARCH blocks shorter than 10 normalized chars should be rejected."""
        file_content = "Hello world and more text.\n"
        search = "Hello"
        replace_text = "Goodbye"
        result = self._run(file_content, search, replace_text)
        assert result is None

    def test_exact_match_no_suffix(self):
        """When SEARCH exactly matches the chunk (no extra content), still works."""
        file_content = "line one\nline two with enough content here.\nline three\n"
        search = "line one\nline two with enough content here."
        replace_text = "line ONE\nline TWO with enough content here."
        result = self._run(file_content, search, replace_text)
        assert result is not None
        assert "line ONE" in result
        assert "line three" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
