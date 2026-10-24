#!/usr/bin/env python3
"""
Serve the exhibition, with the Atlas and the expeditions beside it, from one place.

    python3 exhibition/serve.py              # opens http://127.0.0.1:8770/exhibition/
    python3 exhibition/serve.py --no-browser --port 8771

It serves the repository root on 127.0.0.1 only, so the halls can show the Atlas and
the expeditions as same-origin live views. Every text type goes out with
charset=utf-8: Python's stock server leaves it off, and the browser then shows
"al-MarÄá¹£ad". Nothing here reaches outside the machine. Standard library only.
"""

import argparse
import errno
import functools
import http.server
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRESENTER = "/exhibition/presenter.local.json"

TYPES = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".ttl": "text/turtle",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        t = TYPES.get(Path(str(path)).suffix.lower()) or super().guess_type(path)
        if t.startswith("text/") or t in ("application/json", "image/svg+xml"):
            return f"{t}; charset=utf-8"
        return t

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/exhibition/")
            self.end_headers()
            return
        # Dot folders (.git, .venv, .claude) are never served.
        if any(part.startswith(".") for part in path.split("/") if part):
            self.send_error(404)
            return
        # The presenter's name lives in a git-ignored file; without it the page leaves a blank line.
        if path == PRESENTER and not (ROOT / PRESENTER.lstrip("/")).exists():
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def log_message(self, fmt, *args):
        pass  # quiet while presenting; errors still print below

    def log_error(self, fmt, *args):
        sys.stderr.write("serve.py: " + (fmt % args) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = ap.parse_args(argv)

    handler = functools.partial(Handler, directory=str(ROOT))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"Port {args.port} is busy. Is the exhibition already running? "
                  f"Try http://127.0.0.1:{args.port}/exhibition/ or use --port {args.port + 1}.")
            return 1
        raise
    url = f"http://127.0.0.1:{args.port}/exhibition/"
    print(f"al-Marṣad exhibition at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
