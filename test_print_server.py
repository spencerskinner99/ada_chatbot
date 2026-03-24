#!/usr/bin/env python3
"""
ADA x Ollama — Test Print Server

Simulates the thermal printer endpoint so you can test printing without
physical hardware. Receives HTTP GET requests at:

    http://localhost:8080/?code=MESSAGE

and displays all received print jobs on a webpage at:

    http://localhost:8080/

The page auto-refreshes every 3 seconds.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote_plus
import datetime
import html as html_module

# ── State ──────────────────────────────────────────────────────────────────────

jobs: list[dict] = []   # {"time": str, "text": str}


# ── Request handler ────────────────────────────────────────────────────────────

class PrintHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            self._receive_job(params["code"][0])
        else:
            self._serve_page()

    def _receive_job(self, raw: str):
        text = unquote_plus(raw)
        jobs.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "text": text,
        })
        print(f"[{jobs[-1]['time']}] Print job received ({len(text)} chars)")
        self._respond(200, "text/plain", b"OK")

    def _serve_page(self):
        body = _render_page().encode("utf-8")
        self._respond(200, "text/html; charset=utf-8", body)

    def _respond(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Suppress noisy GET / logs from auto-refresh; keep job receipts only
        pass


# ── Page renderer ──────────────────────────────────────────────────────────────

def _render_page() -> str:
    if jobs:
        cards = ""
        for job in reversed(jobs):
            escaped = html_module.escape(job["text"])
            cards += f"""
      <div class="card">
        <div class="card-meta">{job["time"]}</div>
        <pre class="card-body">{escaped}</pre>
      </div>"""
        count_text = f"{len(jobs)} job{'s' if len(jobs) != 1 else ''} received"
    else:
        cards = """
      <div class="empty">
        <p>No print jobs received yet.</p>
        <p>Send a print from the ADA interface — make sure the printer IP is set to <code>localhost</code>.</p>
      </div>"""
        count_text = "No jobs yet"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="3">
  <title>ADA Print Test Server</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f7f8;
      color: #1a1a1a;
      min-height: 100vh;
    }}

    /* ── Top bar ── */
    #topbar {{
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 0 24px;
      height: 56px;
      background: #fff;
      border-bottom: 1px solid #e5e5e5;
    }}
    #topbar h1 {{
      font-size: 16px;
      font-weight: 700;
      color: #1a1a1a;
      white-space: nowrap;
    }}
    #topbar .sep {{ flex: 1; }}
    #topbar .meta {{
      font-size: 13px;
      color: #888;
    }}
    .dot {{
      display: inline-block;
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #34a853;
      margin-right: 6px;
      animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.4; }}
    }}

    /* ── Content ── */
    #content {{
      max-width: 800px;
      margin: 32px auto;
      padding: 0 16px;
    }}

    /* ── Job card ── */
    .card {{
      background: #fff;
      border: 1px solid #e5e5e5;
      border-radius: 12px;
      margin-bottom: 20px;
      overflow: hidden;
    }}
    .card-meta {{
      padding: 10px 16px;
      font-size: 12px;
      font-weight: 600;
      color: #888;
      background: #f4f4f6;
      border-bottom: 1px solid #e5e5e5;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .card-body {{
      padding: 16px;
      font-family: "Courier New", Courier, monospace;
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
      color: #1a1a1a;
    }}

    /* ── Empty state ── */
    .empty {{
      text-align: center;
      padding: 80px 0;
      color: #888;
      font-size: 15px;
      line-height: 2;
    }}
    .empty code {{
      background: #f4f4f6;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
      color: #1a73e8;
    }}
  </style>
</head>
<body>

  <div id="topbar">
    <h1>ADA Print Test Server</h1>
    <div class="sep"></div>
    <span class="meta"><span class="dot"></span>Listening on port 8080 &nbsp;·&nbsp; {count_text} &nbsp;·&nbsp; Auto-refresh every 3s</span>
  </div>

  <div id="content">
    {cards}
  </div>

</body>
</html>
"""


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), PrintHandler)
    print(f"ADA Test Print Server running at http://localhost:{port}/")
    print(f"Waiting for print jobs at http://localhost:{port}/?code=...")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
