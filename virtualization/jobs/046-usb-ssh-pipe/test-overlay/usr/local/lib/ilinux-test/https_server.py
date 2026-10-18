#!/usr/bin/env python3
"""VM test only: an HTTPS file server on 127.0.0.1 (the M1's network in the test) with the
test certificate, standing in for the web the M5 reaches through the forwarded proxy."""
import argparse
import functools
import http.server
import ssl

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--cert", required=True)
parser.add_argument("--key", required=True)
parser.add_argument("--dir", required=True)
args = parser.parse_args()
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=args.dir)
server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(args.cert, args.key)
server.socket = context.wrap_socket(server.socket, server_side=True)
print("https on 127.0.0.1:%d" % args.port, flush=True)
server.serve_forever()
