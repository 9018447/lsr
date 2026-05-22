#!/usr/bin/env python
"""Local HTTP server for /note command.

Serves the review HTML and receives approve/cancel POST requests.
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class NoteRequestHandler(BaseHTTPRequestHandler):
    """Handle GET (serve HTML) and POST (approve/cancel) requests."""

    def do_GET(self):
        """Serve the HTML file."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        with open(self.server.html_path, "rb") as f:
            self.wfile.write(f.read())

    def do_POST(self):
        """Handle approve/cancel requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        if self.path == "/approve":
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}
            self.server.comments = data
            self.server.approved = True
            self.server.response_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif self.path == "/cancel":
            self.server.approved = False
            self.server.response_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress server logging."""
        pass


class NoteServer:
    """Local HTTP server for /note command.

    Starts on a random port, serves the HTML file,
    and receives approve/cancel POST requests.
    """

    def __init__(self, html_path):
        self.html_path = html_path
        self.port = 0  # Will be assigned
        self.comments = None
        self.approved = False
        self.response_event = threading.Event()
        self._server = None
        self._thread = None

    def start(self):
        """Start server in background thread on a random port."""
        self._server = HTTPServer(("localhost", 0), NoteRequestHandler)
        self._server.html_path = self.html_path
        self._server.comments = None
        self._server.approved = False
        self._server.response_event = self.response_event
        self.port = self._server.server_address[1]

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def wait_for_response(self, timeout=300):
        """Wait for approve/cancel response.

        Returns:
            comments dict if approved, None if cancelled or timed out.
        """
        self.response_event.wait(timeout=timeout)

        if not self.response_event.is_set():
            # Timed out
            self._server.shutdown()
            return None

        self._server.shutdown()

        if self._server.approved:
            return self._server.comments
        return None

    def shutdown(self):
        """Shut down the server."""
        if self._server:
            self._server.shutdown()
