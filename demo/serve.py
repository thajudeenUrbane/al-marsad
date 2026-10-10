#!/usr/bin/env python3
"""
Serve the demo locally with a correct charset.

    python demo/serve.py        # http://localhost:8748

Python's stock http.server does not declare charset=utf-8, so browsers fall
back to windows-1252 and every Arabic transliteration renders as mojibake
(Ghār -> GhÄr). That is a serving bug, not a file bug — but it looks exactly
like a file bug, so this exists to keep it from wasting anyone's time.
"""

import functools
import http.server
import socketserver

PORT = 8748


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        t = super().guess_type(path)
        if str(t).startswith("text/") or t == "application/json":
            return f"{t}; charset=utf-8"
        return t

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    handler = functools.partial(Handler, directory="demo")
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"serving demo/ at http://localhost:{PORT}  (ctrl-c to stop)")
        httpd.serve_forever()
