#!/usr/bin/env python3
"""Tiny relay backend for the Relay demo.

Zero dependencies — just `python3 server.py`. Keeps messages in memory.
  • Relay      POST /send                      (body = the encrypted Envelope JSON)
  • Recipient  GET  /messages?recipient=C      (returns that recipient's envelopes)

Run it on a laptop on the SAME Wi-Fi as the relay + recipient devices, then set
`serverUrl` in AppViewModel.kt to  http://<this-laptop-LAN-IP>:8080
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Windows consoles often default to a non-UTF-8 codepage (e.g. gbk), which would
# crash on any non-ASCII print and take the server down on startup. Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MESSAGES = []  # list of envelope dicts (in-memory; resets on restart)
PORT = 8080


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/send":
            return self._send_json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            env = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "bad json"})
        MESSAGES.append(env)
        ct = env.get("ciphertext", "")
        print(f"[relayed] {env.get('id')}  ->  recipient {env.get('recipientId')}  "
              f"({len(ct)} b64 chars of ciphertext - unreadable to us)")
        self._send_json(200, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/messages":
            return self._send_json(404, {"error": "not found"})
        recipient = parse_qs(parsed.query).get("recipient", [""])[0]
        out = [m for m in MESSAGES if m.get("recipientId") == recipient]
        self._send_json(200, out)

    def log_message(self, *args):
        pass  # silence default request logging; we print our own line


if __name__ == "__main__":
    print(f"Relay server listening on http://0.0.0.0:{PORT}")
    print("  POST /send   |   GET /messages?recipient=C")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
