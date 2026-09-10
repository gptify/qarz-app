"""
=============================================================================
QARZ APP (SMART QARZ DAFTARI) — TELEGRAM MINI APP LOCAL DEV SERVER
=============================================================================
Runs on http://localhost:8085
Serves the `tma_qarz/` web directory with proper UTF-8 and MIME types.
=============================================================================
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

PORT = 8085
DIRECTORY = Path(__file__).resolve().parent

class TMAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def guess_type(self, path):
        mime_type = super().guess_type(path)
        if path.endswith('.js'):
            return 'application/javascript; charset=utf-8'
        elif path.endswith('.html'):
            return 'text/html; charset=utf-8'
        elif path.endswith('.css'):
            return 'text/css; charset=utf-8'
        return mime_type

def run_server():
    print("=" * 65)
    print("Qarz App - Aqlli Qarz Daftari TMA Server")
    print("=" * 65)
    print(f"Web Directory: {DIRECTORY}")
    print(f"Local URL:     http://localhost:{PORT}")
    print("Status:        Server is actively running")
    print("=" * 65)

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), TMAHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer to'xtatildi.")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
