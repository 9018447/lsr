"""A minimal JSON-RPC LSP client for LaTeX, Typst, and Markdown."""

import json
import logging
import os
import re
import shutil
import subprocess
import threading
from typing import Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class LspError(Exception):
    """Raised when an LSP request fails or the server misbehaves."""


class LspServerNotFoundError(LspError):
    """Raised when the configured LSP server binary is not available."""


CONTENT_LENGTH_RE = re.compile(rb"^Content-Length: (\d+)\r?$")


class _PendingRequest:
    __slots__ = ("event", "response", "error")

    def __init__(self):
        self.event = threading.Event()
        self.response = None
        self.error = None


class JsonRpcTransport:
    """Low-level JSON-RPC transport over a subprocess stdin/stdout."""

    def __init__(self, process: subprocess.Popen):
        self.process = process
        self._write_lock = threading.Lock()

    def send(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
        with self._write_lock:
            self.process.stdin.write(header + data)
            self.process.stdin.flush()

    def read_message(self) -> Optional[dict]:
        """Read one JSON-RPC message from the server stdout."""
        content_length = None
        while True:
            line = self.process.stdout.readline()
            if not line:
                return None
            line = line.rstrip(b"\r\n")
            if not line:
                break
            m = CONTENT_LENGTH_RE.match(line)
            if m:
                content_length = int(m.group(1))

        if content_length is None:
            return None

        data = self.process.stdout.read(content_length)
        if len(data) < content_length:
            return None
        return json.loads(data.decode("utf-8"))


class LspClient:
    """Blocking LSP client with a background reader thread."""

    def __init__(self):
        self.transport: Optional[JsonRpcTransport] = None
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._shutdown = False
        self._next_id = 1
        self._pending: dict[int, _PendingRequest] = {}
        self._diagnostics: dict[str, list[dict]] = {}
        self._lock = threading.Lock()
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        command: str,
        args: tuple[str, ...] = (),
        root_uri: str = "",
        initialization_options: Optional[dict] = None,
        timeout: float = 30.0,
    ) -> bool:
        """Start the server and initialize the LSP session.

        Returns True on success, False if the binary is missing or the server
        fails to respond.
        """
        binary = shutil.which(command)
        if binary is None:
            raise LspServerNotFoundError(f"LSP server binary not found: {command}")

        try:
            self._process = subprocess.Popen(
                [binary, *args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except OSError as exc:
            raise LspError(f"Failed to start LSP server {command}: {exc}") from exc

        self.transport = JsonRpcTransport(self._process)
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        init_params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "synchronization": {"dynamicRegistration": False},
                    "documentSymbol": {
                        "dynamicRegistration": False,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                    },
                    "formatting": {"dynamicRegistration": False},
                    "hover": {"dynamicRegistration": False},
                },
                "workspace": {"workspaceFolders": False},
            },
            "workspaceFolders": None,
        }
        if initialization_options:
            init_params["initializationOptions"] = initialization_options

        try:
            result = self._call("initialize", init_params, timeout=timeout)
            if result is None:
                raise LspError("LSP server did not respond to initialize")
            self._server_capabilities = result.get("capabilities", {})
            self._notify("initialized", {})
            self._initialized = True
            return True
        except Exception:
            self.stop()
            raise

    def stop(self, timeout: float = 5.0) -> None:
        """Shutdown the LSP server gracefully."""
        self._shutdown = True
        try:
            if self._initialized and self.transport:
                self._call("shutdown", None, timeout=timeout)
                self._notify("exit", {})
        except Exception as exc:
            logger.debug("LSP shutdown error (ignored): %s", exc)
        finally:
            if self._process is not None:
                try:
                    self._process.stdin.close()
                except Exception:
                    pass
                try:
                    self._process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            self.transport = None
            self._process = None
            self._initialized = False

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def did_open(self, uri: str, language_id: str, text: str) -> None:
        self._notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": language_id,
                    "version": 1,
                    "text": text,
                }
            },
        )

    def did_change(self, uri: str, text: str, version: int = 2) -> None:
        self._notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": version},
                "contentChanges": [{"text": text}],
            },
        )

    def did_save(self, uri: str) -> None:
        self._notify("textDocument/didSave", {"textDocument": {"uri": uri}})

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def document_symbols(self, uri: str) -> list[dict]:
        result = self._call("textDocument/documentSymbol", {"textDocument": {"uri": uri}})
        if not isinstance(result, list):
            return []
        return self._flatten_symbols(result)

    def formatting(self, uri: str) -> list[dict]:
        result = self._call(
            "textDocument/formatting",
            {"textDocument": {"uri": uri}, "options": {"tabSize": 2, "insertSpaces": True}},
        )
        if not isinstance(result, list):
            return []
        return result

    def get_diagnostics(self, uri: str) -> list[dict]:
        with self._lock:
            return list(self._diagnostics.get(uri, []))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reader_loop(self) -> None:
        while not self._shutdown:
            try:
                msg = self.transport.read_message()
            except Exception as exc:
                logger.debug("LSP read error: %s", exc)
                break
            if msg is None:
                break
            self._handle_message(msg)

    def _handle_message(self, msg: dict) -> None:
        if "id" in msg and "method" not in msg:
            # Response to a request
            req_id = msg["id"]
            with self._lock:
                pending = self._pending.pop(req_id, None)
            if pending is None:
                return
            if "error" in msg:
                pending.error = msg["error"]
            else:
                pending.response = msg.get("result")
            pending.event.set()
        elif "method" in msg:
            self._handle_notification(msg)

    def _handle_notification(self, msg: dict) -> None:
        method = msg.get("method")
        params = msg.get("params", {})
        if method == "textDocument/publishDiagnostics":
            uri = params.get("uri")
            diagnostics = params.get("diagnostics", [])
            if uri is not None:
                with self._lock:
                    self._diagnostics[uri] = diagnostics

    def _call(self, method: str, params: Any, timeout: float = 10.0) -> Any:
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            pending = _PendingRequest()
            self._pending[req_id] = pending

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params

        try:
            self.transport.send(payload)
        except Exception as exc:
            with self._lock:
                self._pending.pop(req_id, None)
            raise LspError(f"Failed to send LSP request {method}: {exc}") from exc

        if not pending.event.wait(timeout=timeout):
            with self._lock:
                self._pending.pop(req_id, None)
            raise LspError(f"LSP request {method} timed out after {timeout}s")

        if pending.error is not None:
            raise LspError(f"LSP request {method} failed: {pending.error}")
        return pending.response

    def _notify(self, method: str, params: Any) -> None:
        if self.transport is None:
            return
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self.transport.send(payload)
        except Exception as exc:
            logger.debug("LSP notification %s failed: %s", method, exc)

    @staticmethod
    def _flatten_symbols(symbols: list[dict]) -> list[dict]:
        flat = []

        def walk(items):
            for item in items:
                flat.append(item)
                children = item.get("children")
                if children:
                    walk(children)

        walk(symbols)
        return flat


def path_to_uri(path: str) -> str:
    """Convert a filesystem path to a file:// URI."""
    abs_path = os.path.abspath(path)
    return "file://" + quote(abs_path.replace(os.sep, "/"))


def uri_to_path(uri: str) -> str:
    """Convert a file:// URI back to a filesystem path."""
    from urllib.parse import unquote

    if uri.startswith("file://"):
        uri = uri[7:]
    return unquote(uri).replace("/", os.sep)
