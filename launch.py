#!/usr/bin/env python3
"""
ADA x Ollama — Launcher

Starts both servers in a single command:
  - Test print server  →  http://localhost:8080/
  - Web interface      →  http://localhost:9090/ollama_web.html

Press Ctrl+C to stop both.
"""

import os
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Ensure imports resolve relative to this file's directory
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from test_print_server import PrintHandler

PRINT_PORT = 8080
WEB_PORT   = 9090


# ── Quiet file server (suppresses per-request logs) ───────────────────────────

class QuietFileHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        pass  # suppress request logs


# ── Start ──────────────────────────────────────────────────────────────────────

def _serve(server: HTTPServer):
    server.serve_forever()


def main():
    try:
        print_server = HTTPServer(("0.0.0.0", PRINT_PORT), PrintHandler)
    except OSError:
        print(f"[error] Port {PRINT_PORT} is already in use.")
        sys.exit(1)

    try:
        web_server = HTTPServer(("0.0.0.0", WEB_PORT), QuietFileHandler)
    except OSError:
        print(f"[error] Port {WEB_PORT} is already in use.")
        sys.exit(1)

    threading.Thread(target=_serve, args=(print_server,), daemon=True).start()
    threading.Thread(target=_serve, args=(web_server,),   daemon=True).start()

    print()
    print("  ADA x Ollama — running")
    print()
    print(f"  Chat interface   →  http://localhost:{WEB_PORT}/ollama_web.html")
    print(f"  Print job viewer →  http://localhost:{PRINT_PORT}/")
    print()
    print("  Press Ctrl+C to stop.")
    print()

    try:
        # Block the main thread until Ctrl+C
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n  Shutting down… ", end="", flush=True)
        print_server.shutdown()
        web_server.shutdown()
        print("done.")


if __name__ == "__main__":
    main()
