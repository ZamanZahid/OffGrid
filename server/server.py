#!/usr/bin/env python3
"""Tiny relay backend for the Relay demo.

Zero dependencies — just `python3 server.py`. Keeps messages in memory.
  • Relay      POST /send                      (body = the encrypted Envelope JSON)
  • Recipient  GET  /messages?recipient=C      (returns that recipient's envelopes)

Run it on a laptop on the SAME Wi-Fi as the relay + recipient devices, then set
`serverUrl` in AppViewModel.kt to  http://<this-laptop-LAN-IP>:8080
"""
import base64
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np
from PIL import Image

import aerogaze.mobile as mobile

# Windows consoles often default to a non-UTF-8 codepage (e.g. gbk), which would
# crash on any non-ASCII print and take the server down on startup. Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MESSAGES = []  # list of envelope dicts (in-memory; resets on restart)
PORT = 8080
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_demo_output(output: str):
    def _get(pattern: str):
        m = re.search(pattern, output)
        return None if not m else float(m.group(1))

    return {
        "recovered_lat": _get(r"RECOVERED\s+:\s+([+\-]?\d+\.\d+)"),
        "recovered_lon": _get(r"RECOVERED\s+:\s+[+\-]?\d+\.\d+\s*,\s*([+\-]?\d+\.\d+)"),
        "error_km": _get(r"error\s+:\s*([0-9.]+) km"),
        "stars_detected": _get(r"stars detected\s+:\s*(\d+)"),
        "inlier_matches": _get(r"inlier matches\s+:\s*(\d+)"),
        "residual_arcsec": _get(r"solve residual\s+:\s*([0-9.]+) arcsec"),
    }


def _decode_photo(image_b64: str) -> np.ndarray:
    raw = base64.b64decode(image_b64)
    img = Image.open(BytesIO(raw)).convert("L")
    img.thumbnail((1600, 1600), Image.LANCZOS)
    return np.asarray(img)


def _solve_photo(image_b64: str, timestamp_utc: str, alt_deg: float, roll_deg: float, fov_deg: float):
    img = _decode_photo(image_b64)
    h, w = img.shape
    result = mobile.solve_horizon(img.tobytes(), w, h, alt_deg, roll_deg,
                                  timestamp_utc, fov_deg,
                                  os.path.join(ROOT, "data", "index.npz"))
    return json.loads(result)


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/send":
            length = int(self.headers.get("Content-Length", 0))
            try:
                env = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "bad json"})
            MESSAGES.append(env)
            ct = env.get("ciphertext", "")
            print(f"[relayed] {env.get('id')}  ->  recipient {env.get('recipientId')}  "
                  f"({len(ct)} b64 chars of ciphertext - unreadable to us)")
            return self._send_json(200, {"ok": True})

        if path == "/health":
            return self._send_json(200, {"ok": True, "messages": len(MESSAGES)})

        if path == "/demo-solve":
            try:
                proc = subprocess.run(
                    [sys.executable, os.path.join(ROOT, "scripts", "demo.py")],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except Exception as exc:
                return self._send_json(500, {"error": str(exc)})

            output = (proc.stdout or "") + (proc.stderr or "")
            data = _parse_demo_output(output)
            data["ok"] = proc.returncode == 0
            data["returncode"] = proc.returncode
            data["output"] = output
            return self._send_json(200, data)

        if path == "/solve-photo":
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "bad json"})

            try:
                image_b64 = payload["image_b64"]
                timestamp_utc = payload["timestamp_utc"]
                alt_deg = float(payload.get("alt_deg", 90.0))
                roll_deg = float(payload.get("roll_deg", 0.0))
                fov_deg = float(payload.get("fov_deg", 60.0))
            except Exception as exc:
                return self._send_json(400, {"error": f"invalid request: {exc}"})

            try:
                result = _solve_photo(image_b64, timestamp_utc, alt_deg, roll_deg, fov_deg)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
            return self._send_json(200, result)

        return self._send_json(404, {"error": "not found"})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/messages":
            recipient = parse_qs(parsed.query).get("recipient", [""])[0]
            out = [m for m in MESSAGES if m.get("recipientId") == recipient]
            return self._send_json(200, out)
        if parsed.path == "/health":
            return self._send_json(200, {"ok": True, "messages": len(MESSAGES)})
        return self._send_json(404, {"error": "not found"})

    def log_message(self, *args):
        pass  # silence default request logging; we print our own line


if __name__ == "__main__":
    print(f"Relay server listening on http://0.0.0.0:{PORT}")
    print("  POST /send   |   GET /messages?recipient=C")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
