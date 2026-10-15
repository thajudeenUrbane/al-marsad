#!/usr/bin/env python3
"""Serve stories-50/ locally with a correct UTF-8 charset (see demo/serve.py)."""
import functools, http.server, socketserver

PORT = 8751

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
    handler = functools.partial(Handler, directory="stories-50")
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"serving stories-50/ at http://localhost:{PORT}")
        httpd.serve_forever()
