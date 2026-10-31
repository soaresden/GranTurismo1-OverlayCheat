"""Development server for the page (index.html?test): the project's files, and a disc image at
/test/disc read with HTTP Range requests (as the page reads a chosen file in slices).

python tools/serve_test.py "Gran Turismo.chd" [port]      then open http://localhost:8765/?test
"""
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def _disc(self, body):
        size = os.path.getsize(DISC)
        rng = self.headers.get('Range')
        if rng and rng.startswith('bytes='):
            a, b = rng[6:].split('-')
            a, b = int(a), min(int(b) if b else size - 1, size - 1)
            self.send_response(206)
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (a, b, size))
        else:
            a, b = 0, size - 1
            self.send_response(200)
        self.send_header('Content-Length', str(b - a + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        if body:
            with open(DISC, 'rb') as f:
                f.seek(a)
                self.wfile.write(f.read(b - a + 1))

    def do_HEAD(self):
        if self.path.startswith('/test/disc'):
            return self._disc(False)
        return super().do_HEAD()

    def do_GET(self):
        if self.path.startswith('/test/disc'):
            return self._disc(True)
        return super().do_GET()


if __name__ == '__main__':
    print('http://localhost:%d/?test  (disc: %s)' % (PORT, DISC))
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
