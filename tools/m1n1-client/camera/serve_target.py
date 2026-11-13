#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Serve only the public framing target, briefly; no camera, files or boot API."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind', default='127.0.0.1', help='Explicit LAN address for the M5; no automatic discovery')
    p.add_argument('--port', type=int, default=0)
    p.add_argument('--seconds', type=int, default=900)
    args = p.parse_args()
    if not 1 <= args.seconds <= 1800 or not 0 <= args.port <= 65535:
        p.error('bounded lifetime/port required')
    page = Path(__file__).with_name('framing-target.html').read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/', '/framing'):
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(page)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, *_): pass

    with HTTPServer((args.bind, args.port), Handler) as server:
        server.timeout = 1
        deadline = time.monotonic() + args.seconds
        print(f'Framing page: http://{args.bind}:{server.server_port}/framing', flush=True)
        try:
            while time.monotonic() < deadline:
                server.handle_request()
        except KeyboardInterrupt: pass


if __name__ == '__main__': main()
