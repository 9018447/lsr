"""Hashline manager for persistent storage and display of line hashes."""

import hashlib
import json
import os
import tempfile
from pathlib import Path


def compute_line_hash(line_num, line_content):
    """Compute a 6-char hex hash from line content and 1-indexed position."""
    raw = f"{line_num}:{line_content}"
    return hashlib.sha256(raw.encode()).hexdigest()[:6]


class HashlineManager:
    """Manages persistent storage and display of line hashes for files."""

    def __init__(self, root_dir=None):
        self.root_dir = root_dir or os.getcwd()
        self.cache_dir = Path(self.root_dir) / ".aider" / "hashline_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, file_path):
        """Get cache file path for a given file."""
        # Use relative path to create unique cache filename
        rel_path = os.path.relpath(file_path, self.root_dir)
        # Replace path separators with underscores
        safe_name = rel_path.replace(os.sep, "_").replace("/", "_")
        return self.cache_dir / f"{safe_name}.json"

    def compute_hashes(self, file_path):
        """Compute hashes for all lines in a file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (IOError, OSError):
            return {}

        lines = content.splitlines(keepends=True)
        hashes = {}
        for i, line in enumerate(lines):
            line_num = i + 1
            line_content = line.rstrip("\n").rstrip("\r\n")
            h = compute_line_hash(line_num, line_content)
            hashes[line_num] = {
                "hash": h,
                "content": line_content,
                "full_line": line,
            }
        return hashes

    def _get_file_mtime(self, file_path):
        """Get file modification time."""
        try:
            return os.path.getmtime(file_path)
        except (IOError, OSError):
            return 0

    def save_hashes(self, file_path):
        """Compute and save hashes to cache."""
        hashes = self.compute_hashes(file_path)
        if not hashes:
            return {}

        cache_path = self._get_cache_path(file_path)
        cache_data = {
            "file_path": str(file_path),
            "mtime": self._get_file_mtime(file_path),
            "hashes": {
                str(k): v for k, v in hashes.items()
            },
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except (IOError, OSError):
            pass

        return hashes

    def load_hashes(self, file_path):
        """Load cached hashes for a file.
        
        Returns empty dict if cache is stale (file modified after cache creation).
        """
        cache_path = self._get_cache_path(file_path)
        if not cache_path.exists():
            return {}

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # Check if cache is stale
            cached_mtime = cache_data.get("mtime", 0)
            current_mtime = self._get_file_mtime(file_path)
            
            if current_mtime > cached_mtime:
                # File modified after cache was created, invalidate
                return {}
            
            return {
                int(k): v for k, v in cache_data.get("hashes", {}).items()
            }
        except (json.JSONDecodeError, IOError, OSError):
            return {}

    def get_hashes(self, file_path):
        """Get hashes for a file, computing if necessary."""
        hashes = self.load_hashes(file_path)
        if not hashes:
            hashes = self.save_hashes(file_path)
        return hashes

    def format_with_hashes(self, file_path, show_line_numbers=True):
        """Format file content with hash prefixes for display."""
        hashes = self.get_hashes(file_path)
        if not hashes:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except (IOError, OSError):
                return ""

        lines = []
        for line_num in sorted(hashes.keys()):
            h = hashes[line_num]
            hash_str = h["hash"]
            content = h["full_line"].rstrip("\n")
            if show_line_numbers:
                lines.append(f"{hash_str} | {line_num:4d} | {content}")
            else:
                lines.append(f"{hash_str} | {content}")

        return "\n".join(lines)

    def format_for_editor(self, file_path):
        """Format file content for editor display with hashline annotations."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                original_content = f.read()
        except (IOError, OSError):
            return ""

        hashes = self.compute_hashes(file_path)
        if not hashes:
            return original_content

        lines = original_content.splitlines(keepends=True)
        result = []
        
        # Add header comment
        result.append(f"# Hashline annotations for: {os.path.basename(file_path)}")
        result.append("# Format: HASH | LINE_NUMBER | CONTENT")
        result.append("# Use these hashes when requesting edits with aider")
        result.append("#" + "=" * 70)
        result.append("")
        
        for i, line in enumerate(lines):
            line_num = i + 1
            if line_num in hashes:
                h = hashes[line_num]
                hash_str = h["hash"]
                content = line.rstrip("\n")
                result.append(f"{hash_str} | {line_num:4d} | {content}")
            else:
                result.append(line.rstrip("\n"))

        return "\n".join(result)

    def get_hash_for_line(self, file_path, line_num):
        """Get hash for a specific line number."""
        hashes = self.get_hashes(file_path)
        return hashes.get(line_num, {}).get("hash")

    def find_line_by_hash(self, file_path, target_hash):
        """Find line number by hash value."""
        hashes = self.get_hashes(file_path)
        for line_num, h in hashes.items():
            if h["hash"] == target_hash:
                return line_num
        return None

    def invalidate_cache(self, file_path):
        """Remove cached hashes for a file."""
        cache_path = self._get_cache_path(file_path)
        try:
            if cache_path.exists():
                cache_path.unlink()
        except (IOError, OSError):
            pass

    def clear_all_cache(self):
        """Clear all cached hashes."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
        except (IOError, OSError):
            pass
