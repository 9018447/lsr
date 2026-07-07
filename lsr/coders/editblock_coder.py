import difflib
import math
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from lsr import utils

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .edit_log import EditLog, FallbackTag
from .editblock_prompts import EditBlockPrompts


class EditBlockCoder(Coder):
    """A coder that uses search/replace blocks for code modifications."""

    edit_format = "diff"
    gpt_prompts = EditBlockPrompts()

    def get_edits(self):
        content = self.partial_response_content

        # might raise ValueError for malformed ORIG/UPD blocks
        edits = list(
            find_original_update_blocks(
                content,
                self.fence,
                self.get_inchat_relative_files(),
            )
        )

        # Separate shell commands and file edits
        shell_edits = []
        file_edits = []
        anchor_edits = []

        for edit in edits:
            if edit[0] is None:
                shell_edits.append(edit)
            elif len(edit) == 5 and edit[1] == "ANCHOR":
                # Anchor-based edit: (filename, 'ANCHOR', head_anchor, tail_anchor, updated_text)
                anchor_edits.append(edit)
            else:
                file_edits.append(edit)

        self.shell_commands += [edit[1] for edit in shell_edits]

        # Process anchor edits - convert them to standard format
        edit_log = EditLog(self.io)
        model_name = self.main_model.name if self.main_model else None
        for anchor_edit in anchor_edits:
            filename, _, head_anchor, tail_anchor, updated_text = anchor_edit
            full_path = self.abs_root_path(filename)

            if Path(full_path).exists():
                content = self.io.read_text(full_path)
                # Use anchor replacement
                from .anchor_replace import anchor_replace_with_tag

                new_content, tag = anchor_replace_with_tag(
                    content, head_anchor, tail_anchor, updated_text
                )
                outcome = "applied" if new_content else "failed"
                edit_log.log(full_path, model_name, outcome, tag)
                if new_content:
                    # Write the result directly
                    if True:  # not dry_run
                        self.io.write_text(full_path, new_content)
                    # Add to passed list for reporting
                    file_edits.append(
                        (filename, head_anchor[:50] + "...", updated_text[:50] + "...")
                    )
            else:
                edit_log.log(
                    full_path,
                    model_name,
                    "failed",
                    FallbackTag.ANCHOR_HEADTAIL,
                )

        return file_edits

    def apply_edits_dry_run(self, edits):
        return self.apply_edits(edits, dry_run=True)

    def apply_edits(self, edits, dry_run=False):
        failed = []
        passed = []
        updated_edits = []
        edit_log = EditLog(self.io)
        model_name = self.main_model.name if self.main_model else None

        for edit in edits:
            # Check if this is an anchor-based edit
            if len(edit) == 3 and edit[1].startswith("ANCHOR:"):
                # Anchor-based edit: (filename, "ANCHOR: head_anchor...", "tail_anchor...")
                path, head_info, tail_info = edit
                # These are already processed in get_edits, just add to passed
                passed.append(edit)
                updated_edits.append(edit)
                continue

            path, original, updated = edit
            full_path = self.abs_root_path(path)
            new_content = None
            tag = None

            if Path(full_path).exists():
                content = self.io.read_text(full_path)
                new_content, tag = do_replace_with_tag(
                    full_path, content, original, updated, self.fence
                )

            # If the edit failed, and
            # this is not a "create a new file" with an empty original...
            # https://github.com/your-username/lsr/issues/2258
            if not new_content and original.strip():
                # try patching any of the other files in the chat
                for full_path in self.abs_fnames:
                    content = self.io.read_text(full_path)
                    new_content, tag = do_replace_with_tag(
                        full_path, content, original, updated, self.fence
                    )
                    if new_content:
                        path = self.get_rel_fname(full_path)
                        break

            updated_edits.append((path, original, updated))

            if new_content:
                if not dry_run:
                    self.io.write_text(full_path, new_content)
                passed.append(edit)
                edit_log.log(full_path, model_name, "applied", tag)
            else:
                failed.append(edit)
                edit_log.log(
                    full_path,
                    model_name,
                    "failed",
                    tag or FallbackTag.EDIT_DISTANCE,
                )

        if dry_run:
            return updated_edits

        if not failed:
            return

        blocks = "block" if len(failed) == 1 else "blocks"

        res = f"# {len(failed)} SEARCH/REPLACE {blocks} failed to match!\n"
        for edit in failed:
            path, original, updated = edit

            full_path = self.abs_root_path(path)
            content = self.io.read_text(full_path)

            res += f"""
## SearchReplaceNoExactMatch: This SEARCH block failed to exactly match lines in {path}
<<<<<<< SEARCH
{original}=======
{updated}>>>>>>> REPLACE

"""
            did_you_mean = find_similar_lines(original, content)
            if did_you_mean:
                res += f"""Did you mean to match some of these actual lines from {path}?

{self.fence[0]}
{did_you_mean}
{self.fence[1]}

"""

            if updated in content and updated:
                res += f"""Are you sure you need this SEARCH/REPLACE block?
The REPLACE lines are already in {path}!

"""
        res += (
            "The SEARCH section must exactly match an existing block of lines including all white"
            " space, comments, indentation, docstrings, etc\n"
        )
        if passed:
            pblocks = "block" if len(passed) == 1 else "blocks"
            res += f"""
# The other {len(passed)} SEARCH/REPLACE {pblocks} were applied successfully.
Don't re-send them.
Just reply with fixed versions of the {blocks} above that failed to match.
"""
        raise ValueError(res)


def prep(content):
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines


def perfect_or_whitespace_with_tag(whole_lines, part_lines, replace_lines):
    # Try for a perfect match
    res = perfect_replace(whole_lines, part_lines, replace_lines)
    if res:
        return res, FallbackTag.PERFECT

    # Try being flexible about leading whitespace
    res = replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines)
    if res:
        return res, FallbackTag.MISSING_WHITESPACE

    return None, None


def perfect_or_whitespace(whole_lines, part_lines, replace_lines):
    res, _tag = perfect_or_whitespace_with_tag(whole_lines, part_lines, replace_lines)
    return res


# Unicode math/symbol → ASCII mapping for fuzzy matching.
# LLMs often render Unicode symbols as their ASCII lookalikes.
UNICODE_TO_ASCII = {
    # Superscripts
    "\u207a": "+",  # ⁺ SUPERSCRIPT PLUS
    "\u207b": "-",  # ⁻ SUPERSCRIPT MINUS
    "\u2070": "0",  # ⁰ SUPERSCRIPT ZERO
    "\u00b9": "1",  # ¹ SUPERSCRIPT ONE
    "\u00b2": "2",  # ² SUPERSCRIPT TWO
    "\u00b3": "3",  # ³ SUPERSCRIPT THREE
    "\u2074": "4",  # ⁴ SUPERSCRIPT FOUR
    "\u2075": "5",  # ⁵ SUPERSCRIPT FIVE
    "\u2076": "6",  # ⁶ SUPERSCRIPT SIX
    "\u2077": "7",  # ⁷ SUPERSCRIPT SEVEN
    "\u2078": "8",  # ⁸ SUPERSCRIPT EIGHT
    "\u2079": "9",  # ⁹ SUPERSCRIPT NINE
    # Subscripts
    "\u2080": "0",  # ₀ SUBSCRIPT ZERO
    "\u2081": "1",  # ₁ SUBSCRIPT ONE
    "\u2082": "2",  # ₂ SUBSCRIPT TWO
    "\u2083": "3",  # ₃ SUBSCRIPT THREE
    "\u2084": "4",  # ₄ SUBSCRIPT FOUR
    "\u2085": "5",  # ₅ SUBSCRIPT FIVE
    "\u2086": "6",  # ₆ SUBSCRIPT SIX
    "\u2087": "7",  # ₇ SUBSCRIPT SEVEN
    "\u2088": "8",  # ₈ SUBSCRIPT EIGHT
    "\u2089": "9",  # ₉ SUBSCRIPT NINE
    "\u208a": "+",  # ₊ SUBSCRIPT PLUS
    "\u208b": "-",  # ₋ SUBSCRIPT MINUS
    # Math operators
    "\u00d7": "x",  # × MULTIPLICATION SIGN
    "\u2212": "-",  # − MINUS SIGN
    "\u2264": "<=",  # ≤ LESS-THAN OR EQUAL TO
    "\u2265": ">=",  # ≥ GREATER-THAN OR EQUAL TO
    # Dashes → hyphen for matching
    "\u2011": "-",  # ‑ NON-BREAKING HYPHEN
    "\u2013": "-",  # – EN DASH
    "\u2014": "-",  # — EM DASH
    # Spaces → regular space
    "\u202f": " ",  # NARROW NO-BREAK SPACE
    "\u00a0": " ",  # NO-BREAK SPACE
    "\u2009": " ",  # THIN SPACE
    "\u200a": " ",  # HAIR SPACE
}

# Build a regex pattern for all Unicode chars we want to normalize
_UNICODE_MAP_RE = re.compile("(" + "|".join(re.escape(ch) for ch in UNICODE_TO_ASCII) + ")")


def normalize_unicode_chars(text):
    """Map Unicode math symbols and special whitespace to ASCII equivalents.

    This handles the common case where LLMs render Unicode symbols as their
    ASCII lookalikes (e.g. × → x, ⁺ → +, ² → 2, ‑ → -, narrow no-break
    space → regular space, etc.).
    """
    return _UNICODE_MAP_RE.sub(lambda m: UNICODE_TO_ASCII[m.group(0)], text)


def normalize_whitespace(text):
    """Normalize whitespace for comparison: collapse multiple spaces/newlines into single space."""
    # Replace newlines and multiple spaces with single space
    return " ".join(text.split())


def normalize_latex_escapes(text):
    """Normalize LaTeX escape sequences for fuzzy comparison.

    Handles the common case where an LLM sees rendered LaTeX and generates
    SEARCH blocks using the unescaped characters (e.g. '%' instead of '\\%').
    This strips the backslash from LaTeX special-character escapes so that
    '\\%' matches '%', '\\$' matches '$', etc.
    """
    # LaTeX special chars that need escaping: % $ & # _ { }
    text = re.sub(r"\\([%$&#_{}])", r"\1", text)
    return text


def normalize_for_matching(text):
    """Full normalization pipeline for fuzzy matching.

    Applies in order:
    1. LaTeX escape normalization (\\% → %)
    2. Unicode character normalization (× → x, ⁺ → +, ² → 2, etc.)
    3. Unicode NFC normalization (composing/decomposing character equivalence)
    4. Whitespace normalization (collapse all whitespace to single space)
    """
    text = normalize_latex_escapes(text)
    text = normalize_unicode_chars(text)
    text = unicodedata.normalize("NFC", text)
    return normalize_whitespace(text)


def replace_ignoring_line_breaks(whole_lines, part_lines, replace_lines):
    """Try to match by ignoring line breaks in the SEARCH block.

    This handles the case where LLM splits long lines into multiple lines,
    but the actual file has them as a single line.
    Also handles partial line matching when SEARCH block only covers part of a long line.
    """
    # Normalize the SEARCH block (join all lines, collapse whitespace)
    # Use normalize_for_matching which handles both whitespace and LaTeX escapes
    part_text = " ".join(line.rstrip() for line in part_lines)
    part_normalized = normalize_for_matching(part_text)

    if not part_normalized:
        return None

    # Try to find matching region in the whole file
    for i in range(len(whole_lines)):
        whole_line = whole_lines[i].rstrip()
        whole_normalized = normalize_for_matching(whole_line)

        # Check if the SEARCH block is a substring of this line
        # (handles both prefix match and middle-of-line match)
        if part_normalized in whole_normalized:
            # Found a match! Find the position and replace
            match_pos = whole_normalized.find(part_normalized)
            # Get the original content before and after the matched region
            # Use normalized position to map back to original content
            # We do a best-effort reconstruction preserving the original line's
            # unmodified prefix and suffix
            before_match = whole_line[:match_pos] if match_pos > 0 else ""
            after_match = whole_line[match_pos + len(part_text) :]
            if replace_lines:
                last_replace = replace_lines[-1].rstrip()
                new_line = before_match + last_replace + after_match + "\n"
                result = whole_lines[:i] + replace_lines[:-1] + [new_line] + whole_lines[i + 1 :]
            else:
                result = whole_lines
            return "".join(result)

        # Also check if SEARCH block matches exactly (for short lines)
        chunk_text = " ".join(line.rstrip() for line in whole_lines[i : i + len(part_lines)])
        chunk_normalized = normalize_for_matching(chunk_text)

        if chunk_normalized == part_normalized:
            # Exact match found
            result = whole_lines[:i] + replace_lines + whole_lines[i + len(part_lines) :]
            return "".join(result)

    # Also try with broader chunk length scanning
    # (handles cases where line counts differ between SEARCH and file)
    for i in range(len(whole_lines)):
        for length in range(1, min(20, len(whole_lines) - i + 1)):
            chunk_lines = whole_lines[i : i + length]
            chunk_text = " ".join(line.rstrip() for line in chunk_lines)
            chunk_normalized = normalize_for_matching(chunk_text)

            if chunk_normalized == part_normalized:
                # Found a match! Replace with the REPLACE lines
                result = whole_lines[:i] + replace_lines + whole_lines[i + length :]
                return "".join(result)

    return None


def _find_suffix_in_line(original_line, prefix_norm):
    """Find the unmatched suffix of original_line after the normalized prefix.

    Walks through original_line character by character, consuming those that
    map to prefix_norm under our normalization pipeline.  Returns the
    remaining original characters (the suffix that was NOT part of the
    SEARCH block).
    """
    line = original_line.rstrip("\n")
    norm_pos = 0
    orig_pos = 0

    # Skip leading whitespace (normalization collapses it to a single space
    # that is already accounted for in prefix_norm from the join step).
    while orig_pos < len(line) and line[orig_pos] in (" ", "\t"):
        orig_pos += 1

    while norm_pos < len(prefix_norm) and orig_pos < len(line):
        ch = line[orig_pos]

        # Determine what this char (or char sequence) normalizes to
        consumed = 1
        if ch == "\\" and orig_pos + 1 < len(line) and line[orig_pos + 1] in "%$&#_{}":
            # LaTeX escape  \\% → %
            mapped = line[orig_pos + 1]
            consumed = 2
        elif ch in UNICODE_TO_ASCII:
            mapped = UNICODE_TO_ASCII[ch]
        elif ch in (" ", "\t"):
            mapped = " "
            # Collapse consecutive whitespace
            while orig_pos + consumed < len(line) and line[orig_pos + consumed] in (
                " ",
                "\t",
            ):
                consumed += 1
        else:
            mapped = ch

        # Advance through prefix_norm by matching mapped characters
        for c in mapped:
            if norm_pos < len(prefix_norm) and prefix_norm[norm_pos] == c:
                norm_pos += 1
            elif c == " " and norm_pos > 0 and prefix_norm[norm_pos - 1] == " ":
                pass  # extra space, skip
            else:
                # Mismatch – shouldn't happen if prefix was verified
                break

        orig_pos += consumed

    # Skip whitespace gap between matched content and suffix
    while orig_pos < len(line) and line[orig_pos] in (" ", "\t"):
        orig_pos += 1

    return line[orig_pos:]


def replace_prefix_match(whole_lines, part_lines, replace_lines):
    """Handle SEARCH block that is a prefix of actual file content.

    This handles the case where the LLM's SEARCH block ends mid-line
    (e.g. SEARCH ends with ``water.`` but the file line continues with
    ``water. First, the surface charge density ...``).

    The function scans multi-line chunks of the file, normalizes both
    the SEARCH and file chunk, and checks whether the normalized SEARCH
    is a *prefix* of the normalized chunk.  When found, it splices in
    the REPLACE lines while preserving the unmatched suffix of the last
    file line.
    """
    if not part_lines:
        return None

    part_text = " ".join(line.rstrip() for line in part_lines)
    part_norm = normalize_for_matching(part_text)

    if not part_norm or len(part_norm) < 10:
        # Too short – risk of false positives
        return None

    max_chunk = min(30, len(whole_lines))

    for start in range(len(whole_lines)):
        chunk_norm = ""

        for end in range(start, min(start + max_chunk, len(whole_lines))):
            line_norm = normalize_for_matching(whole_lines[end].rstrip())

            if chunk_norm and line_norm:
                chunk_norm += " " + line_norm
            elif line_norm:
                chunk_norm = line_norm
            # Skip empty normalized lines (blank lines in file)

            # Check if SEARCH is a prefix of this chunk
            if chunk_norm.startswith(part_norm):
                extra = chunk_norm[len(part_norm) :].strip()

                if not extra:
                    # Exact match – all lines fully consumed
                    result = whole_lines[:start] + replace_lines + whole_lines[end + 1 :]
                    return "".join(result)

                # Prefix match with extra content on whole_lines[end]
                # Compute how much of the SEARCH covers the last file line
                prior_norm = ""
                if start < end:
                    prior_text = " ".join(whole_lines[j].rstrip() for j in range(start, end))
                    prior_norm = normalize_for_matching(prior_text)

                # The part of the SEARCH that should match the last line
                if prior_norm and part_norm.startswith(prior_norm):
                    last_search_norm = part_norm[len(prior_norm) :].strip()
                else:
                    last_search_norm = part_norm

                last_line_norm = normalize_for_matching(whole_lines[end].rstrip())

                if not last_line_norm.startswith(last_search_norm):
                    # Can't determine split point – skip
                    break

                # Find the unmatched suffix on the last line
                suffix = _find_suffix_in_line(whole_lines[end], last_search_norm)

                # Build result: prior lines + replace + suffix + remaining
                result_lines = list(whole_lines[:start])
                if len(replace_lines) > 1:
                    result_lines.extend(replace_lines[:-1])
                last_replace = replace_lines[-1].rstrip()
                if suffix:
                    result_lines.append(last_replace + suffix + "\n")
                else:
                    result_lines.append(replace_lines[-1])
                result_lines.extend(whole_lines[end + 1 :])
                return "".join(result_lines)

            # If chunk is already longer and not a prefix match, move on
            if len(chunk_norm) >= len(part_norm) and not chunk_norm.startswith(part_norm):
                break

    return None


def perfect_replace(whole_lines, part_lines, replace_lines):
    part_tup = tuple(part_lines)
    part_len = len(part_lines)

    for i in range(len(whole_lines) - part_len + 1):
        whole_tup = tuple(whole_lines[i : i + part_len])
        if part_tup == whole_tup:
            res = whole_lines[:i] + replace_lines + whole_lines[i + part_len :]
            return "".join(res)


def replace_most_similar_chunk_with_tag(whole, part, replace):
    """Best efforts to find the `part` lines in `whole` and replace them with `replace`.

    Returns:
        Tuple of (new_content, fallback_tag).  new_content is None on failure.
    """

    whole, whole_lines = prep(whole)
    part, part_lines = prep(part)
    replace, replace_lines = prep(replace)

    res, tag = perfect_or_whitespace_with_tag(whole_lines, part_lines, replace_lines)
    if res:
        return res, tag

    # drop leading empty line, GPT sometimes adds them spuriously (issue #25)
    if len(part_lines) > 2 and not part_lines[0].strip():
        skip_blank_line_part_lines = part_lines[1:]
        res, tag = perfect_or_whitespace_with_tag(
            whole_lines, skip_blank_line_part_lines, replace_lines
        )
        if res:
            return res, tag

    # Try matching ignoring line breaks (LLM may split long lines)
    res = replace_ignoring_line_breaks(whole_lines, part_lines, replace_lines)
    if res:
        return res, FallbackTag.IGNORE_LINEBREAKS

    # Try prefix match (SEARCH block ends mid-line in the file)
    res = replace_prefix_match(whole_lines, part_lines, replace_lines)
    if res:
        return res, FallbackTag.PREFIX

    # Try to handle when it elides code with ...
    try:
        res = try_dotdotdots(whole, part, replace)
        if res:
            return res, FallbackTag.EDIT_DISTANCE
    except ValueError:
        pass

    # Try fuzzy matching
    res = replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines)
    if res:
        return res, FallbackTag.EDIT_DISTANCE

    return None, FallbackTag.EDIT_DISTANCE


def replace_most_similar_chunk(whole, part, replace):
    """Best efforts to find the `part` lines in `whole` and replace them with `replace`"""
    res, _tag = replace_most_similar_chunk_with_tag(whole, part, replace)
    return res


def try_dotdotdots(whole, part, replace):
    """
    See if the edit block has ... lines.
    If not, return none.

    If yes, try and do a perfect edit with the ... chunks.
    If there's a mismatch or otherwise imperfect edit, raise ValueError.

    If perfect edit succeeds, return the updated whole.
    """

    dots_re = re.compile(r"(^\s*\.\.\.\n)", re.MULTILINE | re.DOTALL)

    part_pieces = re.split(dots_re, part)
    replace_pieces = re.split(dots_re, replace)

    if len(part_pieces) != len(replace_pieces):
        raise ValueError("Unpaired ... in SEARCH/REPLACE block")

    if len(part_pieces) == 1:
        # no dots in this edit block, just return None
        return

    # Compare odd strings in part_pieces and replace_pieces
    all_dots_match = all(part_pieces[i] == replace_pieces[i] for i in range(1, len(part_pieces), 2))

    if not all_dots_match:
        raise ValueError("Unmatched ... in SEARCH/REPLACE block")

    part_pieces = [part_pieces[i] for i in range(0, len(part_pieces), 2)]
    replace_pieces = [replace_pieces[i] for i in range(0, len(replace_pieces), 2)]

    pairs = zip(part_pieces, replace_pieces)
    for part, replace in pairs:
        if not part and not replace:
            continue

        if not part and replace:
            if not whole.endswith("\n"):
                whole += "\n"
            whole += replace
            continue

        if whole.count(part) == 0:
            raise ValueError
        if whole.count(part) > 1:
            raise ValueError

        whole = whole.replace(part, replace, 1)

    return whole


def replace_part_with_missing_leading_whitespace(whole_lines, part_lines, replace_lines):
    # GPT often messes up leading whitespace.
    # It usually does it uniformly across the ORIG and UPD blocks.
    # Either omitting all leading whitespace, or including only some of it.

    # Outdent everything in part_lines and replace_lines by the max fixed amount possible
    leading = [len(p) - len(p.lstrip()) for p in part_lines if p.strip()] + [
        len(p) - len(p.lstrip()) for p in replace_lines if p.strip()
    ]

    if leading and min(leading):
        num_leading = min(leading)
        part_lines = [p[num_leading:] if p.strip() else p for p in part_lines]
        replace_lines = [p[num_leading:] if p.strip() else p for p in replace_lines]

    # can we find an exact match not including the leading whitespace
    num_part_lines = len(part_lines)

    for i in range(len(whole_lines) - num_part_lines + 1):
        add_leading = match_but_for_leading_whitespace(
            whole_lines[i : i + num_part_lines], part_lines
        )

        if add_leading is None:
            continue

        replace_lines = [add_leading + rline if rline.strip() else rline for rline in replace_lines]
        whole_lines = whole_lines[:i] + replace_lines + whole_lines[i + num_part_lines :]
        return "".join(whole_lines)

    return None


def match_but_for_leading_whitespace(whole_lines, part_lines):
    num = len(whole_lines)

    # does the non-whitespace all agree?
    if not all(whole_lines[i].lstrip() == part_lines[i].lstrip() for i in range(num)):
        return

    # are they all offset the same?
    add = set(
        whole_lines[i][: len(whole_lines[i]) - len(part_lines[i])]
        for i in range(num)
        if whole_lines[i].strip()
    )

    if len(add) != 1:
        return

    return add.pop()


def replace_closest_edit_distance(whole_lines, part, part_lines, replace_lines):
    similarity_thresh = 0.65  # 更宽松的匹配，适合LaTeX

    max_similarity = 0
    most_similar_chunk_start = -1
    most_similar_chunk_end = -1

    scale = 0.1
    min_len = math.floor(len(part_lines) * (1 - scale))
    max_len = math.ceil(len(part_lines) * (1 + scale))

    for length in range(min_len, max_len):
        for i in range(len(whole_lines) - length + 1):
            chunk = whole_lines[i : i + length]
            chunk = "".join(chunk)

            # Use normalized text for similarity comparison so that
            # Unicode differences (×↔x, ⁺↔+, ²↔2, etc.) don't penalize
            chunk_norm = normalize_for_matching(chunk)
            part_norm = normalize_for_matching(part)
            similarity = SequenceMatcher(None, chunk_norm, part_norm).ratio()

            if similarity > max_similarity and similarity:
                max_similarity = similarity
                most_similar_chunk_start = i
                most_similar_chunk_end = i + length

    if max_similarity < similarity_thresh:
        return

    modified_whole = (
        whole_lines[:most_similar_chunk_start]
        + replace_lines
        + whole_lines[most_similar_chunk_end:]
    )
    modified_whole = "".join(modified_whole)

    return modified_whole


DEFAULT_FENCE = ("`" * 3, "`" * 3)


def strip_quoted_wrapping(res, fname=None, fence=DEFAULT_FENCE):
    """
    Given an input string which may have extra "wrapping" around it, remove the wrapping.
    For example:

    filename.ext
    ```
    We just want this content
    Not the filename and triple quotes
    ```
    """
    if not res:
        return res

    res = res.splitlines()

    if fname and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res[0].startswith(fence[0]) and res[-1].startswith(fence[1]):
        res = res[1:-1]

    res = "\n".join(res)
    if res and res[-1] != "\n":
        res += "\n"

    return res


def do_replace_with_tag(fname, content, before_text, after_text, fence=None):
    if fence is None:
        fence = DEFAULT_FENCE
    before_text = strip_quoted_wrapping(before_text, fname, fence)
    after_text = strip_quoted_wrapping(after_text, fname, fence)
    fname = Path(fname)

    # does it want to make a new file?
    if not fname.exists() and not before_text.strip():
        fname.touch()
        content = ""

    if content is None:
        return None, None

    if not before_text.strip():
        # append to existing file, or start a new file
        new_content = content + after_text
        tag = FallbackTag.PERFECT
    else:
        new_content, tag = replace_most_similar_chunk_with_tag(content, before_text, after_text)

    return new_content, tag


def do_replace(fname, content, before_text, after_text, fence=None):
    new_content, _tag = do_replace_with_tag(fname, content, before_text, after_text, fence)
    return new_content


HEAD = r"^<{5,9} SEARCH>?\s*$"
DIVIDER = r"^={5,9}\s*$"
UPDATED = r"^>{5,9} REPLACE\s*$"

HEAD_ERR = "<<<<<<< SEARCH"
DIVIDER_ERR = "======="
UPDATED_ERR = ">>>>>>> REPLACE"

# Anchor-based replace patterns
ANCHOR_HEAD = r"^<{5,9}\s*ANCHOR:\s*(.+)$"
ANCHOR_REPLACE = r"^>{5,9}\s*REPLACE\s*$"
ANCHOR_TAIL = r"^<{5,9}\s*ANCHOR:\s*(.+)$"
ANCHOR_END = r"^>{5,9}\s*END\s*$"

ANCHOR_HEAD_ERR = "<<<<<<< ANCHOR: ..."
ANCHOR_REPLACE_ERR = ">>>>>>> REPLACE"
ANCHOR_TAIL_ERR = "<<<<<<< ANCHOR: ..."
ANCHOR_END_ERR = ">>>>>>> END"

separators = "|".join(
    [HEAD, DIVIDER, UPDATED, ANCHOR_HEAD, ANCHOR_REPLACE, ANCHOR_TAIL, ANCHOR_END]
)

split_re = re.compile(r"^((?:" + separators + r")[ ]*\n)", re.MULTILINE | re.DOTALL)


missing_filename_err = (
    "Bad/missing filename. The filename must be alone on the line before the opening fence"
    " {fence[0]}"
)

# Always be willing to treat triple-backticks as a fence when searching for filenames
triple_backticks = "`" * 3


def strip_filename(filename, fence):
    filename = filename.strip()

    if filename == "...":
        return

    start_fence = fence[0]
    if filename.startswith(start_fence):
        candidate = filename[len(start_fence) :]
        if candidate and ("." in candidate or "/" in candidate):
            return candidate
        return

    if filename.startswith(triple_backticks):
        candidate = filename[len(triple_backticks) :]
        if candidate and ("." in candidate or "/" in candidate):
            return candidate
        return

    filename = filename.rstrip(":")
    filename = filename.lstrip("#")
    filename = filename.strip()
    filename = filename.strip("`")
    filename = filename.strip("*")

    # https://github.com/your-username/lsr/issues/1158
    # filename = filename.replace("\\_", "_")

    return filename


def find_original_update_blocks(content, fence=DEFAULT_FENCE, valid_fnames=None):
    lines = content.splitlines(keepends=True)
    i = 0
    current_filename = None

    head_pattern = re.compile(HEAD)
    divider_pattern = re.compile(DIVIDER)
    updated_pattern = re.compile(UPDATED)
    anchor_head_pattern = re.compile(ANCHOR_HEAD)
    anchor_replace_pattern = re.compile(ANCHOR_REPLACE)
    anchor_tail_pattern = re.compile(ANCHOR_TAIL)
    anchor_end_pattern = re.compile(ANCHOR_END)

    while i < len(lines):
        line = lines[i]

        # Check for shell code blocks
        shell_starts = [
            "```bash",
            "```sh",
            "```shell",
            "```cmd",
            "```batch",
            "```powershell",
            "```ps1",
            "```zsh",
            "```fish",
            "```ksh",
            "```csh",
            "```tcsh",
        ]

        # Check if the next line or the one after that is an editblock
        next_is_editblock = (
            i + 1 < len(lines)
            and head_pattern.match(lines[i + 1].strip())
            or i + 2 < len(lines)
            and head_pattern.match(lines[i + 2].strip())
        )

        # Also check for anchor blocks
        next_is_anchor = (
            i + 1 < len(lines)
            and anchor_head_pattern.match(lines[i + 1].strip())
            or i + 2 < len(lines)
            and anchor_head_pattern.match(lines[i + 2].strip())
        )

        if (
            any(line.strip().startswith(start) for start in shell_starts)
            and not next_is_editblock
            and not next_is_anchor
        ):
            shell_content = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                shell_content.append(lines[i])
                i += 1
            if i < len(lines) and lines[i].strip().startswith("```"):
                i += 1  # Skip the closing ```

            yield None, "".join(shell_content)
            continue

        # Check for ANCHOR/REPLACE blocks
        anchor_head_match = anchor_head_pattern.match(line.strip())
        if anchor_head_match:
            try:
                head_anchor = anchor_head_match.group(1).strip()
                filename = find_filename(lines[max(0, i - 3) : i], fence, valid_fnames)

                if not filename:
                    if current_filename:
                        filename = current_filename
                    else:
                        raise ValueError(missing_filename_err.format(fence=fence))

                current_filename = filename

                # Expect REPLACE marker
                i += 1
                if i >= len(lines) or not anchor_replace_pattern.match(lines[i].strip()):
                    raise ValueError(f"Expected `{ANCHOR_REPLACE_ERR}`")

                # Collect replacement content
                updated_text = []
                i += 1
                while i < len(lines) and not anchor_tail_pattern.match(lines[i].strip()):
                    updated_text.append(lines[i])
                    i += 1

                # Expect tail anchor
                if i >= len(lines) or not anchor_tail_pattern.match(lines[i].strip()):
                    raise ValueError(f"Expected `{ANCHOR_TAIL_ERR}`")

                tail_anchor = anchor_tail_pattern.match(lines[i].strip()).group(1).strip()

                # Expect END marker
                i += 1
                if i >= len(lines) or not anchor_end_pattern.match(lines[i].strip()):
                    raise ValueError(f"Expected `{ANCHOR_END_ERR}`")

                # Yield anchor-based edit with special format:
                # (filename, 'ANCHOR', head_anchor, tail_anchor, updated_text)
                yield (
                    filename,
                    "ANCHOR",
                    head_anchor,
                    tail_anchor,
                    "".join(updated_text),
                )

            except ValueError as e:
                processed = "".join(lines[: i + 1])
                err = e.args[0]
                raise ValueError(f"{processed}\n^^^ {err}")

        # Check for SEARCH/REPLACE blocks
        if head_pattern.match(line.strip()):
            try:
                # if next line after HEAD exists and is DIVIDER, it's a new file
                if i + 1 < len(lines) and divider_pattern.match(lines[i + 1].strip()):
                    filename = find_filename(lines[max(0, i - 3) : i], fence, None)
                else:
                    filename = find_filename(lines[max(0, i - 3) : i], fence, valid_fnames)

                if not filename:
                    if current_filename:
                        filename = current_filename
                    else:
                        raise ValueError(missing_filename_err.format(fence=fence))

                current_filename = filename

                original_text = []
                i += 1
                while i < len(lines) and not divider_pattern.match(lines[i].strip()):
                    original_text.append(lines[i])
                    i += 1

                if i >= len(lines) or not divider_pattern.match(lines[i].strip()):
                    raise ValueError(f"Expected `{DIVIDER_ERR}`")

                updated_text = []
                i += 1
                while i < len(lines) and not (
                    updated_pattern.match(lines[i].strip())
                    or divider_pattern.match(lines[i].strip())
                ):
                    updated_text.append(lines[i])
                    i += 1

                if i >= len(lines) or not (
                    updated_pattern.match(lines[i].strip())
                    or divider_pattern.match(lines[i].strip())
                ):
                    raise ValueError(f"Expected `{UPDATED_ERR}` or `{DIVIDER_ERR}`")

                yield filename, "".join(original_text), "".join(updated_text)

            except ValueError as e:
                processed = "".join(lines[: i + 1])
                err = e.args[0]
                raise ValueError(f"{processed}\n^^^ {err}")

        i += 1


def find_filename(lines, fence, valid_fnames):
    """
    Deepseek Coder v2 has been doing this:


     ```python
    word_count.py
    ```
    ```python
    <<<<<<< SEARCH
    ...

    This is a more flexible search back for filenames.
    """

    if valid_fnames is None:
        valid_fnames = []

    # Go back through the 3 preceding lines
    lines.reverse()
    lines = lines[:3]

    filenames = []
    for line in lines:
        # If we find a filename, done
        filename = strip_filename(line, fence)
        if filename:
            filenames.append(filename)

        # Only continue as long as we keep seeing fences
        if not line.startswith(fence[0]) and not line.startswith(triple_backticks):
            break

    if not filenames:
        return

    # pick the *best* filename found

    # Check for exact match first
    for fname in filenames:
        if fname in valid_fnames:
            return fname

    # Check for partial match (basename match)
    for fname in filenames:
        for vfn in valid_fnames:
            if fname == Path(vfn).name:
                return vfn

    # Perform fuzzy matching with valid_fnames
    for fname in filenames:
        close_matches = difflib.get_close_matches(fname, valid_fnames, n=1, cutoff=0.8)
        if len(close_matches) == 1:
            return close_matches[0]

    # If no fuzzy match, look for a file w/extension
    for fname in filenames:
        if "." in fname:
            return fname

    if filenames:
        return filenames[0]


def find_similar_lines(search_lines, content_lines, threshold=0.6):
    search_lines = search_lines.splitlines()
    content_lines = content_lines.splitlines()

    best_ratio = 0
    best_match = None

    for i in range(len(content_lines) - len(search_lines) + 1):
        chunk = content_lines[i : i + len(search_lines)]
        # Use normalized comparison for Unicode/LaTeX robustness
        chunk_norm = [normalize_for_matching(line) for line in chunk]
        search_norm = [normalize_for_matching(line) for line in search_lines]
        ratio = SequenceMatcher(None, search_norm, chunk_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = chunk
            best_match_i = i

    if best_ratio < threshold:
        return ""

    if best_match[0] == search_lines[0] and best_match[-1] == search_lines[-1]:
        return "\n".join(best_match)

    N = 5
    best_match_end = min(len(content_lines), best_match_i + len(search_lines) + N)
    best_match_i = max(0, best_match_i - N)

    best = content_lines[best_match_i:best_match_end]
    return "\n".join(best)


def main():
    history_md = Path(sys.argv[1]).read_text()
    if not history_md:
        return

    messages = utils.split_chat_history_markdown(history_md)

    for msg in messages:
        msg = msg["content"]
        edits = list(find_original_update_blocks(msg))

        for fname, before, after in edits:
            # Compute diff
            diff = difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
            )
            diff = "".join(diff)
            dump(before)
            dump(after)
            dump(diff)


if __name__ == "__main__":
    main()
