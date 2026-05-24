"""
Anchor-based Replace Strategy for LaTeX Writing

Instead of requiring the full SEARCH block, this strategy uses:
1. First sentence as HEAD anchor
2. Last sentence as TAIL anchor
3. Only the new content in REPLACE

Benefits:
- LLM doesn't need to regenerate entire paragraphs
- Matching is more forgiving (only needs to match anchors)
- Token efficient for large sections
"""

import re
from difflib import SequenceMatcher


def similarity(a, b):
    """Simple similarity score between two strings."""
    return SequenceMatcher(None, a, b).ratio()


def find_anchor_match(content, head_anchor, tail_anchor):
    """Find the region between head and tail anchors in content."""
    # Find head anchor position
    head_pos = content.find(head_anchor)
    if head_pos == -1:
        # Try fuzzy match - find most similar line
        lines = content.split("\n")
        best_match = None
        best_score = 0
        for i, line in enumerate(lines):
            score = similarity(head_anchor, line)
            if score > best_score:
                best_score = score
                best_match = (i, line)
        if best_match and best_score > 0.6:
            head_pos = content.find(best_match[1])
        else:
            return None, None

    # Find tail anchor position (after head)
    tail_pos = content.find(tail_anchor, head_pos + len(head_anchor))
    if tail_pos == -1:
        # Try fuzzy match
        lines = content.split("\n")
        best_match = None
        best_score = 0
        for i, line in enumerate(lines):
            if i <= content[:head_pos].count("\n"):
                continue
            score = similarity(tail_anchor, line)
            if score > best_score:
                best_score = score
                best_match = (i, line)
        if best_match and best_score > 0.6:
            tail_pos = content.find(best_match[1], head_pos + len(head_anchor))
        else:
            return None, None

    # tail_pos points to the start of tail_anchor
    # We want to replace including the tail_anchor
    return head_pos, tail_pos + len(tail_anchor)


def anchor_replace(content, head_anchor, tail_anchor, new_content):
    """
    Replace content between anchors.

    Args:
        content: Original file content
        head_anchor: First sentence/line to match
        tail_anchor: Last sentence/line to match
        new_content: Replacement content

    Returns:
        New content if successful, None if anchors not found
    """
    start, end = find_anchor_match(content, head_anchor, tail_anchor)
    if start is None or end is None:
        return None
    return content[:start] + new_content + content[end:]


def parse_anchor_blocks(text):
    """
    Parse ANCHOR/REPLACE blocks from LLM output.

    Expected format:
    <<<<<<< ANCHOR: first sentence or line
    >>>>>>> REPLACE
    new content here
    <<<<<<< ANCHOR: last sentence or line
    >>>>>>> END
    """
    blocks = []
    pattern = re.compile(
        r"<<<<<<<\s*ANCHOR:\s*(.*?)\n"
        r">>>>>>>\s*REPLACE\n"
        r"(.*?)"
        r"<<<<<<<\s*ANCHOR:\s*(.*?)\n"
        r">>>>>>>\s*END",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        head_anchor = match.group(1).strip()
        new_content = match.group(2).strip()
        tail_anchor = match.group(3).strip()
        blocks.append(
            {"head": head_anchor, "tail": tail_anchor, "replacement": new_content}
        )
    return blocks


def apply_anchor_edits(file_path, edits):
    """
    Apply anchor-based edits to a file.

    Args:
        file_path: Path to the file
        edits: List of {head, tail, replacement} dicts

    Returns:
        Tuple of (success, new_content, error_message)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, None, str(e)

    applied = 0
    for edit in edits:
        new_content = anchor_replace(
            content, edit["head"], edit["tail"], edit["replacement"]
        )
        if new_content:
            content = new_content
            applied += 1

    if applied == 0:
        return False, None, "No edits could be applied"
    return True, content, None


# Example usage for prompt generation
ANCHOR_REPLACE_PROMPT = """
When editing LaTeX sections, use ANCHOR/REPLACE blocks instead of SEARCH/REPLACE blocks.

Format:
<<<<<<< ANCHOR: [first sentence or line of the paragraph/section to replace]
>>>>>>> REPLACE
[entire new content to replace the section]
<<<<<<< ANCHOR: [last sentence or line of the paragraph/section to replace]
>>>>>>> END

Example:
<<<<<<< ANCHOR: Wavefunction analysis based on density functional theory
>>>>>>> REPLACE
Molecular dynamics simulations were performed to investigate the liquid-phase structure.
The simulation box contained 500 pairs of choline chloride and hydrogen bond donor molecules.
<<<<<<< ANCHOR: provides a theoretical basis for the rational design
>>>>>>> END

Benefits:
1. You only need to provide the first and last sentences of the region to replace
2. The matching is more forgiving - small differences won't cause failures
3. You don't need to regenerate entire paragraphs
4. Token efficient for large sections

Rules:
1. The ANCHOR text must be an exact match of the first/last sentence in the file
2. Each ANCHOR/REPLACE block replaces exactly one paragraph or section
3. For multiple paragraphs, use multiple blocks
4. Keep anchors short but unique (first/last sentence is usually enough)
"""
