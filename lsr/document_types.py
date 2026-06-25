"""Document type registry for LaTeX, Typst, and Markdown manuscripts."""

import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LspServerConfig:
    """Configuration for an LSP server used by a document type."""

    command: str
    args: tuple[str, ...] = ()
    initialization_options: Optional[dict] = None


@dataclass(frozen=True)
class DocumentType:
    """Format-specific behavior for a manuscript type."""

    name: str
    extensions: frozenset[str]
    important_files: tuple[str, ...]
    section_pattern: re.Pattern
    comment_start: str
    comment_end: str
    compiler: Optional[str]
    lsp_server: Optional[LspServerConfig]

    def matches(self, path: str) -> bool:
        """Return True if the given path matches this document type."""
        return os.path.splitext(path)[1].lower() in self.extensions

    def parse_sections(self, content: str) -> list[tuple[str, str, int, int, str]]:
        """Parse section structure.

        Returns a list of (level_name, title, start_line, end_line, section_content)
        tuples. level_name is normalized to "section", "subsection", or
        "subsubsection" regardless of the source syntax.
        """
        lines = content.split("\n")
        markers = []
        for i, line in enumerate(lines):
            m = self.section_pattern.search(line)
            if m:
                markers.append((i, m.group(1), m.group(2)))

        items = []
        for idx, (start_line, level_marker, title) in enumerate(markers):
            if idx + 1 < len(markers):
                end_line = markers[idx + 1][0] - 1
            else:
                end_line = len(lines) - 1

            while end_line > start_line and not lines[end_line].strip():
                end_line -= 1

            section_content = "\n".join(lines[start_line : end_line + 1])
            level_name = self._normalize_level(level_marker)
            items.append((level_name, title, start_line, end_line, section_content))

        return items

    def _normalize_level(self, level_marker: str) -> str:
        """Map a native heading marker to a normalized level name."""
        mapping = _LEVEL_NORMALIZERS.get(self.name, {})
        return mapping.get(level_marker, "section")

    def make_hash_marker(self, sec_type: str, title: str, hash_digest: str) -> str:
        """Build a format-appropriate hash marker comment."""
        body = f"=== {sec_type}: {title} (hash: {hash_digest}) ==="
        if self.comment_end:
            return f"{self.comment_start} {body} {self.comment_end}"
        return f"{self.comment_start} {body}"

    @property
    def hash_marker_pattern(self) -> re.Pattern:
        """Regex matching a hash marker comment and capturing title and hash."""
        start = re.escape(self.comment_start)
        end = re.escape(self.comment_end) if self.comment_end else ""
        if end:
            return re.compile(
                rf"{start}\s+===\s+(?:.*?):\s+(.*?)\s+\(hash:\s+(\w+)\)\s+===\s+{end}"
            )
        return re.compile(rf"{start}\s+===\s+(?:.*?):\s+(.*?)\s+\(hash:\s+(\w+)\)\s+===")

    def format_heading(self, level_name: str, title: str) -> str:
        """Build a native heading line for this document type."""
        mapping = _HEADING_FORMATS.get(self.name, {})
        template = mapping.get(level_name)
        if template is None:
            # Fallback for unknown levels.
            if self.name == "latex":
                template = "\\{level_name}{{{title}}}"
            elif self.name == "markdown":
                template = "# {title}"
            else:
                template = "= {title}"
        return template.format(level_name=level_name, title=title)

    def format_todo_comment(self, level_name: str) -> str:
        """Build a format-appropriate TODO placeholder comment."""
        body = f"TODO: Write {level_name} content here"
        if self.comment_end:
            return f"{self.comment_start} {body} {self.comment_end}"
        return f"{self.comment_start} {body}"

    def format_display_heading(self, level_name: str, title: str) -> str:
        """Build a human-readable heading representation for menus."""
        if self.name == "latex":
            return f"\\{level_name}{{{title}}}"
        return self.format_heading(level_name, title)


# Mapping of document-type names to level normalizers.
# Keys are the native markers captured by section_pattern; values are normalized names.
_LEVEL_NORMALIZERS = {
    "latex": {
        "section": "section",
        "subsection": "subsection",
        "subsubsection": "subsubsection",
    },
    "markdown": {
        "#": "section",
        "##": "subsection",
        "###": "subsubsection",
    },
    "typst": {
        "=": "section",
        "==": "subsection",
        "===": "subsubsection",
    },
}

# Mapping of document-type names to heading format templates.
# {level_name} and {title} are substituted.
_HEADING_FORMATS = {
    "latex": {
        "section": "\\section{{{title}}}",
        "subsection": "\\subsection{{{title}}}",
        "subsubsection": "\\subsubsection{{{title}}}",
    },
    "markdown": {
        "section": "# {title}",
        "subsection": "## {title}",
        "subsubsection": "### {title}",
    },
    "typst": {
        "section": "= {title}",
        "subsection": "== {title}",
        "subsubsection": "=== {title}",
    },
}


LATEX = DocumentType(
    name="latex",
    extensions=frozenset({".tex", ".bib", ".sty", ".cls", ".dtx", ".ins"}),
    important_files=(
        "main.tex",
        "paper.tex",
        "thesis.tex",
        "document.tex",
        "main.bib",
        "references.bib",
    ),
    section_pattern=re.compile(r"\\(section|subsection|subsubsection)\{([^}]+)\}"),
    comment_start="%",
    comment_end="",
    compiler="pdflatex",
    lsp_server=LspServerConfig(command="texlab"),
)


MARKDOWN = DocumentType(
    name="markdown",
    extensions=frozenset({".md"}),
    important_files=("main.md", "index.md", "README.md"),
    section_pattern=re.compile(r"^(#{1,3})\s+(.+)$"),
    comment_start="<!--",
    comment_end="-->",
    compiler=None,
    lsp_server=LspServerConfig(command="marksman"),
)


TYPST = DocumentType(
    name="typst",
    extensions=frozenset({".typ"}),
    important_files=("main.typ", "paper.typ", "thesis.typ", "document.typ"),
    section_pattern=re.compile(r"^(={1,3})\s+(.+)$"),
    comment_start="//",
    comment_end="",
    compiler="typst",
    lsp_server=LspServerConfig(command="tinymist"),
)


_DOCUMENT_TYPES: tuple[DocumentType, ...] = (LATEX, MARKDOWN, TYPST)


def get_document_type(path: str) -> Optional[DocumentType]:
    """Return the DocumentType for a path, or None if unknown."""
    ext = os.path.splitext(path)[1].lower()
    for doc_type in _DOCUMENT_TYPES:
        if ext in doc_type.extensions:
            return doc_type
    return None


def find_main_document(root: str, doc_type: DocumentType) -> Optional[str]:
    """Find the main document of a given type in a project root."""
    for candidate in doc_type.important_files:
        path = os.path.join(root, candidate)
        if os.path.exists(path):
            return path

    # Fall back to the first matching file in the root directory.
    for ext in sorted(doc_type.extensions):
        for file_path in sorted(os.listdir(root)):
            if file_path.lower().endswith(ext):
                return os.path.join(root, file_path)

    return None
