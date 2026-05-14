import re
from pathlib import Path

from .base_coder import Coder, compute_line_hash
from .hashline_prompts import HashLinePrompts


class HashLineCoder(Coder):
    """A coder that uses hash-based line references for code modifications."""

    edit_format = "hashline"
    gpt_prompts = HashLinePrompts()

    def get_edits(self, mode="update"):
        content = self.partial_response_content

        edits = list(
            find_hashline_blocks(
                content,
                self.get_inchat_relative_files(),
            )
        )

        # Extract shell commands (blocks with no filename)
        self.shell_commands += [edit[1] for edit in edits if edit[0] is None]
        edits = [edit for edit in edits if edit[0] is not None]

        return edits

    def prepare_to_edit(self, edits):
        """Override to handle CREATE operations without user confirmation."""
        res = []
        seen = {}

        self.need_commit_before_edits = set()

        for edit in edits:
            path = edit[0]
            if path is None:
                res.append(edit)
                continue

            op = edit[3] if len(edit) > 3 else "REPLACE"

            # For CREATE operations, skip the confirmation dialog
            if op == "CREATE":
                res.append(edit)
                continue

            if path in seen:
                allowed = seen[path]
            else:
                allowed = self.allowed_to_edit(path)
                seen[path] = allowed

            if allowed:
                res.append(edit)

        self.dirty_commit()
        self.need_commit_before_edits = set()

        return res

    def apply_edits_dry_run(self, edits):
        return self.apply_edits(edits, dry_run=True)

    def apply_edits(self, edits, dry_run=False):
        if not edits:
            return []

        # Group edits by file
        edits_by_file = {}
        for edit in edits:
            path = edit[0]
            if path not in edits_by_file:
                edits_by_file[path] = []
            edits_by_file[path].append(edit)

        failed = []
        passed = []
        updated_edits = []

        for path, file_edits in edits_by_file.items():
            full_path = self.abs_root_path(path)

            # Separate CREATE edits from other edits
            create_edits = [
                e for e in file_edits if (e[3] if len(e) > 3 else "REPLACE") == "CREATE"
            ]
            non_create_edits = [
                e for e in file_edits if (e[3] if len(e) > 3 else "REPLACE") != "CREATE"
            ]

            # Process CREATE edits first
            for edit in create_edits:
                if Path(full_path).exists():
                    error_msg = f"Cannot CREATE {path}: file already exists"
                    failed.append((edit, error_msg))
                else:
                    new_content = edit[2]
                    if not dry_run:
                        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
                        self.io.write_text(full_path, new_content)
                    passed.append(edit)
                    updated_edits.append(edit)

            # If no non-CREATE edits, continue to next file
            if not non_create_edits:
                continue

            # For non-CREATE edits, read the file content
            if not Path(full_path).exists():
                for edit in non_create_edits:
                    error_msg = f"File not found: {path}"
                    failed.append((edit, error_msg))
                continue

            content = self.io.read_text(full_path)
            if content is None:
                for edit in non_create_edits:
                    error_msg = f"Could not read file: {path}"
                    failed.append((edit, error_msg))
                continue

            # Build hash -> line_number mapping from original content
            hash_map = build_hash_map(content)

            # Sort edits by start line number (descending) to apply from bottom to top
            sorted_edits = []
            for edit in non_create_edits:
                start_hash, end_hash = edit[1]  # (start_hash, end_hash) tuple
                op = edit[3] if len(edit) > 3 else "REPLACE"

                # For INSERT, we only need the target hash (end_hash == start_hash)
                start_line = hash_map.get(start_hash)
                end_line = hash_map.get(end_hash)

                if start_line is None:
                    error_msg = (
                        f"Hash {start_hash} not found in {path}. "
                        "The hash must be copied exactly from the file content."
                    )
                    failed.append((edit, error_msg))
                    continue

                if end_line is None:
                    error_msg = (
                        f"Hash {end_hash} not found in {path}. "
                        "The hash must be copied exactly from the file content."
                    )
                    failed.append((edit, error_msg))
                    continue

                if op != "INSERT" and start_line > end_line:
                    error_msg = (
                        f"Invalid hash range in {path}: start hash {start_hash} "
                        f"(line {start_line}) comes after end hash {end_hash} "
                        f"(line {end_line})."
                    )
                    failed.append((edit, error_msg))
                    continue

                sorted_edits.append((start_line, end_line, edit))

            # Sort by start line descending
            sorted_edits.sort(key=lambda x: x[0], reverse=True)

            # Apply edits from bottom to top
            lines = content.splitlines(keepends=True)
            for start_line, end_line, edit in sorted_edits:
                op = edit[3] if len(edit) > 3 else "REPLACE"
                new_content = edit[2]

                # Convert to 0-indexed
                start_idx = start_line - 1
                end_idx = end_line  # end_line is inclusive, so end_idx is exclusive

                if op == "REPLACE":
                    # Replace lines from start to end with new content
                    new_lines = new_content.splitlines(keepends=True)
                    if new_lines and not new_lines[-1].endswith("\n"):
                        new_lines[-1] += "\n"
                    lines[start_idx:end_idx] = new_lines
                elif op == "INSERT":
                    # Insert after the target line (end_line)
                    insert_idx = end_idx  # Insert after the line
                    new_lines = new_content.splitlines(keepends=True)
                    if new_lines and not new_lines[-1].endswith("\n"):
                        new_lines[-1] += "\n"
                    lines[insert_idx:insert_idx] = new_lines

                passed.append(edit)
                updated_edits.append(edit)

            # Write the modified content
            if not dry_run:
                new_content = "".join(lines)
                self.io.write_text(full_path, new_content)

        if dry_run:
            return updated_edits

        if not failed:
            return updated_edits

        # Build error message
        blocks = "edit" if len(failed) == 1 else "edits"
        res = f"# {len(failed)} HASHLINE {blocks} failed!\n\n"

        for edit, error_msg in failed:
            path = edit[0]
            start_hash, end_hash = edit[1]
            op = edit[3] if len(edit) > 3 else "REPLACE"

            if op == "CREATE":
                res += f"## CREATE failed for {path}\n{error_msg}\n\n"
            else:
                res += f"## HASH mismatch in {path}\n"
                res += f"Error: {error_msg}\n\n"

                # Try to suggest correct hashes
                full_path = self.abs_root_path(path)
                if Path(full_path).exists():
                    content = self.io.read_text(full_path)
                    if content:
                        suggestion = find_similar_hash(start_hash, content)
                        if suggestion:
                            res += f"Did you mean hash {suggestion}?\n\n"

        if passed:
            pblocks = "edit" if len(passed) == 1 else "edits"
            res += (
                f"\nThe other {len(passed)} HASHLINE {pblocks} were applied successfully.\n"
                "Don't re-send them.\n"
                "Just reply with fixed versions of the edits above.\n"
            )

        raise ValueError(res)


def build_hash_map(content):
    """Build a mapping from hash to line number (1-indexed)."""
    hash_map = {}
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        line_num = i + 1
        line_content = line.rstrip("\n").rstrip("\r\n")
        h = compute_line_hash(line_num, line_content)
        hash_map[h] = line_num
    return hash_map


def find_similar_hash(target_hash, content):
    """Try to find a hash that's similar to the target (for error suggestions)."""
    hash_map = build_hash_map(content)

    # Check if any hash starts with the same prefix
    prefix = target_hash[:3]
    candidates = [h for h in hash_map if h.startswith(prefix)]

    if candidates:
        return candidates[0]

    return None


# Regex patterns for parsing hashline blocks
HASH_RANGE_RE = re.compile(r"^<<<<<<?<?\s+HASH\s+([0-9a-f]{6})\.\.([0-9a-f]{6})\s*$")
HASH_SINGLE_RE = re.compile(r"^<<<<<<?<?\s+HASH\s+([0-9a-f]{6})\s*$")
CREATE_RE = re.compile(r"^<<<<<<?<?\s+CREATE\s*$")
END_REPLACE_RE = re.compile(r"^>{5,9}\s+REPLACE\s*$")
END_INSERT_RE = re.compile(r"^>{5,9}\s+INSERT\s*$")
END_CREATE_RE = re.compile(r"^>{5,9}\s+END\s*$")


def find_hashline_blocks(content, valid_fnames=None):
    """Parse hashline edit blocks from LLM response content.

    Yields tuples of:
    - (filename, (start_hash, end_hash), new_content, "REPLACE") for REPLACE blocks
    - (filename, (hash, hash), new_content, "INSERT") for INSERT blocks
    - (filename, None, new_content, "CREATE") for CREATE blocks
    - (None, shell_content) for shell command blocks
    """
    if valid_fnames is None:
        valid_fnames = []

    lines = content.splitlines(keepends=True)
    i = 0
    current_filename = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

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

        if any(stripped.startswith(start) for start in shell_starts):
            # Check if next line is a hashline block
            next_is_hashline = (
                i + 1 < len(lines) and lines[i + 1].strip().startswith("<<<<<")
            ) or (i + 2 < len(lines) and lines[i + 2].strip().startswith("<<<<<"))
            if not next_is_hashline:
                shell_content = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    shell_content.append(lines[i])
                    i += 1
                if i < len(lines) and lines[i].strip().startswith("```"):
                    i += 1
                yield None, "".join(shell_content)
                continue

        # Check for CREATE block
        create_match = CREATE_RE.match(stripped)
        if create_match:
            filename = find_filename_for_hashline(lines, i, valid_fnames)
            if not filename:
                if current_filename:
                    filename = current_filename
                else:
                    raise ValueError("Bad/missing filename before <<<<<<< CREATE")

            current_filename = filename

            # Collect content until >>>>>>> END
            i += 1
            new_content = []
            while i < len(lines):
                if END_CREATE_RE.match(lines[i].strip()):
                    i += 1
                    break
                new_content.append(lines[i])
                i += 1
            else:
                raise ValueError("Expected >>>>>>> END for CREATE block")

            yield filename, None, "".join(new_content), "CREATE"
            continue

        # Check for HASH range block (REPLACE or INSERT)
        hash_range_match = HASH_RANGE_RE.match(stripped)
        hash_single_match = HASH_SINGLE_RE.match(stripped)

        if hash_range_match or hash_single_match:
            filename = find_filename_for_hashline(lines, i, valid_fnames)
            if not filename:
                if current_filename:
                    filename = current_filename
                else:
                    raise ValueError("Bad/missing filename before <<<<<<< HASH")

            current_filename = filename

            if hash_range_match:
                start_hash = hash_range_match.group(1)
                end_hash = hash_range_match.group(2)
            else:
                # Single hash - could be INSERT or single-line REPLACE
                # We'll determine from the end marker
                start_hash = hash_single_match.group(1)
                end_hash = None  # Will be set based on end marker

            # Collect content until end marker
            i += 1
            new_content = []
            op = None
            while i < len(lines):
                end_line = lines[i].strip()
                if END_REPLACE_RE.match(end_line):
                    op = "REPLACE"
                    i += 1
                    break
                if END_INSERT_RE.match(end_line):
                    op = "INSERT"
                    i += 1
                    break
                new_content.append(lines[i])
                i += 1
            else:
                raise ValueError("Expected >>>>>>> REPLACE or >>>>>>> INSERT")

            # For single hash with REPLACE, use same hash for start and end
            if end_hash is None:
                if op == "INSERT":
                    end_hash = start_hash
                else:
                    # Single hash REPLACE = single line replace
                    end_hash = start_hash

            yield filename, (start_hash, end_hash), "".join(new_content), op
            continue

        i += 1


def find_filename_for_hashline(lines, current_idx, valid_fnames):
    """Look backwards from current position to find the filename."""
    # Go back up to 3 lines
    search_lines = lines[max(0, current_idx - 3) : current_idx]
    search_lines = list(reversed(search_lines))

    for line in search_lines:
        stripped = line.strip()

        # Skip fence lines
        if stripped.startswith("```"):
            continue

        # Strip common prefixes/suffixes
        filename = stripped
        filename = filename.rstrip(":")
        filename = filename.lstrip("#")
        filename = filename.strip()
        filename = filename.strip("`")
        filename = filename.strip("*")

        if not filename or len(filename) > 250:
            continue

        # Check if it's a valid filename
        if filename in valid_fnames:
            return filename

        # Check basename match
        for vfn in valid_fnames:
            if filename == Path(vfn).name:
                return vfn

        # If it has a file extension, treat it as filename
        if "." in filename or "/" in filename:
            return filename

    return None
