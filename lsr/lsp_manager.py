"""Manages LSP server processes per workspace and document type."""

import atexit
import logging
from typing import Optional

from lsr import utils
from lsr.document_types import MARKDOWN, TYPST, DocumentType, get_document_type
from lsr.lsp_client import (
    LspClient,
    LspError,
    LspServerNotFoundError,
    path_to_uri,
)

logger = logging.getLogger(__name__)


class LspManager:
    """Keeps one LSP client per (workspace_root, document_type)."""

    def __init__(
        self,
        workspace_root: str,
        enabled: bool = True,
        server_overrides: Optional[dict[str, str]] = None,
    ):
        self.workspace_root = workspace_root
        self.enabled = enabled
        self.server_overrides = server_overrides or {}
        self._clients: dict[str, LspClient] = {}
        self._unavailable: set[str] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop all managed LSP servers."""
        for client in list(self._clients.values()):
            try:
                client.stop()
            except Exception as exc:
                logger.debug("Error stopping LSP client: %s", exc)
        self._clients.clear()
        self._unavailable.clear()

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def get_symbols(self, abs_path: str) -> Optional[list[tuple[str, str, int, int, str]]]:
        """Return section-like symbols for a file, or None if LSP is unavailable.

        The returned tuples match the format used by DocumentType.parse_sections:
        (level_name, title, start_line, end_line, content).
        """
        if not self.enabled:
            return None

        doc_type = get_document_type(abs_path)
        if doc_type is None:
            return None

        client = self._get_client(doc_type)
        if client is None:
            return None

        uri = path_to_uri(abs_path)
        try:
            raw_symbols = client.document_symbols(uri)
        except LspError as exc:
            logger.debug("LSP documentSymbol failed for %s: %s", abs_path, exc)
            return None

        return self._symbols_to_sections(abs_path, raw_symbols, doc_type)

    def get_diagnostics(self, abs_path: str) -> list[dict]:
        """Return cached LSP diagnostics for a file."""
        if not self.enabled:
            return []

        doc_type = get_document_type(abs_path)
        if doc_type is None:
            return []

        client = self._get_client(doc_type)
        if client is None:
            return []

        return client.get_diagnostics(path_to_uri(abs_path))

    def format(self, abs_path: str) -> Optional[list[dict]]:
        """Return text edits from LSP formatting, or None if unavailable."""
        if not self.enabled:
            return None

        doc_type = get_document_type(abs_path)
        if doc_type is None:
            return None

        client = self._get_client(doc_type)
        if client is None:
            return None

        try:
            return client.formatting(path_to_uri(abs_path))
        except LspError as exc:
            logger.debug("LSP formatting failed for %s: %s", abs_path, exc)
            return None

    def notify_open(self, abs_path: str, text: str) -> None:
        client, doc_type = self._get_client_and_type(abs_path)
        if client is None or doc_type is None:
            return
        client.did_open(path_to_uri(abs_path), doc_type.name, text)

    def notify_changed(self, abs_path: str, text: str) -> None:
        client = self._get_client_for_path(abs_path)
        if client is None:
            return
        client.did_change(path_to_uri(abs_path), text)

    def notify_saved(self, abs_path: str) -> None:
        client = self._get_client_for_path(abs_path)
        if client is None:
            return
        client.did_save(path_to_uri(abs_path))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client_key(self, doc_type: DocumentType) -> str:
        return f"{self.workspace_root}::{doc_type.name}"

    def _get_client(self, doc_type: DocumentType) -> Optional[LspClient]:
        if not self.enabled or doc_type.name in self._unavailable:
            return None

        key = self._client_key(doc_type)
        client = self._clients.get(key)
        if client is not None:
            return client

        if doc_type.lsp_server is None:
            self._unavailable.add(doc_type.name)
            return None

        command = self.server_overrides.get(doc_type.name, doc_type.lsp_server.command)
        client = LspClient()
        try:
            client.start(
                command=command,
                args=doc_type.lsp_server.args,
                root_uri=path_to_uri(self.workspace_root),
                initialization_options=doc_type.lsp_server.initialization_options,
            )
        except LspServerNotFoundError as exc:
            logger.debug("LSP server not found for %s: %s", doc_type.name, exc)
            self._unavailable.add(doc_type.name)
            return None
        except LspError as exc:
            logger.debug("LSP server failed for %s: %s", doc_type.name, exc)
            self._unavailable.add(doc_type.name)
            return None

        self._clients[key] = client
        atexit.register(client.stop)
        return client

    def _get_client_for_path(self, abs_path: str) -> Optional[LspClient]:
        doc_type = get_document_type(abs_path)
        if doc_type is None:
            return None
        return self._get_client(doc_type)

    def _get_client_and_type(
        self, abs_path: str
    ) -> tuple[Optional[LspClient], Optional[DocumentType]]:
        doc_type = get_document_type(abs_path)
        if doc_type is None:
            return None, None
        return self._get_client(doc_type), doc_type

    @staticmethod
    def _symbols_to_sections(
        abs_path: str, symbols: list[dict], doc_type: DocumentType
    ) -> list[tuple[str, str, int, int, str]]:
        """Convert LSP symbols to section tuples.

        Only keeps symbols that look like document sections/headings.
        For Markdown and Typst we fall back to regex parsing because LSP
        document symbols usually cover only the heading line, so they would
        drop the section body.
        """
        content = utils.read_text_robust(abs_path)
        if content is None:
            return []
        lines = content.split("\n")

        if doc_type is MARKDOWN or doc_type is TYPST:
            return doc_type.parse_sections(content)

        section_kinds = {2, 3, 5, 15}  # Module, Namespace, Class, String
        items = []

        for sym in symbols:
            kind = sym.get("kind")
            name = sym.get("name", "")
            if kind not in section_kinds:
                continue

            # Handle both SymbolInformation (location.range) and
            # DocumentSymbol (range directly).
            if "location" in sym:
                rng = sym["location"].get("range", {})
            else:
                rng = sym.get("range", {})
            start = rng.get("start", {})
            end = rng.get("end", {})
            start_line = start.get("line", 0)
            end_line = end.get("line", len(lines) - 1)

            if end_line < start_line:
                end_line = start_line

            # Clamp to file bounds.
            end_line = min(end_line, len(lines) - 1)

            section_content = "\n".join(lines[start_line : end_line + 1])
            level_name = LspManager._guess_level(name, kind, doc_type)
            items.append((level_name, name, start_line, end_line, section_content))

        # Sort by start line and remove duplicates.
        items.sort(key=lambda x: x[2])
        return items

    @staticmethod
    def _guess_level(name: str, kind: int, doc_type: DocumentType) -> str:
        """Heuristic to map an LSP symbol to section/subsection/subsubsection."""
        if kind == 3:  # Namespace
            return "section"
        if kind == 2:  # Module
            return "subsection"
        return "subsubsection"
