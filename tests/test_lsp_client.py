import io
import json
import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from lsr.lsp_client import JsonRpcTransport, LspClient, LspError, path_to_uri


def build_message(payload: dict) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data


class TestPathToUri:
    def test_converts_absolute_path(self):
        uri = path_to_uri("/home/user/paper.tex")
        assert uri.startswith("file://")
        assert uri.endswith("paper.tex")


class TestJsonRpcTransport:
    def test_send_writes_header_and_body(self):
        stdout = io.BytesIO()
        stdin = MagicMock()
        process = MagicMock()
        process.stdout = stdout
        process.stdin = stdin

        transport = JsonRpcTransport(process)
        transport.send({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

        stdin.write.assert_called_once()
        written = stdin.write.call_args[0][0]
        assert b"Content-Length:" in written
        assert b"initialize" in written

    def test_read_message(self):
        payload = {"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}
        stdout = io.BytesIO(build_message(payload))
        stdin = MagicMock()
        process = MagicMock()
        process.stdout = stdout
        process.stdin = stdin

        transport = JsonRpcTransport(process)
        msg = transport.read_message()
        assert msg == payload


class RecordingBytesIO(io.BytesIO):
    """A BytesIO that records every write and exposes the last payload."""

    def __init__(self):
        super().__init__()
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        return super().write(data)


class TestLspClientLifecycle:
    def test_call_sends_request_and_returns_response(self):
        stdin = RecordingBytesIO()
        process = MagicMock()
        process.stdin = stdin
        process.stdout = io.BytesIO()
        process.stderr = io.BytesIO()

        client = LspClient()
        client.transport = JsonRpcTransport(process)

        # Inject the matching response shortly after the request is sent.
        def delayed_response():
            time.sleep(0.05)
            client._handle_message({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}})

        threading.Thread(target=delayed_response, daemon=True).start()
        result = client._call("initialize", {"rootUri": "file:///"}, timeout=1.0)

        assert result == {"capabilities": {}}
        assert len(stdin.writes) == 1
        payload = json.loads(stdin.writes[0].split(b"\r\n\r\n")[1])
        assert payload["method"] == "initialize"

    def test_start_invokes_initialize(self):
        captured = {}

        def fake_call(self, method, params, timeout=10.0):
            captured["method"] = method
            captured["params"] = params
            return {"capabilities": {}}

        stdin = RecordingBytesIO()
        process = MagicMock(stdin=stdin, stdout=io.BytesIO(), stderr=io.BytesIO())

        client = LspClient()
        with patch("shutil.which", return_value="/fake/server"):
            with patch("subprocess.Popen", return_value=process):
                with patch.object(LspClient, "_call", fake_call):
                    result = client.start("fake-server")

        assert result is True
        assert client._initialized is True
        assert captured["method"] == "initialize"
        assert captured["params"]["processId"] == os.getpid()

    def test_start_raises_when_binary_missing(self):
        client = LspClient()
        with patch("shutil.which", return_value=None):
            with pytest.raises(LspError):
                client.start("missing-server")


class TestLspClientNotifications:
    def test_did_open_is_sent(self):
        stdin = MagicMock()
        process = MagicMock()
        process.stdin = stdin
        process.stdout = io.BytesIO()
        process.stderr = io.BytesIO()

        client = LspClient()
        client.transport = JsonRpcTransport(process)
        client.did_open("file:///paper.tex", "latex", "\\section{Intro}")

        stdin.write.assert_called_once()
        written = stdin.write.call_args[0][0]
        msg = json.loads(written.split(b"\r\n\r\n")[1])
        assert msg["method"] == "textDocument/didOpen"
        assert msg["params"]["textDocument"]["uri"] == "file:///paper.tex"


class TestLspClientDiagnostics:
    def test_publish_diagnostics_cached(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": "file:///paper.tex",
                "diagnostics": [{"range": {"start": {"line": 0, "character": 0}}}],
            },
        }
        stdout = io.BytesIO(build_message(payload))
        stdin = MagicMock()
        process = MagicMock()
        process.stdout = stdout
        process.stdin = stdin

        transport = JsonRpcTransport(process)
        client = LspClient()
        client.transport = transport

        # Run reader loop briefly.
        client._handle_message(client.transport.read_message())

        diagnostics = client.get_diagnostics("file:///paper.tex")
        assert len(diagnostics) == 1
